"""LLM client factory for primary and utility models."""

from __future__ import annotations

import os
from typing import List, Optional

from openai import AsyncOpenAI


_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create a shared AsyncOpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


async def llm_generate(
    prompt: str,
    model: str = "gpt-4o-mini",
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 500,
) -> str:
    """Simple LLM text generation helper."""
    client = get_openai_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


async def llm_generate_embedding(
    text: str,
    model: str = "text-embedding-3-small",
) -> List[float]:
    """Generate a single embedding vector."""
    client = get_openai_client()
    response = await client.embeddings.create(
        model=model,
        input=text,
    )
    return response.data[0].embedding


async def llm_generate_embeddings_batch(
    texts: List[str],
    model: str = "text-embedding-3-small",
) -> List[List[float]]:
    """Generate embedding vectors for a batch of texts."""
    client = get_openai_client()
    response = await client.embeddings.create(
        model=model,
        input=texts,
    )
    return [item.embedding for item in response.data]
