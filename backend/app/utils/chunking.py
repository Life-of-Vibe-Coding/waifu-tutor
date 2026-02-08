from collections.abc import Iterable


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(0, end - overlap)

    return chunks


def top_keywords(text: str, max_keywords: int = 5) -> list[str]:
    stop = {
        "the",
        "a",
        "an",
        "is",
        "of",
        "for",
        "and",
        "to",
        "in",
        "on",
        "with",
        "that",
        "it",
        "this",
        "as",
    }
    freq: dict[str, int] = {}
    for raw in text.lower().split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) < 4 or token in stop:
            continue
        freq[token] = freq.get(token, 0) + 1

    ranked = sorted(freq.items(), key=lambda item: item[1], reverse=True)
    return [token for token, _ in ranked[:max_keywords]]


def estimate_difficulty(word_count: int) -> str:
    if word_count < 500:
        return "easy"
    if word_count < 2000:
        return "medium"
    return "hard"


def safe_take(items: Iterable[str], limit: int) -> list[str]:
    result: list[str] = []
    for item in items:
        if len(result) >= limit:
            break
        result.append(item)
    return result
