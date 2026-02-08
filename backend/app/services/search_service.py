from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.services.vector_service import VectorService


class SearchService:
    def __init__(self, ai_service: AIService, vector_service: VectorService) -> None:
        self.ai_service = ai_service
        self.vector_service = vector_service

    def keyword_search(self, db: Session, query: str, doc_id: str | None = None, limit: int = 6) -> list[dict]:
        if doc_id:
            stmt = text(
                """
                SELECT dc.id as chunk_id, dc.doc_id, dc.chunk_text as text,
                       bm25(document_chunks_fts) as score
                FROM document_chunks_fts
                JOIN document_chunks dc ON dc.rowid = document_chunks_fts.rowid
                WHERE document_chunks_fts MATCH :query AND dc.doc_id = :doc_id
                ORDER BY bm25(document_chunks_fts)
                LIMIT :limit
                """
            )
            params = {"query": query, "doc_id": doc_id, "limit": limit}
        else:
            stmt = text(
                """
                SELECT dc.id as chunk_id, dc.doc_id, dc.chunk_text as text,
                       bm25(document_chunks_fts) as score
                FROM document_chunks_fts
                JOIN document_chunks dc ON dc.rowid = document_chunks_fts.rowid
                WHERE document_chunks_fts MATCH :query
                ORDER BY bm25(document_chunks_fts)
                LIMIT :limit
                """
            )
            params = {"query": query, "limit": limit}

        try:
            rows = db.execute(stmt, params).mappings().all()
        except Exception:
            return []
        return [
            {
                "chunk_id": str(row["chunk_id"]),
                "doc_id": row["doc_id"],
                "text": row["text"],
                "score": float(-row["score"]),  # bm25 lower is better; invert for uniform ranking
                "source": "keyword",
            }
            for row in rows
        ]

    def semantic_search(self, query: str, doc_id: str | None = None, limit: int = 6) -> list[dict]:
        vectors = self.ai_service.embed([query])
        candidates = self.vector_service.semantic_search(query_vector=vectors[0], limit=limit * 2)
        if doc_id:
            candidates = [item for item in candidates if item.get("doc_id") == doc_id]
        return candidates[:limit]

    def hybrid_search(self, db: Session, query: str, doc_id: str | None = None, limit: int = 6) -> list[dict]:
        keyword = self.keyword_search(db=db, query=query, doc_id=doc_id, limit=limit)
        semantic = self.semantic_search(query=query, doc_id=doc_id, limit=limit)

        merged: dict[str, dict] = {}
        for item in keyword + semantic:
            key = item["chunk_id"]
            if key not in merged:
                merged[key] = item
                continue
            merged[key]["score"] = max(merged[key]["score"], item["score"])
            if merged[key]["source"] != item["source"]:
                merged[key]["source"] = "semantic" if item["source"] == "semantic" else "keyword"

        ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
        return ranked[:limit]
