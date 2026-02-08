from pathlib import Path


class UnsupportedDocumentError(Exception):
    pass


class DocumentParser:
    supported_suffixes: set[str] = set()

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.supported_suffixes

    def parse(self, path: Path) -> str:
        raise NotImplementedError
