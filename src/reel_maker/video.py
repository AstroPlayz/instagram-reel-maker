from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
try:
    from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip
except ModuleNotFoundError:
    from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip
from PIL import Image, ImageDraw, ImageFont

# moviepy's built-in resize uses Image.ANTIALIAS which was removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS  # type: ignore[attr-defined]

from reel_maker.transcription import SubtitleSegment


@dataclass
class ReelRenderConfig:
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    font_size: int = 64
    subtitle_bottom_padding: int = 220


def _clip_section(clip, start: float, end: float):
    if hasattr(clip, "subclip"):
        return clip.subclip(start, end)
    return clip.subclipped(start, end)


def _with_audio(video_clip, audio_clip):
    if hasattr(video_clip, "set_audio"):
        return video_clip.set_audio(audio_clip)
    return video_clip.with_audio(audio_clip)


def _crop_clip(clip, **kwargs):
    if hasattr(clip, "crop"):
        return clip.crop(**kwargs)
    return clip.cropped(**kwargs)


def _resize_clip(clip, size):
    if hasattr(clip, "resize"):
        return clip.resize(size)
    return clip.resized(new_size=size)


def _set_start(clip, value: float):
    if hasattr(clip, "set_start"):
        return clip.set_start(value)
    return clip.with_start(value)


def _set_end(clip, value: float):
    if hasattr(clip, "set_end"):
        return clip.set_end(value)
    return clip.with_end(value)


def fit_vertical(video: VideoFileClip, width: int, height: int) -> VideoFileClip:
    target_ratio = width / height
    clip_ratio = video.w / video.h

    if clip_ratio > target_ratio:
        new_width = int(video.h * target_ratio)
        cropped = _crop_clip(video, x_center=video.w // 2, width=new_width)
    else:
        new_height = int(video.w / target_ratio)
        cropped = _crop_clip(video, y_center=video.h // 2, height=new_height)

    return _resize_clip(cropped, (width, height))


def _load_font(font_size: int) -> ImageFont.ImageFont:
    for font_name in ["Arial Bold.ttf", "Arial.ttf", "Helvetica.ttc"]:
        try:
            return ImageFont.truetype(font_name, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _subtitle_image(text: str, width: int, height: int, font_size: int, bottom_padding: int) -> np.ndarray:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _load_font(font_size)

    max_text_width = int(width * 0.86)
    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    for word in words:
        current.append(word)
        probe = " ".join(current)
        bbox = draw.textbbox((0, 0), probe, font=font, stroke_width=3)
        if (bbox[2] - bbox[0]) > max_text_width and len(current) > 1:
            current.pop()
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    line_height = font_size + 16
    total_text_height = line_height * len(lines)
    start_y = height - bottom_padding - total_text_height

    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = start_y + idx * line_height
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 255),
        )

    return np.array(image)


def render_reel(
    background_video_path: Path,
    narration_audio_path: Path,
    subtitles: list[SubtitleSegment],
    output_path: Path,
    background_start: float = 0.0,
    config: ReelRenderConfig | None = None,
) -> Path:
    options = config or ReelRenderConfig()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_clip = AudioFileClip(str(narration_audio_path))
    raw_video = VideoFileClip(str(background_video_path))
    effective_start = min(max(0.0, background_start), max(0.0, raw_video.duration - 0.05))
    available_video_duration = max(0.0, raw_video.duration - effective_start)
    duration = min(audio_clip.duration, available_video_duration)

    if duration <= 0:
        raise RuntimeError("Background clip duration is too short for rendering.")

    audio_clip = _clip_section(audio_clip, 0, duration)
    base_video = _clip_section(raw_video, effective_start, effective_start + duration)
    base_video = fit_vertical(base_video, options.target_width, options.target_height)
    base_video = _with_audio(base_video, audio_clip)

    subtitle_clips: list[ImageClip] = []
    for segment in subtitles:
        subtitle_frame = _subtitle_image(
            segment.text,
            width=options.target_width,
            height=options.target_height,
            font_size=options.font_size,
            bottom_padding=options.subtitle_bottom_padding,
        )
        subtitle_clips.append(
            _set_end(
                _set_start(ImageClip(subtitle_frame), max(0.0, segment.start)),
                min(duration, segment.end),
            )
        )

    final = CompositeVideoClip([base_video, *subtitle_clips], size=(options.target_width, options.target_height))
    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=options.fps,
        preset="medium",
        threads=4,
    )

    final.close()
    audio_clip.close()
    base_video.close()
    raw_video.close()
    for clip in subtitle_clips:
        clip.close()

    return output_path
