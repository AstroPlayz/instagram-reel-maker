from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

from transformers import pipeline


SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"


@dataclass
class NarrationTone:
    label: str
    score: float
    intensity: str
    voice: str
    rate: str
    pitch: str
    volume: str = "+0%"


def _story_intensity(text: str) -> str:
    exclamations = text.count("!")
    questions = text.count("?")
    uppercase_words = len(re.findall(r"\b[A-Z]{3,}\b", text))
    dramatic_keywords = len(
        re.findall(
            r"\b(shocked|terrified|panic|panicked|screamed|crying|furious|awful|horrible|amazing|unbelievable|suddenly|instantly|finally)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    score = exclamations + questions + uppercase_words + dramatic_keywords
    if score >= 5:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


@lru_cache(maxsize=1)
def _sentiment_pipeline():
    return pipeline(
        task="sentiment-analysis",
        model=SENTIMENT_MODEL,
        tokenizer=SENTIMENT_MODEL,
    )


def analyze_sentence_tones(sentences: list[str]) -> list[tuple[str, NarrationTone]]:
    """Analyze each sentence independently and return (sentence, tone) pairs."""
    return [(s, analyze_tone(s)) for s in sentences if s.strip()]


def analyze_tone(text: str) -> NarrationTone:
    classifier = _sentiment_pipeline()
    result = classifier(text[:1500])[0]

    label = str(result["label"]).lower()
    score = float(result["score"])
    intensity = _story_intensity(text)

    if label == "positive":
        if intensity == "high":
            return NarrationTone(
                label=label,
                score=score,
                intensity=intensity,
                voice="en-US-AriaNeural",
                rate="+2%",
                pitch="+10Hz",
                volume="+4%",
            )
        return NarrationTone(
            label=label,
            score=score,
            intensity=intensity,
            voice="en-US-JennyNeural",
            rate="+0%",
            pitch="+6Hz",
            volume="+2%",
        )

    if label == "negative":
        if intensity == "high":
            return NarrationTone(
                label=label,
                score=score,
                intensity=intensity,
                voice="en-US-JennyNeural",
                rate="-18%",
                pitch="-12Hz",
                volume="+3%",
            )
        return NarrationTone(
            label=label,
            score=score,
            intensity=intensity,
            voice="en-US-JennyNeural",
            rate="-10%",
            pitch="-6Hz",
            volume="+2%",
        )

    if intensity == "high":
        return NarrationTone(
            label="neutral",
            score=score,
            intensity=intensity,
            voice="en-US-AndrewNeural",
            rate="-8%",
            pitch="-2Hz",
            volume="+2%",
        )

    if intensity == "medium":
        return NarrationTone(
            label="neutral",
            score=score,
            intensity=intensity,
            voice="en-US-JennyNeural",
            rate="-5%",
            pitch="+0Hz",
            volume="+1%",
        )

    return NarrationTone(
        label="neutral",
        score=score,
        intensity=intensity,
        voice="en-US-AndrewNeural",
        rate="-3%",
        pitch="+0Hz",
            volume="+0%",
        )
