from __future__ import annotations

import re
from typing import Iterable

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
MULTISPACE_PATTERN = re.compile(r"\s+")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
REDDIT_REF_PATTERN = re.compile(r"\b(?:r|u)/([A-Za-z0-9_\-]+)")

REPLACEMENTS = {
    "AITA": "Am I the asshole",
    "TIFU": "Today I messed up",
    "TLDR": "too long, didn't read",
    "IMO": "in my opinion",
    "IMHO": "in my humble opinion",
    "WTF": "what the heck",
    "IDK": "I don't know",
    "OMG": "oh my god",
    "BF": "boyfriend",
    "GF": "girlfriend",
    "MIL": "mother in law",
    "FIL": "father in law",
}


def normalize_text(text: str) -> str:
    cleaned = URL_PATTERN.sub("", text)
    cleaned = REDDIT_REF_PATTERN.sub(lambda match: match.group(1).replace("_", " "), cleaned)
    cleaned = cleaned.replace("&", " and ")
    cleaned = cleaned.replace("/", " or ")
    cleaned = cleaned.replace("\n", " ").strip()
    return MULTISPACE_PATTERN.sub(" ", cleaned)


def expand_common_abbreviations(text: str) -> str:
    expanded = text
    for short, long_form in REPLACEMENTS.items():
        expanded = re.sub(rf"\b{re.escape(short)}\b", long_form, expanded, flags=re.IGNORECASE)
    return expanded


def optimize_for_tts(text: str) -> str:
    cleaned = expand_common_abbreviations(normalize_text(text))
    cleaned = re.sub(r"\s*[-–—]\s*", ", ", cleaned)
    cleaned = re.sub(r"\s*;\s*", ". ", cleaned)
    cleaned = re.sub(r"\s*:\s*", ", ", cleaned)
    cleaned = re.sub(r"([!?]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"\.{3,}", ".", cleaned)
    cleaned = re.sub(r"\b(\d+)\s*yo\b", r"\1 year old", cleaned, flags=re.IGNORECASE)
    cleaned = MULTISPACE_PATTERN.sub(" ", cleaned).strip()
    return cleaned


def sentence_chunks(text: str) -> list[str]:
    cleaned = optimize_for_tts(text)
    if not cleaned:
        return []
    return [segment.strip() for segment in SENTENCE_SPLIT_PATTERN.split(cleaned) if segment.strip()]


def trim_to_max_words(text: str, max_words: int) -> str:
    chunks = sentence_chunks(text)
    if not chunks:
        return ""

    selected: list[str] = []
    word_count = 0
    for chunk in chunks:
        chunk_words = len(chunk.split())
        if word_count and word_count + chunk_words > max_words:
            break
        selected.append(chunk)
        word_count += chunk_words

    if not selected:
        words = text.split()[:max_words]
        return " ".join(words)

    return " ".join(selected)


def build_narration(title: str, body: str, max_words: int) -> str:
    spoken_title = optimize_for_tts(title)
    spoken_body = optimize_for_tts(body)
    content = trim_to_max_words(spoken_body, max_words=max(20, max_words - len(spoken_title.split())))
    narration = f"{spoken_title}. {content}".strip()
    narration = re.sub(r"\s+", " ", narration)
    return narration


def chunk_for_screen(text: str, max_words_per_chunk: int = 8) -> list[str]:
    words = normalize_text(text).split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words_per_chunk:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


def even_timing(items: Iterable[str], duration: float) -> list[tuple[str, float, float]]:
    elements = list(items)
    if not elements or duration <= 0:
        return []
    segment_duration = duration / len(elements)
    timeline: list[tuple[str, float, float]] = []
    current = 0.0
    for idx, item in enumerate(elements):
        start = current
        end = duration if idx == len(elements) - 1 else current + segment_duration
        timeline.append((item, start, end))
        current += segment_duration
    return timeline
