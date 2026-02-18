"""Document parsing and chunking (aligned with lib/document-parser.ts)."""
from pathlib import Path


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    words = [w for w in text.split() if w]
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


def parse_document(file_path: str | Path) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    raw = path.read_bytes()

    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")

    if ext == ".pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()

    if ext == ".docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()

    raise ValueError(f"Unsupported file type: {ext}")
