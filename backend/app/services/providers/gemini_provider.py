from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Any | None = None
        self._enabled = False

        if self.settings.gemini_api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.settings.gemini_api_key)
                self._enabled = True
            except Exception as exc:  # pragma: no cover - optional runtime path
                logger.warning("Gemini SDK unavailable, using fallback provider path: %s", exc)

    def summarize(self, text: str, detail_level: str) -> str:
        if self._enabled:
            prompt = (
                "You are an educational tutor. Summarize the document in "
                f"{detail_level} detail with key concepts and action items.\n\n{text[:12000]}"
            )
            try:
                response = self._client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=prompt,
                )
                text_out = getattr(response, "text", None)
                if text_out:
                    return text_out.strip()
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini summarize failed, using fallback: %s", exc)

        return self._fallback_summary(text, detail_level)

    def generate_flashcards(self, text: str, max_cards: int) -> list[dict[str, str]]:
        if self._enabled:
            prompt = (
                "Generate JSON array of flashcards with keys question, answer, explanation. "
                f"Return exactly {max_cards} cards.\n\n{text[:12000]}"
            )
            try:
                response = self._client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=prompt,
                )
                candidate = getattr(response, "text", "") or ""
                parsed = self._extract_json_array(candidate)
                if parsed:
                    return parsed[:max_cards]
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini flashcards failed, using fallback: %s", exc)

        return self._fallback_flashcards(text, max_cards)

    def chat(self, prompt: str, context: list[str]) -> str:
        context_block = "\n\n".join(context[:8])
        full_prompt = (
            "You are Waifu Tutor, an encouraging study companion. "
            "Answer clearly and cite relevant context when available.\n\n"
            f"Context:\n{context_block}\n\nUser question:\n{prompt}"
        )

        if self._enabled:
            try:
                response = self._client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=full_prompt,
                )
                text_out = getattr(response, "text", None)
                if text_out:
                    return text_out.strip()
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini chat failed, using fallback: %s", exc)

        return self._fallback_chat(prompt, context)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._enabled:
            try:
                vectors: list[list[float]] = []
                for text in texts:
                    response = self._client.models.embed_content(
                        model=self.settings.gemini_embed_model,
                        contents=text,
                    )
                    emb = getattr(response, "embeddings", None)
                    if emb:
                        values = emb[0].values
                    else:
                        values = getattr(response, "embedding", {}).get("values", [])
                    vectors.append(list(values)[: self.settings.embedding_dim])
                if vectors:
                    return [self._pad_vector(v) for v in vectors]
            except Exception as exc:  # pragma: no cover
                logger.warning("Gemini embedding failed, using fallback: %s", exc)

        return [self._deterministic_embedding(text) for text in texts]

    def _extract_json_array(self, text: str) -> list[dict[str, str]]:
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            return []
        return []

    def _fallback_summary(self, text: str, detail_level: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if detail_level == "short":
            take = 2
        elif detail_level == "detailed":
            take = 8
        else:
            take = 4

        selected = [s.strip() for s in sentences if s.strip()][:take]
        if not selected:
            selected = [text[:800].strip()]

        return "\n".join(f"- {line}" for line in selected if line)

    def _fallback_flashcards(self, text: str, max_cards: int) -> list[dict[str, str]]:
        lines = [line.strip() for line in re.split(r"[\n.!?]", text) if len(line.strip().split()) > 5]
        cards: list[dict[str, str]] = []
        for i, line in enumerate(lines[:max_cards]):
            short = " ".join(line.split()[:12])
            cards.append(
                {
                    "question": f"What is the key idea from statement {i + 1}?",
                    "answer": short,
                    "explanation": line,
                }
            )
        if not cards:
            cards.append(
                {
                    "question": "What is the main topic of this document?",
                    "answer": text[:120],
                    "explanation": "Generated fallback card because source text was sparse.",
                }
            )
        return cards

    def _fallback_chat(self, prompt: str, context: list[str]) -> str:
        context_prefix = "\n".join(f"- {chunk[:220]}" for chunk in context[:3])
        if context_prefix:
            return (
                "Here is a focused answer based on your document context:\n"
                f"{context_prefix}\n\n"
                f"Question interpretation: {prompt}\n"
                "Use these points to review and ask follow-up questions for deeper understanding."
            )
        return (
            "I can help with this question. Upload a document or ask for a summary/flashcards to get "
            "content-specific guidance."
        )

    def _deterministic_embedding(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        values = [rng.uniform(-1.0, 1.0) for _ in range(self.settings.embedding_dim)]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    def _pad_vector(self, vector: list[float]) -> list[float]:
        if len(vector) >= self.settings.embedding_dim:
            return vector[: self.settings.embedding_dim]
        return vector + [0.0] * (self.settings.embedding_dim - len(vector))
