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


async def _render_sentence_with_retry(
    text: str,
    output_path: Path,
    tone: NarrationTone,
    max_attempts: int = 5,
) -> None:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            await _render_sentence(text, output_path, tone)
            return
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            await asyncio.sleep(min(10, 1.5 * attempt))
    if last_exc is not None:
        raise last_exc


async def _render_all_sentences(
    sentence_tones: list[tuple[str, NarrationTone]],
    tmp_dir: Path,
) -> list[Path]:
    paths: list[Path] = []
    for idx, (sentence, tone) in enumerate(sentence_tones):
        clip_path = tmp_dir / f"sentence_{idx:04d}.mp3"
        await _render_sentence_with_retry(sentence, clip_path, tone)
        paths.append(clip_path)
    return paths


async def _render_full_text_with_retry(text: str, output_path: Path, tone: NarrationTone) -> None:
    await _render_sentence_with_retry(text, output_path, tone, max_attempts=6)


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

    overall_tone = analyze_tone(text)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        try:
            segment_paths = asyncio.run(_render_all_sentences(sentence_tones, tmp_dir))
            if len(segment_paths) == 1:
                import shutil
                shutil.copy2(segment_paths[0], output_audio)
            else:
                _concatenate_mp3s(segment_paths, output_audio)
        except Exception as exc:
            print(f"[TTS] Per-sentence synthesis failed ({type(exc).__name__}); retrying with single-pass TTS...")
            asyncio.run(_render_full_text_with_retry(text, output_audio, overall_tone))

    # Return overall tone based on full-text analysis for metadata
    return TTSResult(audio_path=output_audio, tone=overall_tone)
