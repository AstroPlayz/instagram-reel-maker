from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import requests


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
        "User-Agent": "instagram-reel-maker/0.1 (by u/story_reel_bot)",
    }

    endpoint = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": limit}
    if sort == "top":
        params["t"] = period

    response = requests.get(endpoint, params=params, headers=headers, timeout=20)
    response.raise_for_status()

    payload = response.json()
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
