"""OpenViking file search over the context filesystem (viking://).

Searches the virtual filesystem by URI scope (directory recursive retrieval),
returns L0/L1 content (abstract/overview) for matched nodes. Fallback: SQLite
document chunks when OpenViking is unavailable.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from app.core.viking_logging import log_viking_search
from app.db.repositories import get_chunks_for_document


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        out: dict[str, Any] = {}
        for f in fields(value):
            try:
                out[f.name] = _to_plain(getattr(value, f.name))
            except Exception:
                out[f.name] = None
        return out
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if hasattr(value, "__dict__") and not isinstance(value, (str, bytes, int, float, bool)):
        out: dict[str, Any] = {}
        for k, v in value.__dict__.items():
            if k.startswith("_"):
                continue
            try:
                out[k] = _to_plain(v)
            except Exception:
                continue
        if out:
            return out
    return value


def _doc_id_from_uri(uri: str) -> str | None:
    marker = "/documents/"
    if marker not in uri:
        return None
    tail = uri.split(marker, 1)[1].strip("/")
    if not tail:
        return None
    return tail.split("/", 1)[0]


def user_root_uri(user_id: str) -> str:
    """Base URI for a user's resources in the OpenViking filesystem."""
    return f"viking://resources/users/{user_id}"


def doc_uri(user_id: str, doc_id: str) -> str:
    """URI for a single document under the user's resources."""
    return f"{user_root_uri(user_id)}/documents/{doc_id}"


class ContextSearchService:
    """OpenViking file search: search the viking:// filesystem and load L0/L1 content."""

    def __init__(self, ov_client: Any | None):
        self.client = ov_client
        self.last_error: str | None = None
        self.last_trace: dict[str, Any] = {}

    def _fallback_document_chunks(self, doc_id: str | None, limit: int) -> list[dict[str, Any]]:
        if not doc_id:
            return []
        chunks = get_chunks_for_document(doc_id, limit=limit)
        return [
            {
                "chunk_id": c["id"],
                "doc_id": c["doc_id"],
                "text": c["chunk_text"],
                "source": "document",
                "score": 1.0,
                "uri": "",
            }
            for c in chunks
        ]

    def search(
        self,
        query: str,
        user_id: str,
        doc_id: str | None,
        limit: int = 5,
        session: Any | None = None,
        include_trace: bool = False,
    ) -> list[dict[str, Any]]:
        """Search the OpenViking context filesystem under the given scope.

        Uses directory recursive retrieval: target_uri is either a single
        document URI or the user root; OpenViking searches L0 abstracts
        then returns L1 overview (or L0 abstract) content for matched nodes.
        """
        self.last_error = None
        self.last_trace = {}
        if not self.client:
            self.last_error = "openviking_unavailable"
            self.last_trace = {"mode": "fallback", "reason": self.last_error}
            log_viking_search(query, "unavailable", 0, error=self.last_error)
            return self._fallback_document_chunks(doc_id, limit)

        target_uri = doc_uri(user_id, doc_id) if doc_id else user_root_uri(user_id)
        try:
            if session is not None:
                result = self.client.search(query, target_uri=target_uri, session=session, limit=limit)
            else:
                result = self.client.search(query, target_uri=target_uri, limit=limit)
        except Exception as e:
            self.last_error = str(e)
            self.last_trace = {"mode": "fallback", "target_uri": target_uri, "reason": self.last_error}
            log_viking_search(query, target_uri, 0, error=self.last_error)
            return self._fallback_document_chunks(doc_id, limit)

        result_dict = _to_plain(result)
        resources = getattr(result, "resources", None)
        if resources is None and isinstance(result_dict, dict):
            resources = result_dict.get("resources", [])
        resources = resources or []

        out: list[dict[str, Any]] = []
        for idx, raw_item in enumerate(resources):
            item = _to_plain(raw_item)
            uri = str(item.get("uri", "") or "")
            parsed_doc_id = _doc_id_from_uri(uri)
            # L1 (overview) then L0 (abstract) per OpenViking tiered loading
            text = (
                str(item.get("overview", "") or "").strip()
                or str(item.get("abstract", "") or "").strip()
                or str(item.get("match_reason", "") or "").strip()
            )
            if not text:
                continue
            out.append(
                {
                    "chunk_id": uri or f"ov-{idx}",
                    "doc_id": parsed_doc_id or doc_id or "",
                    "text": text,
                    "source": "semantic",
                    "score": float(item.get("score", 0.0) or 0.0),
                    "uri": uri,
                }
            )

        query_plan = result_dict.get("query_plan") if isinstance(result_dict, dict) else None
        query_results = result_dict.get("query_results") if isinstance(result_dict, dict) else None
        self.last_trace = {
            "mode": "openviking",
            "target_uri": target_uri,
            "result_count": len(out),
            "query_plan": query_plan if include_trace else None,
            "query_results": query_results if include_trace else None,
        }

        log_viking_search(query, target_uri, len(out))
        if out:
            return out[:limit]
        return self._fallback_document_chunks(doc_id, limit)

    @staticmethod
    def context_texts(items: list[dict[str, Any]]) -> list[str]:
        return [str(c.get("text", "")).strip() for c in items if str(c.get("text", "")).strip()]
