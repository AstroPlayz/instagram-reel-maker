from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random

try:
    from moviepy.editor import AudioFileClip, VideoFileClip
except ModuleNotFoundError:
    from moviepy import AudioFileClip, VideoFileClip

from reel_maker.hashtags import build_caption_and_hashtags
from reel_maker.reddit_scraper import RedditStoryNotFoundError, fetch_story
from reel_maker.text_processing import build_narration
from reel_maker.transcription import transcribe_audio
from reel_maker.tts import synthesize_tts
from reel_maker.video import render_reel


STORYTELLING_SUBREDDITS = [
    "tifu",
    "aita",
    "trueoffmychest",
    "confession",
    "relationship_advice",
    "pettyrevenge",
    "prorevenge",
    "nosleep",
    "maliciouscompliance",
    "entitledparents",
]


@dataclass
class ReelPipelineConfig:
    subreddit: str
    background_video: Path | None = None
    background_dir: Path = Path("Videos")
    sort: str = "top"
    period: str = "week"
    max_words: int = 130
    output_video: Path = Path("output/instagram_reel.mp4")
    whisper_model: str = "base"
    allow_nsfw: bool = False
    upload_instagram: bool = False
    upload_youtube: bool = False


@dataclass
class ReelOutput:
    video_path: Path
    story_title: str
    subreddit: str
    sentiment: str
    intensity: str
    instagram_caption: str
    youtube_caption: str
    instagram_media_id: str | None = None
    youtube_video_id: str | None = None


class ReelPipeline:
    def __init__(self, config: ReelPipelineConfig) -> None:
        self.config = config

    @staticmethod
    def _video_duration(video_path: Path) -> float:
        clip = VideoFileClip(str(video_path))
        duration = float(clip.duration)
        clip.close()
        return duration

    @staticmethod
    def _find_background_videos(background_dir: Path) -> list[Path]:
        extensions = {".mp4", ".mov", ".m4v", ".webm"}
        return sorted(
            [
                path
                for path in background_dir.iterdir()
                if path.is_file() and path.suffix.lower() in extensions
            ]
        )

    def _resolve_subreddit_candidates(self) -> list[str]:
        raw = self.config.subreddit.strip().lower()

        if raw in {"random", "story", "storytelling", "all"}:
            candidates = list(STORYTELLING_SUBREDDITS)
            random.shuffle(candidates)
            return candidates

        parts = [p.strip().lower() for p in self.config.subreddit.split(",") if p.strip()]
        if not parts:
            return ["tifu"]

        deduped: list[str] = []
        seen: set[str] = set()
        for part in parts:
            if part not in seen:
                seen.add(part)
                deduped.append(part)

        if len(deduped) > 1:
            random.shuffle(deduped)

        return deduped

    def _select_background_video(self) -> Path:
        if self.config.background_video is not None:
            return self.config.background_video

        background_dir = self.config.background_dir.resolve()
        if not background_dir.exists() or not background_dir.is_dir():
            raise RuntimeError(f"Background directory does not exist: {background_dir}")

        candidates = self._find_background_videos(background_dir)
        if not candidates:
            raise RuntimeError(
                f"No background video files found in {background_dir}. "
                "Add .mp4/.mov/.m4v/.webm clips."
            )

        if len(candidates) == 1:
            return candidates[0]

        long_video_threshold_seconds = 300.0
        long_candidates: list[tuple[Path, float]] = []
        for candidate in candidates:
            try:
                duration = self._video_duration(candidate)
            except Exception:
                continue
            if duration >= long_video_threshold_seconds:
                long_candidates.append((candidate, duration))

        if long_candidates:
            long_candidates.sort(key=lambda item: item[1], reverse=True)
            return long_candidates[0][0]

        return random.choice(candidates)

    @staticmethod
    def _pick_random_window(background_video_path: Path, narration_audio_path: Path) -> tuple[float, float]:
        audio_clip = AudioFileClip(str(narration_audio_path))
        video_clip = VideoFileClip(str(background_video_path))

        narration_duration = float(audio_clip.duration)
        video_duration = float(video_clip.duration)

        audio_clip.close()
        video_clip.close()

        if narration_duration <= 0:
            raise RuntimeError("Narration audio duration is invalid.")

        if video_duration <= 0:
            raise RuntimeError("Background video duration is invalid.")

        if narration_duration >= video_duration:
            return 0.0, video_duration

        max_start = max(0.0, video_duration - narration_duration)
        if max_start < 0.05:
            return 0.0, narration_duration
        start = random.uniform(0.0, max_start)
        end = min(video_duration, start + narration_duration)
        return start, end

    def run(self) -> ReelOutput:
        output_dir = self.config.output_video.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        subreddit_candidates = self._resolve_subreddit_candidates()
        story = None
        errors: list[str] = []
        for candidate in subreddit_candidates:
            try:
                story = fetch_story(
                    subreddit=candidate,
                    sort=self.config.sort,
                    period=self.config.period,
                    allow_nsfw=self.config.allow_nsfw,
                )
                if len(subreddit_candidates) > 1:
                    print(f"[Story] Selected r/{story.subreddit} from random pool.")
                break
            except RedditStoryNotFoundError as exc:
                errors.append(str(exc))

        if story is None:
            tried = ", ".join(f"r/{s}" for s in subreddit_candidates)
            details = " | ".join(errors[:3]) if errors else "No eligible posts returned."
            raise RuntimeError(
                f"Could not find a suitable story across: {tried}. {details}"
            )

        narration = build_narration(story.title, story.text, max_words=self.config.max_words)
        if not narration.strip():
            raise RuntimeError("Narration text is empty after processing.")

        source_info = output_dir / "story_source.txt"
        source_info.write_text(
            "\n".join(
                [
                    f"Title: {story.title}",
                    f"Author: u/{story.author}",
                    f"Subreddit: r/{story.subreddit}",
                    f"Score: {story.score}",
                    f"Permalink: {story.permalink}",
                    "",
                    "Narration:",
                    narration,
                ]
            ),
            encoding="utf-8",
        )

        narration_audio = output_dir / "narration.mp3"
        tts_result = synthesize_tts(narration, narration_audio)

        chosen_background = self._select_background_video()
        clip_start, clip_end = self._pick_random_window(chosen_background, narration_audio)

        subtitles = transcribe_audio(narration_audio, model_name=self.config.whisper_model)
        if not subtitles:
            raise RuntimeError("Whisper did not return subtitle segments.")

        with source_info.open("a", encoding="utf-8") as source_file:
            source_file.write("\n\nVoice tone:\n")
            source_file.write(f"Sentiment: {tts_result.tone.label}\n")
            source_file.write(f"Confidence: {tts_result.tone.score:.4f}\n")
            source_file.write(f"Intensity: {tts_result.tone.intensity}\n")
            source_file.write(f"Voice: {tts_result.tone.voice}\n")
            source_file.write(f"Rate: {tts_result.tone.rate}\n")
            source_file.write(f"Pitch: {tts_result.tone.pitch}\n")
            source_file.write(f"Volume: {tts_result.tone.volume}\n")
            source_file.write("\n\nBackground clip:\n")
            source_file.write(f"File: {chosen_background}\n")
            source_file.write(f"Clip start: {clip_start:.2f}s\n")
            source_file.write(f"Clip end: {clip_end:.2f}s\n")

        video_path = render_reel(
            background_video_path=chosen_background,
            narration_audio_path=narration_audio,
            subtitles=subtitles,
            output_path=self.config.output_video,
            background_start=clip_start,
        )

        sentiment = tts_result.tone.label
        intensity = tts_result.tone.intensity

        ig_caption, _ = build_caption_and_hashtags(
            subreddit=story.subreddit,
            title=story.title,
            sentiment=sentiment,
            intensity=intensity,
            platform="instagram",
        )
        yt_caption, yt_tags_str = build_caption_and_hashtags(
            subreddit=story.subreddit,
            title=story.title,
            sentiment=sentiment,
            intensity=intensity,
            platform="youtube",
        )

        result = ReelOutput(
            video_path=video_path,
            story_title=story.title,
            subreddit=story.subreddit,
            sentiment=sentiment,
            intensity=intensity,
            instagram_caption=ig_caption,
            youtube_caption=yt_caption,
        )

        if self.config.upload_instagram:
            from reel_maker.instagram_uploader import upload_reel_to_instagram
            try:
                result.instagram_media_id = upload_reel_to_instagram(video_path, ig_caption)
            except Exception as exc:
                print(f"[Instagram] Upload skipped due to error: {type(exc).__name__}: {exc}")

        if self.config.upload_youtube:
            from reel_maker.youtube_uploader import upload_reel_to_youtube
            yt_tags = [
                t.lstrip("#") for t in yt_tags_str.split() if t.startswith("#")
            ]
            try:
                result.youtube_video_id = upload_reel_to_youtube(
                    video_path=video_path,
                    title=story.title,
                    description=yt_caption,
                    tags=yt_tags,
                )
            except Exception as exc:
                print(f"[YouTube] Upload skipped due to error: {type(exc).__name__}: {exc}")

        return result
