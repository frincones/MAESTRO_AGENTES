"""Agent RAG Template - Main entry point."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.schema import load_config
from utils.db import get_storage, close_storage
from utils.logger import setup_logger

logger = setup_logger("agent-rag", level=os.getenv("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    config = load_config()
    logger.info("Starting Agent RAG Template: %s (%s)", config.agent.name, config.agent.role)

    # Initialize storage on startup
    storage = await get_storage(config.storage)
    logger.info("Storage initialized: %s", config.storage.provider)

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

app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


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
