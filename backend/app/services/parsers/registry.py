from pathlib import Path

from app.services.parsers.base import UnsupportedDocumentError
from app.services.parsers.docx_parser import DOCXParser
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.text_parser import PlainTextParser


PARSERS = [PlainTextParser(), PDFParser(), DOCXParser()]


def parse_document(path: Path) -> str:
    for parser in PARSERS:
        if parser.can_parse(path):
            return parser.parse(path)
    raise UnsupportedDocumentError(f"Unsupported file type: {path.suffix}")
