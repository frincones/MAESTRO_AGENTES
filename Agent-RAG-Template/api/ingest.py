"""Ingestion endpoints: upload and process documents."""

from __future__ import annotations

import os
import tempfile
import logging
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from config.schema import load_config
from ingestion.pipeline import IngestionPipeline
from utils.db import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestTextRequest(BaseModel):
    text: str
    title: str = "Untitled"
    source: str = "api_input"
    doc_type: str = "text"


class IngestDirectoryRequest(BaseModel):
    directory: str
    clean_before: bool = False


@router.post("/text")
async def ingest_text(request: IngestTextRequest):
    """Ingest raw text directly into the knowledge base."""
    config = load_config()
    storage = await get_storage()
    pipeline = IngestionPipeline(config, storage)

    doc_id = await pipeline.ingest_text(
        text=request.text,
        title=request.title,
        source=request.source,
        doc_type=request.doc_type,
    )

    if doc_id is None:
        raise HTTPException(status_code=400, detail="Failed to ingest text")

    return {"status": "ingested", "document_id": doc_id}


@router.post("/files")
async def ingest_files(files: List[UploadFile] = File(...)):
    """Upload and ingest one or more files."""
    config = load_config()
    storage = await get_storage()
    pipeline = IngestionPipeline(config, storage)

    results = []
    for file in files:
        try:
            # Save uploaded file to temp location
            suffix = os.path.splitext(file.filename or "file.txt")[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            doc_id = await pipeline.ingest_file(tmp_path)

            if doc_id:
                results.append({
                    "file": file.filename,
                    "status": "success",
                    "document_id": doc_id,
                })
            else:
                results.append({
                    "file": file.filename,
                    "status": "failed",
                    "error": "Empty or unsupported content",
                })

        except Exception as e:
            logger.error("Failed to ingest %s: %s", file.filename, e)
            results.append({
                "file": file.filename,
                "status": "failed",
                "error": str(e),
            })
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    successful = sum(1 for r in results if r["status"] == "success")
    return {
        "total": len(files),
        "successful": successful,
        "failed": len(files) - successful,
        "results": results,
    }


@router.post("/directory")
async def ingest_directory(request: IngestDirectoryRequest):
    """Ingest all supported files from a directory."""
    if not os.path.isdir(request.directory):
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.directory}")

    config = load_config()
    storage = await get_storage()
    pipeline = IngestionPipeline(config, storage)

    result = await pipeline.ingest_directory(
        directory=request.directory,
        clean_before=request.clean_before,
    )

    return result.to_dict()
