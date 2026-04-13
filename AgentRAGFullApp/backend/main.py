"""Agent RAG Template - Main entry point."""

from __future__ import annotations

import logging
import os
import uvicorn

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

from config.schema import load_config
from utils.db import get_storage, close_storage
from utils.logger import setup_logger

logger = setup_logger("agent-rag", level=os.getenv("LOG_LEVEL", "INFO"))


async def _prewarm_openai():
    """Pre-warm the OpenAI HTTPS connection so the first user request
    doesn't pay the cold-start TLS handshake (~3s on first call).

    We send a tiny embedding request that establishes the keep-alive
    connection in the shared httpx pool. Subsequent requests reuse it.
    """
    try:
        from utils.llm import get_openai_client
        client = get_openai_client()
        # Tiny embedding to warm DNS + TLS + auth
        await client.embeddings.create(
            model="text-embedding-3-small",
            input="warmup",
        )
        logger.info("OpenAI connection pre-warmed")
    except Exception as e:
        logger.warning("OpenAI pre-warm failed (non-fatal): %s", e)


async def _prewarm_reranker():
    """Pre-load the cross-encoder model so the first re-ranking call
    doesn't pay the model download/load cost (~25s on first ever call,
    ~2s on subsequent cold loads after restart).
    """
    try:
        import asyncio
        from retrieval.reranker import _get_reranker

        # Run the synchronous model load in a thread to not block startup
        def _load():
            _get_reranker("cross-encoder/ms-marco-MiniLM-L-6-v2")

        await asyncio.to_thread(_load)
        logger.info("Cross-encoder re-ranker pre-loaded")
    except Exception as e:
        logger.warning("Re-ranker pre-warm failed (non-fatal): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    config = load_config()
    logger.info("Starting Agent RAG Template: %s (%s)", config.agent.name, config.agent.role)

    # Initialize storage on startup
    storage = await get_storage(config.storage)
    logger.info("Storage initialized: %s", config.storage.provider)

    # Pre-warm OpenAI connection to eliminate cold-start latency on first request
    await _prewarm_openai()

    # Pre-load the cross-encoder reranker model
    await _prewarm_reranker()

    # Initialize legal sources and derogation graph
    try:
        from legal_sources.source_router import LegalSourceRouter
        from derogation.graph import DerogationGraph
        from derogation.vigencia_checker import VigenciaChecker
        from ingestion.embedder import create_embedder
        from api.legal import init_legal_api

        legal_config = getattr(config, 'legal_sources', None)
        legal_config_dict = legal_config.model_dump() if legal_config else {}
        source_router = LegalSourceRouter(legal_config_dict)

        derogation_graph = DerogationGraph(storage.pool)
        vigencia_checker = VigenciaChecker(derogation_graph)
        embedder = create_embedder(
            model=config.ingestion.embedding.model,
            use_cache=True,
        )

        init_legal_api(source_router, derogation_graph, vigencia_checker, storage, embedder)
        logger.info("Legal sources and derogation graph initialized")
    except Exception as e:
        logger.warning("Legal system init failed (non-fatal): %s", e)

    yield

    # Cleanup on shutdown
    await close_storage()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Agent RAG Template",
    description="Customizable RAG agent with Level 3 ingestion and Level 5 retrieval",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from api.health import router as health_router
from api.chat import router as chat_router
from api.ingest import router as ingest_router
from api.documents import router as documents_router
from api.sessions import router as sessions_router
from api.usage import router as usage_router
from api.legal import router as legal_router

app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(usage_router, prefix="/api")
app.include_router(legal_router)  # Already has /api/legal prefix


def main():
    """Run the application."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()
