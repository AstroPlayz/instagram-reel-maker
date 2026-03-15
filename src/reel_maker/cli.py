from __future__ import annotations

from pathlib import Path

import click

from reel_maker.pipeline import ReelPipeline, ReelPipelineConfig


@click.command()
@click.option("--background", type=click.Path(exists=True, path_type=Path), default=None, help="Optional fixed background clip path. If omitted, one is chosen randomly from --background-dir.")
@click.option("--background-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), default=Path("Videos"), show_default=True, help="Directory to scan for background videos when --background is omitted.")
@click.option("--subreddit", default="random", show_default=True, help="Story source subreddit. Use 'random' for rotating storytelling subs, or pass a comma-separated list like 'tifu,aita,nosleep'.")
@click.option("--sort", type=click.Choice(["top", "hot", "new"]), default="top", show_default=True)
@click.option("--period", type=click.Choice(["day", "week", "month", "year", "all"]), default="week", show_default=True, help="Top timeframe when --sort=top.")
@click.option("--max-words", default=130, show_default=True, type=int, help="Maximum words for spoken narration.")
@click.option("--output", type=click.Path(path_type=Path), default=Path("output/instagram_reel.mp4"), show_default=True)
@click.option("--whisper-model", default="base", show_default=True, help="Whisper model name: tiny/base/small/medium/large.")
@click.option("--allow-nsfw", is_flag=True, default=False, help="Include NSFW posts.")
@click.option("--upload-instagram", is_flag=True, default=False, help="Upload finished reel to Instagram. Requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD env vars.")
@click.option("--upload-youtube", is_flag=True, default=False, help="Upload finished reel to YouTube Shorts. Requires YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN env vars.")
def main(
    background: Path | None,
    background_dir: Path,
    subreddit: str,
    sort: str,
    period: str,
    max_words: int,
    output: Path,
    whisper_model: str,
    allow_nsfw: bool,
    upload_instagram: bool,
    upload_youtube: bool,
) -> None:
    config = ReelPipelineConfig(
        background_video=background,
        background_dir=background_dir,
        subreddit=subreddit,
        sort=sort,
        period=period,
        max_words=max_words,
        output_video=output,
        whisper_model=whisper_model,
        allow_nsfw=allow_nsfw,
        upload_instagram=upload_instagram,
        upload_youtube=upload_youtube,
    )
    pipeline = ReelPipeline(config)
    result = pipeline.run()
    click.echo(f"\n✅ Reel created: {result.video_path}")
    click.echo(f"   Subreddit  : r/{result.subreddit}")
    click.echo(f"   Sentiment  : {result.sentiment} / {result.intensity}")
    click.echo(f"\nInstagram caption:\n{result.instagram_caption}")
    click.echo(f"\nYouTube caption:\n{result.youtube_caption}")
    if result.instagram_media_id:
        click.echo(f"\n[Instagram] Media ID: {result.instagram_media_id}")
    if result.youtube_video_id:
        click.echo(f"[YouTube]   https://youtube.com/shorts/{result.youtube_video_id}")


if __name__ == "__main__":
    main()
