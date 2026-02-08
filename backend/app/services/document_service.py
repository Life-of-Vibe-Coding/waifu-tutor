from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import DEMO_USER_ID
from app.models import Document, DocumentChunk, Summary
from app.services.ai_service import AIService
from app.services.parsers.base import UnsupportedDocumentError
from app.services.parsers.registry import parse_document
from app.services.vector_service import VectorService
from app.utils.chunking import chunk_text, estimate_difficulty, top_keywords

logger = logging.getLogger(__name__)


class DocumentService:
    ALLOWED_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def __init__(self, ai_service: AIService, vector_service: VectorService) -> None:
        self.ai_service = ai_service
        self.vector_service = vector_service
        self.settings = get_settings()
        Path(self.settings.upload_dir).mkdir(parents=True, exist_ok=True)

    async def create_document(self, db: Session, upload: UploadFile) -> Document:
        content = await upload.read()
        size = len(content)
        if size == 0:
            raise ValueError("Uploaded file is empty")
        if size > self.settings.max_upload_bytes:
            raise ValueError(f"File exceeds max upload size ({self.settings.max_upload_bytes} bytes)")

        suffix = Path(upload.filename or "document.txt").suffix.lower()
        mime = upload.content_type or "application/octet-stream"

        allowed_suffixes = {".pdf", ".docx", ".txt", ".md"}
        if suffix not in allowed_suffixes:
            raise ValueError("Unsupported file extension")
        if mime not in self.ALLOWED_MIME_TYPES and suffix in {".pdf", ".docx"}:
            raise ValueError("Unsupported MIME type")

        doc_id = str(uuid4())
        safe_name = f"{doc_id}{suffix}"
        storage_path = Path(self.settings.upload_dir) / safe_name
        storage_path.write_bytes(content)

        document = Document(
            id=doc_id,
            user_id=DEMO_USER_ID,
            title=Path(upload.filename or safe_name).stem,
            filename=upload.filename or safe_name,
            mime_type=mime,
            size_bytes=size,
            status="processing",
            word_count=0,
            topic_hint=None,
            difficulty_estimate=None,
            storage_path=str(storage_path),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        self._process_document(db=db, document=document, path=storage_path)
        db.refresh(document)
        return document

    def _process_document(self, db: Session, document: Document, path: Path) -> None:
        try:
            raw_text = parse_document(path)
            raw_text = raw_text.strip()
            if not raw_text:
                raise ValueError("No readable text extracted from document")

            chunks = chunk_text(raw_text)
            word_count = len(raw_text.split())
            keywords = top_keywords(raw_text, max_keywords=3)

            db.execute(delete(DocumentChunk).where(DocumentChunk.doc_id == document.id))

            chunk_rows: list[DocumentChunk] = []
            payloads: list[dict[str, Any]] = []
            for idx, chunk in enumerate(chunks):
                chunk_id = str(uuid4())
                chunk_row = DocumentChunk(
                    id=chunk_id,
                    doc_id=document.id,
                    chunk_index=idx,
                    chunk_text=chunk,
                    page=None,
                    section=None,
                )
                chunk_rows.append(chunk_row)
                payloads.append(
                    {
                        "chunk_id": chunk_id,
                        "doc_id": document.id,
                        "chunk_index": idx,
                        "chunk_text": chunk,
                        "title": document.title,
                        "page": None,
                        "section": None,
                        "created_at": document.created_at.isoformat(),
                    }
                )

            db.add_all(chunk_rows)
            document.word_count = word_count
            document.topic_hint = ", ".join(keywords) if keywords else None
            document.difficulty_estimate = estimate_difficulty(word_count)

            vectors = self.ai_service.embed([chunk.chunk_text for chunk in chunk_rows]) if chunk_rows else []
            self.vector_service.upsert_chunks(vectors=vectors, payloads=payloads)

            summary_text = self.ai_service.summarize(db=db, text=raw_text, detail_level="medium")
            db.add(
                Summary(
                    doc_id=document.id,
                    detail_level="medium",
                    summary_text=summary_text,
                    token_usage=0,
                )
            )

            document.status = "ready"
            db.commit()
        except UnsupportedDocumentError as exc:
            document.status = "failed"
            db.commit()
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            db.rollback()
            with db.begin():
                doc = db.get(Document, document.id)
                if doc:
                    doc.status = "failed"
            logger.exception("Failed to process document %s", document.id)
            raise RuntimeError("Document processing failed") from exc

    def get_document(self, db: Session, doc_id: str) -> Document | None:
        return db.scalar(select(Document).where(Document.id == doc_id, Document.user_id == DEMO_USER_ID))

    def list_documents(self, db: Session) -> list[Document]:
        return list(
            db.scalars(
                select(Document)
                .where(Document.user_id == DEMO_USER_ID)
                .order_by(Document.created_at.desc())
            ).all()
        )

    def delete_document(self, db: Session, doc_id: str) -> bool:
        doc = self.get_document(db, doc_id)
        if not doc:
            return False

        try:
            path = Path(doc.storage_path)
            if path.exists():
                path.unlink()
        except Exception:
            logger.warning("Failed to remove file for doc_id=%s", doc_id)

        self.vector_service.delete_document(doc_id)
        db.delete(doc)
        db.commit()
        return True
