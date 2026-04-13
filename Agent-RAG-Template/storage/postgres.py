"""PostgreSQL + pgVector storage backend (works with Supabase)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import asyncpg

from models.chunks import DocumentChunk
from models.documents import Document
from models.search import SearchResult
from storage.base import BaseStorage

logger = logging.getLogger(__name__)


def _embedding_to_pg(embedding: List[float]) -> str:
    """Convert Python list to PostgreSQL vector literal."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


class PostgresStorage(BaseStorage):
    """PostgreSQL + pgVector storage backend."""

    def __init__(
        self,
        connection_string: str,
        pool_min: int = 2,
        pool_max: int = 10,
        similarity_threshold: float = 0.7,
    ):
        self.connection_string = connection_string
        self.pool_min = pool_min
        self.pool_max = pool_max
        self.similarity_threshold = similarity_threshold
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=self.pool_min,
            max_size=self.pool_max,
            command_timeout=60,
        )
        logger.info("PostgreSQL connection pool initialized")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return self._pool

    # -- Document operations --

    async def save_document(
        self,
        document: Document,
        chunks: List[DocumentChunk],
    ) -> str:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO documents (title, source, content, doc_type, metadata)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    RETURNING id
                    """,
                    document.title,
                    document.source,
                    document.content,
                    document.doc_type,
                    json.dumps(document.metadata),
                )
                doc_id = str(row["id"])

                for chunk in chunks:
                    embedding_str = _embedding_to_pg(chunk.embedding) if chunk.has_embedding else None
                    await conn.execute(
                        """
                        INSERT INTO chunks (document_id, content, embedding, chunk_index, token_count, metadata)
                        VALUES ($1::uuid, $2, $3::vector, $4, $5, $6::jsonb)
                        """,
                        doc_id,
                        chunk.content,
                        embedding_str,
                        chunk.index,
                        chunk.token_count,
                        json.dumps(chunk.metadata),
                    )

                logger.info("Saved document '%s' with %d chunks", document.title, len(chunks))
                return doc_id

    async def get_document(self, document_id: str) -> Optional[Document]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, title, source, content, doc_type, metadata, created_at FROM documents WHERE id = $1::uuid",
                document_id,
            )
            if row is None:
                return None
            return Document(
                id=str(row["id"]),
                title=row["title"],
                source=row["source"],
                content=row["content"] or "",
                doc_type=row["doc_type"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )

    async def get_document_by_title(self, title: str) -> Optional[Document]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, title, source, content, doc_type, metadata, created_at FROM documents WHERE title ILIKE $1 LIMIT 1",
                f"%{title}%",
            )
            if row is None:
                return None
            return Document(
                id=str(row["id"]),
                title=row["title"],
                source=row["source"],
                content=row["content"] or "",
                doc_type=row["doc_type"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )

    async def list_documents(self) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT d.id, d.title, d.source, d.doc_type, d.created_at,
                       COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id
                ORDER BY d.created_at DESC
                """
            )
            return [
                {
                    "id": str(r["id"]),
                    "title": r["title"],
                    "source": r["source"],
                    "doc_type": r["doc_type"],
                    "chunk_count": r["chunk_count"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]

    async def delete_document(self, document_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM documents WHERE id = $1::uuid", document_id
            )
            deleted = result.split()[-1] != "0"
            if deleted:
                logger.info("Deleted document %s", document_id)
            return deleted

    async def clear_all(self) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM conversation_chunks")
                await conn.execute("DELETE FROM conversations")
                await conn.execute("DELETE FROM chunks")
                await conn.execute("DELETE FROM documents")
            logger.info("Cleared all data")

    # -- Search operations --

    async def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        threshold = similarity_threshold or self.similarity_threshold
        embedding_str = _embedding_to_pg(query_embedding)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM match_chunks($1::vector, $2, $3)",
                embedding_str,
                limit,
                threshold,
            )

        return [
            SearchResult(
                chunk_id=str(r["id"]),
                document_id=str(r["document_id"]),
                content=r["content"],
                similarity=float(r["similarity"]),
                metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                document_title=r["document_title"] or "",
                document_source=r["document_source"] or "",
            )
            for r in rows
        ]

    async def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3,
        similarity_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        threshold = similarity_threshold or 0.5
        embedding_str = _embedding_to_pg(query_embedding)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM hybrid_search($1::vector, $2, $3, $4, $5)",
                embedding_str,
                query_text,
                limit,
                text_weight,
                threshold,
            )

        return [
            SearchResult(
                chunk_id=str(r["chunk_id"]),
                document_id=str(r["document_id"]),
                content=r["content"],
                similarity=float(r["combined_score"]),
                metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                document_title=r["document_title"] or "",
                document_source=r["document_source"] or "",
            )
            for r in rows
        ]

    # -- Conversation memory --

    async def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        embedding: List[float],
        intent: Optional[str] = None,
        sources_used: Optional[List[str]] = None,
        relevance_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        combined_content = f"User: {user_message}\nAssistant: {assistant_message}"
        embedding_str = _embedding_to_pg(embedding)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                conv_row = await conn.fetchrow(
                    """
                    INSERT INTO conversations
                        (session_id, user_message, assistant_message, intent, sources_used, relevance_score, metadata)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::jsonb)
                    RETURNING id
                    """,
                    session_id,
                    user_message,
                    assistant_message,
                    intent,
                    json.dumps(sources_used or []),
                    relevance_score,
                    json.dumps(metadata or {}),
                )
                conv_id = str(conv_row["id"])

                await conn.execute(
                    """
                    INSERT INTO conversation_chunks
                        (conversation_id, content, embedding, session_id, metadata)
                    VALUES ($1::uuid, $2, $3::vector, $4, $5::jsonb)
                    """,
                    conv_id,
                    combined_content,
                    embedding_str,
                    session_id,
                    json.dumps({
                        "intent": intent,
                        "sources": sources_used or [],
                        **(metadata or {}),
                    }),
                )

        logger.debug("Saved conversation %s for session %s", conv_id, session_id)
        return conv_id

    async def search_conversations(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> List[SearchResult]:
        threshold = similarity_threshold or self.similarity_threshold
        embedding_str = _embedding_to_pg(query_embedding)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM match_conversations($1::vector, $2, $3, $4)",
                embedding_str,
                limit,
                threshold,
                session_id,
            )

        return [
            SearchResult(
                chunk_id=str(r["id"]),
                document_id=str(r["conversation_id"]),
                content=r["content"],
                similarity=float(r["similarity"]),
                metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                document_title=f"Conversation ({r['session_id']})",
                document_source="conversation_memory",
            )
            for r in rows
        ]

    async def search_all(
        self,
        query_embedding: List[float],
        doc_limit: int = 5,
        conv_limit: int = 3,
        similarity_threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        threshold = similarity_threshold or self.similarity_threshold
        embedding_str = _embedding_to_pg(query_embedding)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM match_all($1::vector, $2, $3, $4)",
                embedding_str,
                doc_limit,
                conv_limit,
                threshold,
            )

        return [
            SearchResult(
                chunk_id=str(r["id"]),
                document_id="",
                content=r["content"],
                similarity=float(r["similarity"]),
                metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                document_title=r["source_name"] or "",
                document_source=r["source_type"] or "",
            )
            for r in rows
        ]
