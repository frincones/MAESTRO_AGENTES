"""Main ingestion pipeline orchestrator."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional

from config.schema import AppConfig
from models.chunks import ChunkingConfig, DocumentChunk
from models.documents import Document, IngestionResult
from ingestion.format_router import get_supported_extensions, read_file, chunk_content
from ingestion.metadata import extract_metadata
from ingestion.enrichment import enrich_chunks
from ingestion.embedder import create_embedder
from storage.base import BaseStorage

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the full document ingestion pipeline."""

    def __init__(self, config: AppConfig, storage: BaseStorage):
        self.config = config
        self.storage = storage
        self.embedder = create_embedder(
            model=config.ingestion.embedding.model,
            batch_size=config.ingestion.embedding.batch_size,
            max_retries=config.ingestion.embedding.max_retries,
            use_cache=config.ingestion.embedding.use_cache,
        )
        self.chunking_config = ChunkingConfig(
            chunk_size=config.ingestion.chunking.chunk_size,
            chunk_overlap=config.ingestion.chunking.chunk_overlap,
            max_tokens=config.ingestion.chunking.max_tokens,
            min_chunk_size=config.ingestion.chunking.min_chunk_size,
            use_semantic_splitting=config.ingestion.chunking.strategy != "simple",
            merge_peers=config.ingestion.chunking.merge_peers,
        )

    async def ingest_directory(
        self,
        directory: str,
        clean_before: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> IngestionResult:
        """Ingest all supported files from a directory."""
        start_time = time.time()
        result = IngestionResult()

        if clean_before:
            await self.storage.clear_all()
            logger.info("Cleared existing data")

        supported_ext = get_supported_extensions(self.config.ingestion.formats)
        files = self._find_files(directory, supported_ext)
        result.total_documents = len(files)

        logger.info("Found %d files to ingest in %s", len(files), directory)

        for i, file_path in enumerate(files):
            try:
                if progress_callback:
                    progress_callback(file_path, i + 1, len(files))

                doc_id = await self.ingest_file(str(file_path))

                if doc_id:
                    result.add_success(str(file_path), 0)
                    logger.info("[%d/%d] Ingested: %s", i + 1, len(files), file_path.name)
                else:
                    result.add_error(str(file_path), "Ingestion returned no document ID")

            except Exception as e:
                logger.error("[%d/%d] Failed: %s - %s", i + 1, len(files), file_path.name, e)
                result.add_error(str(file_path), str(e))

        result.duration_seconds = time.time() - start_time
        logger.info(
            "Ingestion complete: %d/%d successful, %d chunks, %.1fs",
            result.successful, result.total_documents,
            result.total_chunks, result.duration_seconds,
        )
        return result

    async def ingest_file(self, file_path: str) -> Optional[str]:
        """Ingest a single file through the full pipeline."""
        # Step 1: Read file
        content, docling_doc, reader_metadata = read_file(
            file_path, self.config.ingestion.formats
        )

        if not content or not content.strip():
            logger.warning("Empty content from %s", file_path)
            return None

        # Step 2: Extract metadata
        metadata = extract_metadata(content, file_path, reader_metadata)
        title = metadata.get("title", Path(file_path).stem)
        source = metadata.get("file_name", file_path)

        # Step 3: Chunk content
        chunks = chunk_content(
            content=content,
            chunking_config=self.chunking_config,
            title=title,
            source=source,
            metadata=metadata,
            docling_doc=docling_doc,
        )

        if not chunks:
            logger.warning("No chunks generated from %s", file_path)
            return None

        # Step 4: Contextual enrichment (optional)
        if self.config.ingestion.enrichment.enabled:
            chunks = await enrich_chunks(
                chunks=chunks,
                document_content=content,
                title=title,
                source=source,
                model=self.config.ingestion.enrichment.model,
                max_concurrent=self.config.ingestion.enrichment.max_concurrent,
                max_document_chars=self.config.ingestion.enrichment.max_document_chars,
            )

        # Step 5: Generate embeddings
        chunks = await self.embedder.embed_chunks(chunks)

        # Step 6: Save to storage
        document = Document(
            title=title,
            source=source,
            content=content,
            doc_type=metadata.get("reader", "unknown"),
            metadata=metadata,
        )

        doc_id = await self.storage.save_document(document, chunks)
        logger.info("Stored '%s' with %d chunks (id=%s)", title, len(chunks), doc_id)
        return doc_id

    async def ingest_text(
        self,
        text: str,
        title: str = "Untitled",
        source: str = "direct_input",
        doc_type: str = "text",
    ) -> Optional[str]:
        """Ingest raw text directly (not from file)."""
        if not text or not text.strip():
            return None

        metadata = {
            "reader": "direct",
            "format": "text",
            "title": title,
            "source": source,
        }

        chunks = chunk_content(
            content=text,
            chunking_config=self.chunking_config,
            title=title,
            source=source,
            metadata=metadata,
        )

        if not chunks:
            return None

        if self.config.ingestion.enrichment.enabled:
            chunks = await enrich_chunks(
                chunks=chunks,
                document_content=text,
                title=title,
                source=source,
                model=self.config.ingestion.enrichment.model,
                max_concurrent=self.config.ingestion.enrichment.max_concurrent,
                max_document_chars=self.config.ingestion.enrichment.max_document_chars,
            )

        chunks = await self.embedder.embed_chunks(chunks)

        document = Document(
            title=title,
            source=source,
            content=text,
            doc_type=doc_type,
            metadata=metadata,
        )

        return await self.storage.save_document(document, chunks)

    def _find_files(self, directory: str, extensions: set) -> List[Path]:
        """Find all supported files in a directory recursively."""
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error("Directory does not exist: %s", directory)
            return []

        files = []
        for ext in extensions:
            files.extend(dir_path.rglob(f"*{ext}"))

        # Sort by name for consistent ordering
        return sorted(set(files), key=lambda p: p.name.lower())
