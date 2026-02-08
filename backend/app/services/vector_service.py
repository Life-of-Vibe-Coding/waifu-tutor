from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.collection = self.settings.qdrant_collection
        self.client = QdrantClient(url=self.settings.qdrant_url)

    def ensure_collection(self) -> None:
        try:
            exists = self.client.collection_exists(collection_name=self.collection)
        except Exception as exc:
            logger.warning("Qdrant unavailable during ensure_collection: %s", exc)
            return

        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(
                    size=self.settings.embedding_dim,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            return

        info = self.client.get_collection(self.collection)
        vectors_cfg = info.config.params.vectors
        vector_size: int | None = None

        if hasattr(vectors_cfg, "size"):
            vector_size = vectors_cfg.size
        elif isinstance(vectors_cfg, dict):
            default_cfg = vectors_cfg.get("") or next(iter(vectors_cfg.values()), None)
            if default_cfg and hasattr(default_cfg, "size"):
                vector_size = default_cfg.size
            elif isinstance(default_cfg, dict):
                vector_size = default_cfg.get("size")

        if vector_size != self.settings.embedding_dim:
            raise RuntimeError(
                f"Collection vector size {vector_size} does not match configured "
                f"EMBEDDING_DIM {self.settings.embedding_dim}"
            )

    def upsert_chunks(self, vectors: list[list[float]], payloads: list[dict]) -> None:
        if not vectors:
            return
        points = [
            qmodels.PointStruct(id=payload["chunk_id"], vector=vector, payload=payload)
            for vector, payload in zip(vectors, payloads, strict=False)
        ]
        try:
            self.client.upsert(collection_name=self.collection, points=points)
        except Exception as exc:
            logger.warning("Qdrant upsert failed: %s", exc)

    def delete_document(self, doc_id: str) -> None:
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id))]
                    )
                ),
            )
        except Exception as exc:
            logger.warning("Qdrant delete failed: %s", exc)

    def semantic_search(self, query_vector: list[float], limit: int = 6) -> list[dict]:
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "chunk_id": str(item.id),
                    "doc_id": item.payload.get("doc_id"),
                    "text": item.payload.get("chunk_text", ""),
                    "score": float(item.score),
                    "source": "semantic",
                }
                for item in results
            ]
        except Exception as exc:
            logger.warning("Qdrant semantic search failed: %s", exc)
            return []
