"""Base agent: orchestrates retrieval pipeline + LLM response + conversation memory."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional

from config.schema import AppConfig
from ingestion.conversation_memory import ConversationMemory
from ingestion.embedder import create_embedder
from retrieval.pipeline import RetrievalPipeline
from storage.base import BaseStorage
from agent.system_prompts import build_system_prompt
from agent.response_builder import (
    build_context,
    get_sources,
    get_confidence,
    format_response_with_sources,
    sanitize_llm_response,
)
from utils.llm import get_openai_client

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Stateless RAG agent that:
    1. Loads conversation history from storage per session
    2. Routes query through retrieval pipeline (RAG-first)
    3. Builds context from retrieved data
    4. Generates response using primary LLM
    5. Persists exchange back to conversation memory
    """

    def __init__(self, config: AppConfig, storage: BaseStorage):
        self.config = config
        self.storage = storage
        self.retrieval = RetrievalPipeline(config, storage)
        self.embedder = create_embedder(
            model=config.ingestion.embedding.model,
            use_cache=True,
        )
        self.memory = ConversationMemory(
            storage=storage,
            embedder=self.embedder,
            utility_model=config.agent.utility_model,
        )
        # TTL cache for the allow-list of loaded document titles.
        # Refreshed every 5 min or when invalidated manually after ingestion.
        self._allow_list_cache: Optional[List[str]] = None
        self._allow_list_cached_at: float = 0.0
        self._allow_list_ttl_s: float = 300.0  # 5 minutes

    async def _build_messages(
        self,
        message: str,
        session_id: str,
        history_limit: int = 10,
    ) -> tuple[List[Dict[str, str]], dict]:
        """Build the message list for the LLM, including system prompt and history.

        The retrieval query is enriched with conversation history so that short
        follow-up messages like "y si yo me robé una computadora" carry the
        context of the previous exchange (in this case, "despido"). Without this,
        the RAG would search only for "robo" and miss the laboral chunks.
        """

        # Step 1: Load conversation history FIRST (we need it for query expansion)
        history: list = []
        try:
            history = await self.storage.get_session_messages(session_id)
        except Exception as e:
            logger.debug("Could not load history for session %s: %s", session_id, e)

        # Step 2: Build a "contextualized query" for retrieval that combines
        # recent conversation context with the new user message. This helps
        # the RAG find relevant chunks even on short follow-up turns.
        retrieval_query = self._build_retrieval_query(message, history)

        # Step 3: Retrieve context using the enriched query
        retrieval_result = await self.retrieval.retrieve(
            query=retrieval_query,
            session_id=session_id,
        )

        # Always preserve the user's actual message for display/logging purposes
        retrieval_result.query.original_query = message

        context = build_context(retrieval_result)
        sources = get_sources(retrieval_result)
        confidence = get_confidence(retrieval_result)
        intent = (
            retrieval_result.query.intent.value
            if retrieval_result.query.intent
            else "knowledge"
        )

        # Load the full list of documents in the corpus for the allow-list.
        # Cached with 5-min TTL: avoids hitting Postgres on every chat turn.
        loaded_doc_titles = await self._get_loaded_doc_titles()

        system_prompt = build_system_prompt(
            agent_name=self.config.agent.name,
            agent_role=self.config.agent.role,
            context=context,
            intent=intent,
            sources=sources,
            confidence=confidence,
            was_refined=retrieval_result.was_refined,
            refined_query=retrieval_result.refined_query,
            custom_template=self.config.agent.system_prompt_template,
            loaded_documents=loaded_doc_titles,
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Step 4: Append recent history so the LLM has full conversation context
        if history:
            tail = history[-(history_limit * 2):]
            for h in tail:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": message})

        meta = {
            "intent": intent,
            "sources": sources,
            "context": context,
            "retrieval_result": retrieval_result,
            "retrieval_query": retrieval_query,
            "loaded_documents": loaded_doc_titles,
        }
        return messages, meta

    def _build_retrieval_query(self, message: str, history: list) -> str:
        """Combine recent conversation context with the new message.

        This is critical for follow-up turns. Example:
        - Previous: "me quieren despedir y cumplo mis funciones"
        - New: "pero me robé una computadora"
        - Combined: the second message is enriched with "despido / trabajo /
          empleador" context so vector search finds laboral chunks instead
          of treating "robo" as a pure penal term.
        """
        if not history:
            return message

        # Take the last 2-3 user messages (most recent context wins)
        recent_user_msgs = [
            h["content"] for h in history[-6:]
            if h.get("role") == "user"
        ]

        # If no prior user messages, just use the new one
        if not recent_user_msgs:
            return message

        # Concatenate previous user messages with the new one for retrieval.
        # We use the user side only (not the assistant) because:
        # 1. The user's words contain the situation
        # 2. The assistant's reply is verbose and would dilute embeddings
        previous_context = " ".join(recent_user_msgs[-2:])  # last 2 user turns
        combined = f"{previous_context} {message}"

        # Cap at ~500 chars to keep embedding tokens reasonable
        if len(combined) > 500:
            combined = combined[-500:]

        return combined

    async def chat(self, message: str, session_id: Optional[str] = None) -> Dict:
        """Process a user message and return the agent's response."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())

        messages, meta = await self._build_messages(message, session_id)

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
        )

        if response.usage:
            tracker.record_chat(
                model=self.config.agent.primary_model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                purpose="main_response",
                session_id=session_id,
            )

        assistant_message = response.choices[0].message.content.strip()
        assistant_message = sanitize_llm_response(
            assistant_message, allowed_documents=meta.get("loaded_documents")
        )
        assistant_message = format_response_with_sources(
            assistant_message, meta["retrieval_result"]
        )

        # ALWAYS persist chat history (lightweight) so the next message in
        # this session can see the previous turns.
        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent=meta["intent"],
            sources_used=meta["sources"],
        )

        # Optionally persist exchange to conversation memory (heavyweight, with
        # embeddings). Background task — does not block the response.
        self._schedule_memory_save(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent=meta["intent"],
            sources_used=meta["sources"],
        )

        return {
            "response": assistant_message,
            "intent": meta["intent"],
            "sources": meta["sources"],
            "session_id": session_id,
        }

    async def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Process a user message and stream the response."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())

        messages, meta = await self._build_messages(message, session_id)

        client = get_openai_client()

        full_response = ""
        stream = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            # Final chunk with usage stats has no choices
            if chunk.usage:
                tracker.record_chat(
                    model=self.config.agent.primary_model,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                    purpose="main_response_stream",
                    session_id=session_id,
                )
                continue

            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        # Sanitize the full response (strip hallucinated norm references)
        full_response = sanitize_llm_response(
            full_response, allowed_documents=meta.get("loaded_documents")
        )

        # Append sources at the end
        sources = meta["sources"]
        if sources:
            source_footer = "\n\n---\n**Fuentes:**\n" + "\n".join(f"- {s}" for s in sources)
            yield source_footer
            full_response += source_footer

        # ALWAYS persist chat history (lightweight) for in-session context
        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent=meta["intent"],
            sources_used=sources,
        )

        # Optional: heavyweight RAG memory save (background, non-blocking)
        self._schedule_memory_save(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent=meta["intent"],
            sources_used=sources,
        )

    async def _build_chitchat_messages(
        self,
        message: str,
        session_id: str,
        history_limit: int = 6,
    ) -> List[Dict[str, str]]:
        """Build a minimal message list for chitchat turns (no retrieval).

        Used by chat_chitchat / chat_chitchat_stream to short-circuit the RAG
        pipeline for trivial turns like greetings, thanks, and farewells.
        Skips: embedding, hybrid_search, cross-encoder rerank, sources footer.
        Result: time-to-first-token drops from ~3s to ~0.5s.
        """
        history: list = []
        try:
            history = await self.storage.get_session_messages(session_id)
        except Exception as e:
            logger.debug("Could not load history for session %s: %s", session_id, e)

        system_prompt = (
            f"Eres {self.config.agent.name}, {self.config.agent.role}. "
            "El usuario te ha enviado un saludo, agradecimiento o mensaje conversacional "
            "breve que no requiere consultar documentos. Responde de forma cordial, "
            "concisa (1-2 frases) y en el mismo idioma del usuario. No inventes citas "
            "legales. Si el usuario quiere una consulta real, invitalo a formularla."
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            tail = history[-(history_limit * 2):]
            for h in tail:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": message})
        return messages

    async def chat_chitchat(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict:
        """Lightweight chat path for greetings / trivial turns. No RAG."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())
        messages = await self._build_chitchat_messages(message, session_id)

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
        )

        if response.usage:
            tracker.record_chat(
                model=self.config.agent.primary_model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                purpose="chitchat",
                session_id=session_id,
            )

        assistant_message = (response.choices[0].message.content or "").strip()

        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent="chitchat",
            sources_used=[],
        )

        return {
            "response": assistant_message,
            "intent": "chitchat",
            "sources": [],
            "session_id": session_id,
        }

    async def chat_chitchat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming variant of chat_chitchat. No RAG pipeline."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())
        messages = await self._build_chitchat_messages(message, session_id)

        client = get_openai_client()
        full_response = ""
        stream = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.usage:
                tracker.record_chat(
                    model=self.config.agent.primary_model,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                    purpose="chitchat_stream",
                    session_id=session_id,
                )
                continue

            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent="chitchat",
            sources_used=[],
        )

    async def _save_chat_history(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str,
        sources_used: list,
    ) -> None:
        """Lightweight chat history save (no embeddings, no LLM calls).

        Always runs so the next user turn in the same session can see the
        previous exchange via get_session_messages(). Independent from the
        heavier RAG memory (save_to_rag) which embeds and re-ranks past
        conversations as additional retrieval context.
        """
        try:
            await self.storage.save_chat_message(
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                intent=intent,
                sources_used=sources_used,
            )
        except Exception as e:
            logger.warning("Chat history save failed (non-fatal): %s", e)

    def _schedule_memory_save(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str,
        sources_used: list,
    ) -> None:
        """Schedule a non-blocking RAG conversation memory save.

        This is for SEMANTIC search of past conversations (heavyweight: embedding
        + relevance grading + summary). Skipped entirely if
        conversation_memory.save_to_rag is disabled.

        Note: chat history persistence (for in-session context) is handled by
        _save_chat_history and runs unconditionally.
        """
        if not self.config.retrieval.conversation_memory.save_to_rag:
            return

        async def _do_save():
            try:
                await self.memory.process_exchange(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    intent=intent,
                    sources_used=sources_used,
                )
            except Exception as e:
                logger.debug("Background conversation memory save failed: %s", e)

        try:
            asyncio.create_task(_do_save())
        except RuntimeError:
            # No running loop — skip silently
            pass

    async def _get_loaded_doc_titles(self) -> List[str]:
        """Return the allow-list of loaded document titles, cached for 5 min.

        The allow-list drives the anti-hallucination layer in the system prompt.
        Reading it from Postgres on every turn cost ~100-200ms per query; this
        cache brings it down to <1ms on the hot path. Cache is invalidated
        automatically on TTL expiry and manually via `invalidate_doc_cache()`
        after document ingestion or deletion.
        """
        now = time.monotonic()
        if (
            self._allow_list_cache is not None
            and (now - self._allow_list_cached_at) < self._allow_list_ttl_s
        ):
            return self._allow_list_cache

        try:
            all_docs_meta = await self.storage.list_documents()
            titles = [
                d["title"] for d in all_docs_meta
                if d.get("status") in (None, "completed")
                and "tmp" not in (d.get("title") or "").lower()
            ]
        except Exception as e:
            logger.debug("Could not load document allow-list: %s", e)
            titles = self._allow_list_cache or []

        self._allow_list_cache = titles
        self._allow_list_cached_at = now
        return titles

    def invalidate_doc_cache(self) -> None:
        """Force the next query to reload the document allow-list from DB.

        Call this after ingesting or deleting a document so that the prompt
        reflects the current corpus on the next user turn.
        """
        self._allow_list_cache = None
        self._allow_list_cached_at = 0.0

    @staticmethod
    def new_session_id() -> str:
        """Generate a new session ID."""
        return str(uuid.uuid4())
