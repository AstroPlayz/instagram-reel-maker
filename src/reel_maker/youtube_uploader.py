from __future__ import annotations

import os
from pathlib import Path

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# Entertainment category ID
CATEGORY_ID = "24"


class YouTubeUploadError(RuntimeError):
    pass


def _get_credentials() -> Credentials:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

    if not client_id or not client_secret or not refresh_token:
        raise YouTubeUploadError(
            "Missing YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, or YOUTUBE_REFRESH_TOKEN "
            "environment variables. Run scripts/get_youtube_token.py to obtain a refresh token."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=YOUTUBE_SCOPES,
    )
    creds.refresh(Request())
    return creds


def upload_reel_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
) -> str:
    """
    Upload a vertical MP4 as a YouTube Short via the Data API v3.
    Returns the published video ID.

    Requires env vars:
        YOUTUBE_CLIENT_ID
        YOUTUBE_CLIENT_SECRET
        YOUTUBE_REFRESH_TOKEN
    """
    creds = _get_credentials()
    youtube = build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, credentials=creds)

    # Ensure #Shorts is in both title and description for Shorts detection
    short_title = title if "#Shorts" in title else f"{title[:90]} #Shorts"
    short_description = description if "#Shorts" in description else f"{description}\n\n#Shorts"

    body = {
        "snippet": {
            "title": short_title,
            "description": short_description,
            "tags": (tags or []) + ["Shorts", "reddit", "redditstories"],
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10 MB chunks
    )

    print(f"[YouTube] Uploading {video_path.name}...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[YouTube] Upload progress: {pct}%")
        except HttpError as e:
            raise YouTubeUploadError(f"YouTube upload failed: {e}") from e

    video_id = response.get("id", "unknown")
    print(f"[YouTube] ✅ Published! https://youtube.com/shorts/{video_id}")
    return video_id
