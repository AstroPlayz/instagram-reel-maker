from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import whisper


@dataclass
class SubtitleSegment:
    text: str
    start: float
    end: float


def transcribe_audio(audio_path: Path, model_name: str = "base") -> list[SubtitleSegment]:
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path), fp16=False)
    raw_segments = result.get("segments", [])

    segments: list[SubtitleSegment] = []
    for segment in raw_segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end <= start:
            end = start + 0.1
        segments.append(SubtitleSegment(text=text, start=start, end=end))

    return segments
