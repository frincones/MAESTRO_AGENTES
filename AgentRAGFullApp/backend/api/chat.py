"""Chat endpoint: main conversational interface."""

from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.base_agent import RAGAgent
from config.schema import load_config
from utils.db import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Single shared agent instance (stateless — session_id is passed per request)
_agent: Optional[RAGAgent] = None


async def _get_agent() -> RAGAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        config = load_config()
        storage = await get_storage(config.storage)
        _agent = RAGAgent(config, storage)
        logger.info(
            "Agent initialized: %s (%s)",
            config.agent.name,
            config.agent.role,
        )
    return _agent


# Chitchat short-circuit: detects trivial conversational turns (greetings,
# thanks, farewells, acknowledgments) and routes them through a lightweight
# path that skips embedding + hybrid_search + rerank. Saves ~2-3s on TTFT.
#
# Detection strategy: tokenize the message and check if EVERY significant
# word belongs to a small curated chitchat vocabulary. This catches compound
# greetings like "hola como estas", "buenos dias gracias", "hello how are you"
# that an exact-phrase match would miss.

# Individual chitchat tokens (word-level). A message is chitchat if all its
# significant words are drawn from this set.
_CHITCHAT_TOKENS = {
    # Spanish — greetings
    "hola", "holi", "holis", "holaaa", "holaa", "buenas", "buenos",
    "dias", "días", "tardes", "noches", "saludos",
    # Spanish — how are you
    "como", "cómo", "que", "qué", "tal", "estas", "estás", "estan", "están",
    "estais", "estáis", "va", "andas", "anda", "mas", "más", "pasa", "cuentas",
    # Spanish — thanks
    "gracias", "muchas", "mil", "agradezco", "agradecido", "agradecida",
    # Spanish — acknowledgments
    "ok", "okay", "okey", "vale", "listo", "entendido", "entendida",
    "perfecto", "perfecta", "genial", "excelente", "claro", "dale", "bien",
    "bueno", "buena",
    # Spanish — yes/no
    "si", "sí", "no", "quiza", "quizá", "quizas", "quizás", "tal", "vez",
    # Spanish — farewell
    "adios", "adiós", "chao", "chau", "bye", "hasta", "luego", "pronto",
    "mañana", "nos", "vemos", "cuidate", "cuídate",
    # English — greetings
    "hi", "hello", "hey", "howdy", "yo", "sup", "greetings",
    # English — how are you
    "how", "are", "you", "yall", "doing", "whats", "what's", "up",
    # English — thanks
    "thanks", "thank", "thx", "ty", "thnx", "appreciated", "appreciate",
    # English — acknowledgments
    "cool", "nice", "great", "awesome", "got", "it", "understood", "sure",
    "alright", "fine",
    # English — yes/no
    "yes", "yeah", "yep", "no", "nope",
    # English — farewell
    "goodbye", "see", "ya", "cya", "later", "farewell",
    # Universal pleasantries
    "pls", "please", "porfa", "porfavor", "por", "favor",
    # Fillers / emotional
    "jaja", "jeje", "jiji", "lol", "xd", "haha", "hehe",
}

# Lightweight tokens that don't disqualify a message from being chitchat
# (articles, prepositions, conjunctions, particles)
_CHITCHAT_STOPWORDS = {
    "a", "e", "i", "o", "u", "y", "de", "del", "la", "las", "el", "los",
    "un", "una", "unos", "unas", "al", "en", "con", "me", "te", "se",
    "to", "the", "and", "of", "for", "is", "im", "i'm",
}

# Messages matching this pattern are chitchat even if not in the exact set
_CHITCHAT_EMOJI_ONLY = re.compile(
    r"^[\s\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2700-\u27BF!?.,¿¡]*$"
)

# Words we tokenize as (letters/numbers only, drop everything else)
_WORD_RE = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)


def _normalize(text: str) -> str:
    return text.lower().strip().rstrip("?!.,¿¡").strip()


def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def is_chitchat(message: str) -> bool:
    """Return True if the message is trivial conversational filler.

    Triggers the short-circuit path that skips the full RAG pipeline.
    Conservative: only short inputs that clearly do not ask a legal question.

    A message is chitchat when ALL of its significant (non-stopword) tokens
    belong to the chitchat vocabulary. Length is capped at 8 words to avoid
    false-positives on longer, substantive questions that happen to start
    with a greeting.
    """
    clean = _normalize(message)
    if not clean:
        return True

    # Messages that are just emojis / punctuation
    if _CHITCHAT_EMOJI_ONLY.match(clean):
        return True

    # Very short inputs (<4 chars) are almost always filler
    if len(clean) < 4:
        return True

    tokens = _tokenize(clean)
    if not tokens:
        return True

    # Hard cap: longer inputs are probably real questions even if they
    # start with "hola". Let the RAG pipeline handle them.
    if len(tokens) > 8:
        return False

    # Every significant (non-stopword) token must be in the chitchat vocab.
    significant = [t for t in tokens if t not in _CHITCHAT_STOPWORDS]
    if not significant:
        # Only stopwords → too ambiguous, send to RAG
        return False

    return all(t in _CHITCHAT_TOKENS for t in significant)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    sources: list = []
    session_id: str = ""


@router.post("/", response_model=None)
async def chat(request: ChatRequest):
    """Send a message and get a response (JSON or streaming)."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    agent = await _get_agent()
    session_id = request.session_id or RAGAgent.new_session_id()
    chitchat = is_chitchat(request.message)

    if chitchat:
        logger.info("Chitchat short-circuit triggered: %r", request.message[:60])

    if request.stream:
        async def stream_generator():
            if chitchat:
                async for chunk in agent.chat_chitchat_stream(
                    request.message, session_id=session_id
                ):
                    yield chunk
            else:
                async for chunk in agent.chat_stream(
                    request.message, session_id=session_id
                ):
                    yield chunk

        return StreamingResponse(
            stream_generator(),
            media_type="application/x-ndjson",
            headers={
                "X-Session-Id": session_id,
                "X-Intent": "chitchat" if chitchat else "knowledge",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    if chitchat:
        result = await agent.chat_chitchat(request.message, session_id=session_id)
    else:
        result = await agent.chat(request.message, session_id=session_id)

    return ChatResponse(
        response=result["response"],
        intent=result.get("intent"),
        sources=result.get("sources", []),
        session_id=result["session_id"],
    )


@router.post("/reset")
async def reset_session():
    """Generate a fresh session ID for a new conversation."""
    new_id = RAGAgent.new_session_id()
    return {"status": "reset", "new_session_id": new_id}


@router.post("/attach")
async def attach_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload and ingest a file to be used in the current chat session."""
    from ingestion.pipeline import IngestionPipeline
    from utils.db import get_storage
    from config.schema import load_config
    import uuid
    from pathlib import Path

    config = load_config()
    storage = await get_storage(config.storage)

    # Save file temporarily
    upload_dir = Path(".cache/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file.txt").suffix
    temp_path = upload_dir / f"{uuid.uuid4()}{ext}"

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        # Ingest synchronously (user waits)
        pipeline = IngestionPipeline(config, storage)
        doc_id = await pipeline.ingest_file(
            str(temp_path),
            original_filename=file.filename,
        )

        if not doc_id:
            raise HTTPException(400, "Could not process file")

        # Get chunk count
        docs = await storage.list_documents()
        chunk_count = 0
        for d in docs:
            if d["id"] == doc_id:
                chunk_count = d.get("chunk_count", 0)
                break

        # Save attachment reference
        await storage.save_chat_attachment(session_id, doc_id, file.filename or "file", chunk_count)

        # Invalidate doc cache in agent
        agent = await _get_agent()
        agent.invalidate_doc_cache()

        return {
            "status": "ok",
            "doc_id": doc_id,
            "filename": file.filename,
            "chunk_count": chunk_count,
        }
    except Exception as e:
        logger.error(f"File attach failed: {e}")
        raise HTTPException(500, f"Error processing file: {str(e)}")
    finally:
        temp_path.unlink(missing_ok=True)
