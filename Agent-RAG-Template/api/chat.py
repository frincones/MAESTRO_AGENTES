"""Chat endpoint: main conversational interface."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.base_agent import RAGAgent
from config.schema import load_config
from utils.db import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Global agent instance (initialized on first request)
_agent: Optional[RAGAgent] = None


async def _get_agent() -> RAGAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        config = load_config()
        storage = await get_storage(config.storage)
        _agent = RAGAgent(config, storage)
        logger.info("Agent initialized: %s (%s)", config.agent.name, config.agent.role)
    return _agent


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    sources: list = []
    session_id: str = ""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and get a response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    agent = await _get_agent()

    # Set session if provided
    if request.session_id:
        agent.session_id = request.session_id

    if request.stream:
        async def stream_generator():
            async for chunk in agent.chat_stream(request.message):
                yield chunk

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
        )

    response = await agent.chat(request.message)

    return ChatResponse(
        response=response,
        intent=agent.state.last_intent,
        sources=[],
        session_id=agent.session_id,
    )


@router.post("/reset")
async def reset_session():
    """Reset the conversation session."""
    agent = await _get_agent()
    agent.reset_session()
    return {"status": "reset", "new_session_id": agent.session_id}
