# Instagram Reel Maker (Reddit + edge-tts + Whisper)

Generate an Instagram-ready vertical reel from:
- a randomly selected background clip (from the Videos folder by default),
- a scraped text story from a subreddit,
- edge-tts narration audio,
- Whisper-based timed subtitles.

The output is a `1080x1920` MP4 (`H.264 + AAC`) suitable for Instagram Reels.

## What this project does

1. Scrapes a text post from a subreddit (`hot`, `new`, or `top`).
2. Builds a short narration script from the title + body.
3. Uses a transformer sentiment model to detect story tone.
4. Generates voiceover with `edge-tts` using sentiment-driven voice settings.
5. Picks a random background video and random start time that fits full narration.
6. Runs Whisper transcription to get subtitle timing.
7. Overlays timed subtitles on the selected background slice.
8. Exports a ready-to-upload reel.

## Prerequisites

- Python `3.10+`
- `ffmpeg` installed and available in PATH

macOS install:

```bash
brew install ffmpeg
```

## Setup

```bash
cd instagram-reel-maker
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

> First Whisper run downloads a model (depends on `--whisper-model`).
>
> First sentiment-analysis run also downloads a Hugging Face transformer model.

## Usage

```bash
make-reel \
  --subreddit tifu \
  --sort top \
  --period week \
  --max-words 130 \
  --whisper-model base \
  --output output/instagram_reel.mp4
```

Put 2-3 background videos (`.mp4`, `.mov`, `.m4v`, `.webm`) in the `Videos` folder in project root and run the command above. A file is chosen randomly each run.

If multiple clips exist, the pipeline prefers a long clip (5+ minutes) and then picks a random start/end chunk that fits the full narration.

If your clips are in another folder:

```bash
make-reel --background-dir /absolute/path/to/backgrounds --subreddit tifu
```

If you want to force a specific clip once:

```bash
make-reel --background /absolute/path/to/video.mp4 --subreddit tifu
```

## Useful options

- `--subreddit`: e.g. `nosleep`, `confession`, `relationship_advice`, `pettyrevenge`
- `--background-dir`: folder scanned for random background videos
- `--background`: optional fixed video path override
- `--sort`: `top`, `hot`, `new`
- `--period`: only used with `top` (`day`, `week`, `month`, `year`, `all`)
- `--max-words`: reduce if narration is too long for your background
- `--allow-nsfw`: include NSFW posts

## Output files

Inside your output folder:
- `instagram_reel.mp4` (final reel)
- `narration.mp3` (generated voiceover)
- `story_source.txt` (source post metadata + narration script)

## Notes

- This uses Reddit's public JSON endpoint, so very aggressive scraping may be rate-limited.
- Voice generation uses `edge-tts` and a transformer sentiment model to adjust delivery tone automatically.
- Subtitle styling is intentionally bold and centered near the bottom for mobile readability.
- If your narration is longer than the background clip, lower `--max-words`.
