from pathlib import Path

from PyPDF2 import PdfReader

from app.services.parsers.base import DocumentParser


class PDFParser(DocumentParser):
    supported_suffixes = {".pdf"}

    def parse(self, path: Path) -> str:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
