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


def _build_story_from_pullpush(item: dict, subreddit: str, allow_nsfw: bool, min_chars: int) -> RedditStory | None:
    selftext = (item.get("selftext") or "").strip()
    if len(selftext) < min_chars:
        return None
    if item.get("stickied"):
        return None
    if not allow_nsfw and (item.get("over_18") or item.get("nsfw")):
        return None

    permalink = item.get("full_link") or item.get("permalink") or ""
    if permalink and permalink.startswith("/"):
        permalink = f"https://reddit.com{permalink}"

    return RedditStory(
        title=item.get("title", "Untitled"),
        text=selftext,
        author=item.get("author", "unknown"),
        subreddit=item.get("subreddit", subreddit),
        score=int(item.get("score") or 0),
        permalink=permalink,
    )


def _fetch_story_from_pullpush(
    subreddit: str,
    sort: SortMode,
    period: TopPeriod,
    min_chars: int,
    limit: int,
    allow_nsfw: bool,
) -> RedditStory:
    # PullPush provides public mirror access to Reddit submissions and helps in
    # environments where Reddit blocks anonymous cloud runner IPs.
    endpoint = "https://api.pullpush.io/reddit/search/submission/"
    params: dict[str, str | int] = {
        "subreddit": subreddit,
        "size": limit,
        "is_self": "true",
        "sort": sort,
        "sort_type": "score" if sort == "top" else "created_utc",
    }
    if sort == "top":
        params["timeframe"] = period

    response = requests.get(endpoint, params=params, timeout=25)
    response.raise_for_status()
    data = response.json().get("data", [])

    for item in data:
        story = _build_story_from_pullpush(item, subreddit, allow_nsfw, min_chars)
        if story is not None:
            return story

    raise RedditStoryNotFoundError(
        f"No suitable text post found in r/{subreddit} from PullPush mirror."
    )


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
        try:
            return _fetch_story_from_pullpush(
                subreddit=subreddit,
                sort=sort,
                period=period,
                min_chars=min_chars,
                limit=limit,
                allow_nsfw=allow_nsfw,
            )
        except RequestException as exc:
            reason = type(last_error).__name__ if last_error else type(exc).__name__
            raise RedditStoryNotFoundError(
                f"Could not fetch r/{subreddit} ({reason}). Trying another subreddit."
            ) from exc

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
