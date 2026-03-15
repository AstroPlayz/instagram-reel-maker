from __future__ import annotations

import os
from pathlib import Path


class InstagramUploadError(RuntimeError):
    pass


def upload_reel_to_instagram(video_path: Path, caption: str) -> str:
    """
    Upload a vertical MP4 as an Instagram Reel using instagrapi.

    Requires env vars:
        INSTAGRAM_USERNAME  – your Instagram username
        INSTAGRAM_PASSWORD  – your Instagram password

    A session file (instagram_session.json) is saved after the first login so
    you stay logged in between runs without re-entering your password.

    Returns the published media ID.
    """
    try:
        from instagrapi import Client  # type: ignore
        from instagrapi.exceptions import LoginRequired  # type: ignore
    except ImportError as exc:
        raise InstagramUploadError(
            "instagrapi is not installed. Run: pip install instagrapi"
        ) from exc

    username = os.environ.get("INSTAGRAM_USERNAME", "").strip()
    password = os.environ.get("INSTAGRAM_PASSWORD", "").strip()
    if not username or not password:
        raise InstagramUploadError(
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables."
        )

    session_file = Path("instagram_session.json")
    cl = Client()

    # Try to reuse a saved session first
    logged_in = False
    if session_file.exists():
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            cl.get_timeline_feed()  # validate session is alive
            logged_in = True
            print("Instagram: reused cached session.")
        except (LoginRequired, Exception):
            print("Instagram: cached session expired, logging in fresh.")
            cl = Client()

    if not logged_in:
        try:
            cl.login(username, password)
        except Exception as exc:
            if "challenge_required" in str(exc).lower() or "ChallengeRequired" in type(exc).__name__:
                raise InstagramUploadError(
                    "Instagram requires a security verification.\n"
                    "  → Open the Instagram app on your phone and approve the login attempt,\n"
                    "    OR check the email linked to your account for a verification code.\n"
                    "  → Once approved, run this script again — it will work and save the session."
                ) from exc
            raise
        cl.dump_settings(session_file)
        print("Instagram: logged in and session saved.")

    print(f"Instagram: uploading reel {video_path} …")
    media = cl.clip_upload(
        Path(video_path),
        caption=caption,
        extra_data={"share_to_feed": 1},
    )
    media_id = str(media.pk)
    print(f"Instagram: published! media_id={media_id}")
    return media_id
