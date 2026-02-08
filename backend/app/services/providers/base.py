from typing import Protocol


class AIProvider(Protocol):
    def summarize(self, text: str, detail_level: str) -> str:
        ...

    def generate_flashcards(self, text: str, max_cards: int) -> list[dict[str, str]]:
        ...

    def chat(self, prompt: str, context: list[str]) -> str:
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
