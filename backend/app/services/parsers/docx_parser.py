from pathlib import Path

from docx import Document as DocxDocument

from app.services.parsers.base import DocumentParser


class DOCXParser(DocumentParser):
    supported_suffixes = {".docx"}

    def parse(self, path: Path) -> str:
        doc = DocxDocument(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
