"""Base agent: orchestrates retrieval pipeline + LLM response + conversation memory."""

from __future__ import annotations

import logging
import uuid
from typing import AsyncGenerator, Optional

from config.schema import AppConfig
from ingestion.conversation_memory import ConversationMemory
from ingestion.embedder import create_embedder
from models.agent import AgentState
from models.search import RetrievalResult
from retrieval.pipeline import RetrievalPipeline
from storage.base import BaseStorage
from agent.system_prompts import build_system_prompt
from agent.response_builder import (
    build_context,
    get_sources,
    get_confidence,
    format_response_with_sources,
)
from utils.llm import get_openai_client

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Main agent that:
    1. Routes query through retrieval pipeline (RAG-first)
    2. Builds context from retrieved data
    3. Generates response using primary LLM
    4. Stores relevant conversations back to RAG
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
        self.state = AgentState()
        self.session_id = str(uuid.uuid4())

    async def chat(self, message: str) -> str:
        """Process a user message and return the agent's response."""
        self.state.add_message("user", message)
        self.state.total_queries += 1

        # Step 1: Retrieve context (RAG-first, BEFORE LLM)
        retrieval_result = await self.retrieval.retrieve(
            query=message,
            session_id=self.session_id,
        )

        # Step 2: Build system prompt with retrieved context
        context = build_context(retrieval_result)
        sources = get_sources(retrieval_result)
        confidence = get_confidence(retrieval_result)
        intent = retrieval_result.query.intent.value if retrieval_result.query.intent else "knowledge"

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
        )

        # Step 3: Generate response using primary LLM
        client = get_openai_client()
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.state.get_history(max_messages=10))

        response = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
        )

        assistant_message = response.choices[0].message.content.strip()

        # Add source citations
        assistant_message = format_response_with_sources(assistant_message, retrieval_result)

        # Step 4: Update state
        self.state.add_message("assistant", assistant_message)
        self.state.last_retrieval_context = context
        self.state.last_intent = intent

        # Step 5: Store conversation in memory (async, non-blocking evaluation)
        try:
            await self.memory.process_exchange(
                session_id=self.session_id,
                user_message=message,
                assistant_message=assistant_message,
                intent=intent,
                sources_used=sources,
            )
        except Exception as e:
            logger.debug("Conversation memory save failed (non-critical): %s", e)

        return assistant_message

    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        """Process a user message and stream the response."""
        self.state.add_message("user", message)
        self.state.total_queries += 1

        # Step 1: Retrieve context (RAG-first)
        retrieval_result = await self.retrieval.retrieve(
            query=message,
            session_id=self.session_id,
        )

        # Step 2: Build prompt
        context = build_context(retrieval_result)
        sources = get_sources(retrieval_result)
        confidence = get_confidence(retrieval_result)
        intent = retrieval_result.query.intent.value if retrieval_result.query.intent else "knowledge"

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
        )

        # Step 3: Stream response
        client = get_openai_client()
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.state.get_history(max_messages=10))

        full_response = ""
        stream = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        # Append sources
        if sources:
            source_footer = "\n\n---\n**Sources:**\n" + "\n".join(f"- {s}" for s in sources)
            yield source_footer
            full_response += source_footer

        # Step 4: Update state and memory
        self.state.add_message("assistant", full_response)
        self.state.last_retrieval_context = context
        self.state.last_intent = intent

        try:
            await self.memory.process_exchange(
                session_id=self.session_id,
                user_message=message,
                assistant_message=full_response,
                intent=intent,
                sources_used=sources,
            )
        except Exception as e:
            logger.debug("Conversation memory save failed: %s", e)

    def reset_session(self) -> None:
        """Start a new conversation session."""
        self.state.clear()
        self.session_id = str(uuid.uuid4())
