from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import requests
from requests import RequestException


SortMode = Literal["hot", "new", "top"]
TopPeriod = Literal["day", "week", "month", "year", "all"]


@dataclass
class RedditStory:
    title: str
    text: str
    author: str
    subreddit: str
    score: int
    permalink: str


class RedditStoryNotFoundError(RuntimeError):
    pass


def fetch_story(
    subreddit: str,
    sort: SortMode = "top",
    period: TopPeriod = "week",
    min_chars: int = 250,
    limit: int = 50,
    allow_nsfw: bool = False,
) -> RedditStory:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }

    base_params = {"limit": limit}
    if sort == "top":
        base_params["t"] = period

    endpoints = [
        f"https://api.reddit.com/r/{subreddit}/{sort}",
        f"https://www.reddit.com/r/{subreddit}/{sort}.json",
        f"https://old.reddit.com/r/{subreddit}/{sort}.json",
    ]

    payload = None
    last_error: Exception | None = None
    for endpoint in endpoints:
        params = dict(base_params)
        if "reddit.com" in endpoint:
            params["raw_json"] = 1

        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
            break
        except RequestException as exc:
            last_error = exc
            continue

    if payload is None:
        reason = type(last_error).__name__ if last_error else "RequestException"
        raise RedditStoryNotFoundError(
            f"Could not fetch r/{subreddit} ({reason}). Trying another subreddit."
        )

    posts = payload.get("data", {}).get("children", [])

    for post in posts:
        data = post.get("data", {})
        selftext = (data.get("selftext") or "").strip()
        if len(selftext) < min_chars:
            continue
        if data.get("stickied"):
            continue
        if not allow_nsfw and data.get("over_18"):
            continue

        return RedditStory(
            title=data.get("title", "Untitled"),
            text=selftext,
            author=data.get("author", "unknown"),
            subreddit=data.get("subreddit", subreddit),
            score=int(data.get("score") or 0),
            permalink=f"https://reddit.com{data.get('permalink', '')}",
        )

    raise RedditStoryNotFoundError(
        f"No suitable text post found in r/{subreddit}. Try different filters."
    )
