"""Documents: list, upload, get by id, subject patch."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.openviking_client import index_document as openviking_index_document
from app.db.repositories import (
    delete_chunks_for_document,
    get_document,
    insert_chunk,
    insert_document,
    list_documents,
    set_document_subject,
    update_document_status,
)
from app.services.document_parser import chunk_text, parse_document

router = APIRouter()

ALLOWED_EXT = (".pdf", ".docx", ".txt", ".md")


def _demo_user_id() -> str:
    return get_settings().demo_user_id


@router.get("/list")
def list_docs() -> list:
    return list_documents(_demo_user_id())


@router.get("/{doc_id}")
def get_doc(doc_id: str) -> dict:
    doc = get_document(doc_id, _demo_user_id())
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Document not found"})
    return doc


class PatchDocBody(BaseModel):
    subject_id: str | None = None


@router.patch("/{doc_id}")
def patch_doc(doc_id: str, body: PatchDocBody) -> dict:
    doc = set_document_subject(doc_id, _demo_user_id(), body.subject_id)
    if not doc:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Document not found"})
    return doc


@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    folder_name: str | None = Form(None),
) -> dict:
    if not file.filename:
        print("Upload failed: No filename")
        raise HTTPException(status_code=400, detail={"code": "invalid_document", "message": "No file"})
    content = await file.read()
    size = len(content)
    max_bytes = get_settings().max_upload_bytes
    if size > max_bytes:
        print(f"Upload failed: Size {size} exceeds limit {max_bytes}")
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_document", "message": f"File exceeds max upload size ({max_bytes} bytes)"},
        )
    if size == 0:
        print("Upload failed: File is empty")
        raise HTTPException(status_code=400, detail={"code": "invalid_document", "message": "File is empty"})
    name = file.filename or "document.txt"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
        print(f"Upload failed: Unsupported extension {ext}")
        raise HTTPException(status_code=400, detail={"code": "invalid_document", "message": "Unsupported file extension"})

    doc_id = str(uuid.uuid4())
    upload_dir = Path(get_settings().upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{doc_id}{ext}"
    storage_path = upload_dir / safe_name
    storage_path.write_bytes(content)

    title = Path(name).stem
    mime = file.content_type or "application/octet-stream"
    insert_document(
        doc_id=doc_id,
        user_id=_demo_user_id(),
        title=title,
        filename=name,
        mime_type=mime,
        size_bytes=size,
        storage_path=str(storage_path),
        status="processing",
        source_folder=folder_name,
    )

    try:
        raw_text = parse_document(storage_path).strip()
        if not raw_text:
            raise ValueError("No readable text extracted from document")
        chunks_list = chunk_text(raw_text)
        delete_chunks_for_document(doc_id)
        for i, text in enumerate(chunks_list):
            chunk_id = str(uuid.uuid4())
            insert_chunk(chunk_id, doc_id, i, text, None, None)
        word_count = len(raw_text.split())
        openviking_uri = openviking_index_document(storage_path, doc_id)
        update_document_status(doc_id, "ready", word_count, openviking_uri=openviking_uri)
        doc = get_document(doc_id, _demo_user_id())
        if doc is not None:
            return doc
        return {
            "id": doc_id,
            "user_id": _demo_user_id(),
            "subject_id": None,
            "title": title,
            "filename": name,
            "source_folder": folder_name,
            "mime_type": mime,
            "size_bytes": size,
            "status": "ready",
            "word_count": word_count,
            "topic_hint": None,
            "difficulty_estimate": None,
            "storage_path": str(storage_path),
            "openviking_uri": openviking_uri,
            "created_at": "",
            "updated_at": "",
        }
    except Exception as e:
        update_document_status(doc_id, "failed")
        raise HTTPException(status_code=500, detail={"code": "processing_failed", "message": str(e)})
