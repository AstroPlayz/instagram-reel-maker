from __future__ import annotations

import asyncio
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import edge_tts

try:
    from moviepy.editor import AudioFileClip, concatenate_audioclips
except ModuleNotFoundError:
    from moviepy import AudioFileClip, concatenate_audioclips

from reel_maker.sentiment import NarrationTone, analyze_sentence_tones, analyze_tone
from reel_maker.text_processing import sentence_chunks


@dataclass
class TTSResult:
    audio_path: Path
    tone: NarrationTone


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


async def _render_sentence(text: str, output_path: Path, tone: NarrationTone) -> None:
    communicator = edge_tts.Communicate(
        text=text,
        voice=tone.voice,
        rate=tone.rate,
        pitch=tone.pitch,
        volume=tone.volume,
    )
    await communicator.save(str(output_path))


async def _render_all_sentences(
    sentence_tones: list[tuple[str, NarrationTone]],
    tmp_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    for idx, (sentence, tone) in enumerate(sentence_tones):
        clip_path = tmp_dir / f"sentence_{idx:04d}.mp3"
        await _render_sentence(sentence, clip_path, tone)
        paths.append(clip_path)
    return paths


def _concatenate_mp3s(segment_paths: list[Path], output_path: Path) -> None:
    clips = [AudioFileClip(str(p)) for p in segment_paths]
    try:
        combined = concatenate_audioclips(clips)
        combined.write_audiofile(str(output_path), logger=None)
        combined.close()
    finally:
        for clip in clips:
            clip.close()


def synthesize_tts(text: str, output_audio: Path) -> TTSResult:
    output_audio.parent.mkdir(parents=True, exist_ok=True)

    sentences = sentence_chunks(text)
    if not sentences:
        raise RuntimeError("No sentences found in narration text.")

    sentence_tones = analyze_sentence_tones(sentences)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        segment_paths = asyncio.run(_render_all_sentences(sentence_tones, tmp_dir))
        if len(segment_paths) == 1:
            import shutil
            shutil.copy2(segment_paths[0], output_audio)
        else:
            _concatenate_mp3s(segment_paths, output_audio)

    # Return overall tone based on full-text analysis for metadata
    overall_tone = analyze_tone(text)
    return TTSResult(audio_path=output_audio, tone=overall_tone)
