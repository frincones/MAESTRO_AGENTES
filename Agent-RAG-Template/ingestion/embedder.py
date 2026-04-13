"""Embedding generator with batch processing, retry logic, and caching."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple

from models.chunks import DocumentChunk
from utils.llm import get_openai_client

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Simple LRU cache for embeddings keyed by content hash."""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._max_size = max_size

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        key = self._key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, text: str, embedding: List[float]) -> None:
        key = self._key(text)
        self._cache[key] = embedding
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


class EmbeddingGenerator:
    """Generate embeddings with batch processing, retry, and caching."""

    MODEL_CONFIGS = {
        "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
        "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
        "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
    }

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_cache: bool = True,
    ):
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = EmbeddingCache() if use_cache else None

        config = self.MODEL_CONFIGS.get(model, {"dimensions": 1536, "max_tokens": 8191})
        self.dimensions = config["dimensions"]
        self.max_tokens = config["max_tokens"]

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a single embedding with retry logic."""
        if self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                return cached

        client = get_openai_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.embeddings.create(
                    model=self.model,
                    input=text,
                )
                embedding = response.data[0].embedding

                if self.cache:
                    self.cache.put(text, embedding)

                return embedding

            except Exception as e:
                if "rate_limit" in str(e).lower():
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning("Rate limited. Retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, self.max_retries)
                    await asyncio.sleep(delay)
                elif attempt < self.max_retries - 1:
                    logger.warning("Embedding error: %s. Retrying (attempt %d/%d)", e, attempt + 1, self.max_retries)
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Embedding failed after %d attempts: %s", self.max_retries, e)
                    return [0.0] * self.dimensions

        return [0.0] * self.dimensions

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        client = get_openai_client()

        # Check cache first
        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            if self.cache:
                cached = self.cache.get(text)
                if cached is not None:
                    results[i] = cached
                    continue
            uncached_indices.append(i)
            uncached_texts.append(text)

        if not uncached_texts:
            return results  # type: ignore

        for attempt in range(self.max_retries):
            try:
                response = await client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                )

                for j, item in enumerate(response.data):
                    idx = uncached_indices[j]
                    results[idx] = item.embedding
                    if self.cache:
                        self.cache.put(uncached_texts[j], item.embedding)

                return [r if r is not None else [0.0] * self.dimensions for r in results]

            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning("Batch embedding error: %s. Retrying in %.1fs", e, delay)
                    await asyncio.sleep(delay)
                else:
                    logger.warning("Batch failed. Falling back to individual processing.")
                    return await self._process_individually(texts, results)

        return [r if r is not None else [0.0] * self.dimensions for r in results]

    async def _process_individually(
        self, texts: List[str], partial_results: List[Optional[List[float]]]
    ) -> List[List[float]]:
        """Fallback: process each text individually."""
        for i, text in enumerate(texts):
            if partial_results[i] is not None:
                continue
            partial_results[i] = await self.generate_embedding(text)
        return [r if r is not None else [0.0] * self.dimensions for r in partial_results]

    async def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[DocumentChunk]:
        """Embed all chunks in batches."""
        total = len(chunks)

        for i in range(0, total, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            texts = [c.content for c in batch]

            embeddings = await self.generate_embeddings_batch(texts)

            for j, embedding in enumerate(embeddings):
                chunks[i + j].embedding = embedding

            if progress_callback:
                progress_callback(min(i + len(batch), total), total)

            logger.debug("Embedded batch %d-%d / %d", i + 1, min(i + len(batch), total), total)

        embedded_count = sum(1 for c in chunks if c.has_embedding)
        logger.info("Embedded %d/%d chunks", embedded_count, total)
        return chunks


def create_embedder(
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
    max_retries: int = 3,
    use_cache: bool = True,
) -> EmbeddingGenerator:
    """Factory function for creating an embedding generator."""
    return EmbeddingGenerator(
        model=model,
        batch_size=batch_size,
        max_retries=max_retries,
        use_cache=use_cache,
    )
