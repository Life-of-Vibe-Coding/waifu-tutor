from typing import Literal


Mood = Literal["happy", "encouraging", "sad", "neutral", "excited"]


def mood_from_score(score: int) -> Mood:
    if score >= 90:
        return "excited"
    if score >= 75:
        return "happy"
    if score >= 50:
        return "encouraging"
    return "sad"


def mood_from_text(text: str) -> Mood:
    lower = text.lower()
    if any(key in lower for key in ["great", "excellent", "awesome", "perfect"]):
        return "excited"
    if any(key in lower for key in ["good", "correct", "nice"]):
        return "happy"
    if any(key in lower for key in ["try", "improve", "almost", "close"]):
        return "encouraging"
    if any(key in lower for key in ["incorrect", "wrong", "not quite"]):
        return "sad"
    return "neutral"
