#!/usr/bin/env python3
"""
One-time YouTube OAuth setup. Run this locally to get your tokens.

HOW TO USE
----------
1. Go to https://console.cloud.google.com/
2. Create a project → Enable "YouTube Data API v3"
3. Go to APIs & Services → Credentials → + Create Credentials → OAuth 2.0 Client ID
4. Application type: Desktop app → click Create → Download JSON
5. Run:  python scripts/get_youtube_token.py ~/Downloads/client_secret_xxx.json
6. Your browser will open → log in → click Allow
7. Copy the 3 values printed here into your environment / GitHub secrets

That's it. You never need to do this again (refresh tokens don't expire).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python scripts/get_youtube_token.py path/to/client_secret.json")
        sys.exit(1)

    secret_file = Path(sys.argv[1]).expanduser()
    if not secret_file.exists():
        print(f"Error: file not found: {secret_file}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Run: pip install google-auth-oauthlib")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), scopes=SCOPES)
    print("\nOpening your browser… log in and click Allow.")
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    # Read client_id / client_secret back from the JSON so we can print them
    with secret_file.open() as f:
        raw = json.load(f)
    client_data = raw.get("installed") or raw.get("web", {})

    print("\n" + "=" * 60)
    print("✅  Done! Add these three values as env vars or GitHub Secrets:")
    print("=" * 60)
    print(f"YOUTUBE_CLIENT_ID     = {client_data.get('client_id', creds.client_id)}")
    print(f"YOUTUBE_CLIENT_SECRET = {client_data.get('client_secret', creds.client_secret)}")
    print(f"YOUTUBE_REFRESH_TOKEN = {creds.refresh_token}")
    print("=" * 60)
    print("Refresh tokens don't expire — this is a one-time step.\n")


if __name__ == "__main__":
    main()
