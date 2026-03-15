#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from reel_maker.pipeline import ReelPipeline, ReelPipelineConfig


def main() -> None:
    config = ReelPipelineConfig(
        subreddit="random",
        sort="top",
        period="week",
        max_words=130,
        whisper_model="base",
        output_video=Path("output/instagram_reel_instagram_only.mp4"),
        upload_instagram=True,
        upload_youtube=False,
    )

    result = ReelPipeline(config).run()
    print(f"✅ Reel created: {result.video_path}")
    print(f"   Subreddit: r/{result.subreddit}")
    if result.instagram_media_id:
        print(f"[Instagram] Media ID: {result.instagram_media_id}")


if __name__ == "__main__":
    main()
