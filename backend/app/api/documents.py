"""Documents: list, upload, get by id, subject patch."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.openviking_client import get_openviking_client, openviking_enabled
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
from app.services.file_search import doc_uri

router = APIRouter()

ALLOWED_EXT = (".pdf", ".docx", ".txt", ".md")


def _demo_user_id() -> str:
    return get_settings().demo_user_id


def _index_document_in_openviking(doc_id: str, storage_path: Path, title: str) -> tuple[bool, str | None, str | None]:
    if not openviking_enabled():
        return False, "openviking_disabled", None
    try:
        user_id = _demo_user_id()
        target = doc_uri(user_id, doc_id)
        client = get_openviking_client()
        client.add_resource(
            path=str(storage_path),
            target=target,
            reason=f"User uploaded study material: {title}",
            instruction="Index this study material for OpenViking context file search.",
            wait=False,
        )
        return True, None, target
    except Exception as e:
        return False, str(e), None


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
async def upload_doc(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail={"code": "invalid_document", "message": "No file"})
    content = await file.read()
    size = len(content)
    if size > get_settings().max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_document", "message": f"File exceeds max upload size ({get_settings().max_upload_bytes} bytes)"},
        )
    if size == 0:
        raise HTTPException(status_code=400, detail={"code": "invalid_document", "message": "File is empty"})
    name = file.filename or "document.txt"
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXT:
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
        indexed, index_error, ov_uri = _index_document_in_openviking(doc_id, storage_path, title)
        update_document_status(doc_id, "ready", word_count, openviking_uri=ov_uri)
        doc = get_document(doc_id, _demo_user_id())
        if doc is not None:
            doc["openviking_indexed"] = indexed
            if index_error:
                doc["openviking_error"] = index_error
            return doc
        payload = {
            "id": doc_id,
            "user_id": _demo_user_id(),
            "subject_id": None,
            "title": title,
            "filename": name,
            "mime_type": mime,
            "size_bytes": size,
            "status": "ready",
            "word_count": word_count,
            "topic_hint": None,
            "difficulty_estimate": None,
            "storage_path": str(storage_path),
            "openviking_uri": ov_uri,
            "created_at": "",
            "updated_at": "",
        }
        payload["openviking_indexed"] = indexed
        if index_error:
            payload["openviking_error"] = index_error
        return payload
    except Exception as e:
        update_document_status(doc_id, "failed")
        raise HTTPException(status_code=500, detail={"code": "processing_failed", "message": str(e)})
