from pathlib import Path

from app.services.parsers.base import DocumentParser


class PlainTextParser(DocumentParser):
    supported_suffixes = {".txt", ".md"}

    def parse(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
