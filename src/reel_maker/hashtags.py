from __future__ import annotations

import re

# --- Viral base tags (always included) ---
VIRAL_BASE = [
    "#fyp",
    "#foryou",
    "#foryoupage",
    "#viral",
    "#trending",
    "#storytime",
    "#reddit",
    "#redditstories",
    "#redditreadings",
    "#storytelling",
    "#redditstory",
    "#textstory",
    "#plottwist",
    "#drama",
    "#mustwatch",
]

# --- Subreddit-specific tags ---
SUBREDDIT_TAGS: dict[str, list[str]] = {
    "tifu": ["#tifu", "#todayifuckedup", "#funnyreddit", "#embarrassing", "#oops", "#awkward"],
    "aita": ["#aita", "#amithebadguy", "#moraldilemma", "#relationship", "#advice"],
    "nosleep": ["#nosleep", "#horrortok", "#scarystories", "#creepy", "#horror", "#spooky"],
    "relationship_advice": ["#relationshipadvice", "#dating", "#breakup", "#toxic", "#love"],
    "confession": ["#confession", "#confessions", "#anonymous", "#secretstory"],
    "pettyrevenge": ["#pettyrevenge", "#revenge", "#karma", "#satisfying"],
    "prorevenge": ["#revenge", "#prorevenge", "#karma", "#justice", "#satisfying"],
    "raisedbynarcissists": ["#narcissist", "#toxicfamily", "#healingjourney", "#mentalhealth"],
    "entitledparents": ["#entitledparents", "#karencheck", "#entitledpeople"],
    "maliciouscompliance": ["#maliciouscompliance", "#workstories", "#pettysatisfying"],
    "legaladvice": ["#legaladvice", "#law", "#legal", "#storytime"],
    "trueoffmychest": ["#offmychest", "#confession", "#truestory"],
    "survivorsofabuse": ["#survivor", "#mentalhealth", "#healed", "#truestory"],
}

# --- Sentiment / tone tags ---
SENTIMENT_TAGS: dict[str, list[str]] = {
    "positive": ["#funny", "#wholesome", "#laugh", "#comedy", "#heartwarming", "#goodvibes"],
    "negative": ["#sad", "#emotional", "#crying", "#dark", "#relatable", "#deep"],
    "neutral": ["#interesting", "#relatable", "#truestory", "#unbelievable", "#story"],
}

# --- Intensity tags ---
INTENSITY_TAGS: dict[str, list[str]] = {
    "high": ["#omg", "#unbelievable", "#mindblown", "#shocking", "#cantmakethisup", "#wtf"],
    "medium": ["#relatable", "#interesting", "#storytime", "#waitforit"],
    "low": ["#chill", "#storytelling", "#slice_of_life", "#everydaylife"],
}

# --- Platform-specific tags ---
INSTAGRAM_EXTRA = [
    "#reels",
    "#instareels",
    "#reelsinstagram",
    "#reelsviral",
    "#explorepage",
    "#viralreels",
    "#reelitfeelit",
]
YOUTUBE_EXTRA = ["#Shorts", "#YouTubeShorts", "#shortsfeed", "#redditonytshorts"]


def _extract_keywords(title: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{5,}\b", title.lower())
    stop_words = {
        "about", "after", "again", "every", "found", "getting", "going",
        "great", "heres", "https", "later", "little", "makes", "never",
        "other", "posts", "reddit", "right", "since", "still", "their",
        "there", "these", "thing", "think", "those", "today", "until",
        "using", "where", "which", "while", "would",
    }
    keywords: list[str] = []
    for word in words:
        if word in stop_words:
            continue
        if len(word) > 16:
            continue
        keywords.append(f"#{word}")
    return keywords[:6]


def build_caption_and_hashtags(
    subreddit: str,
    title: str,
    sentiment: str,
    intensity: str,
    platform: str = "instagram",
) -> tuple[str, str]:
    """Return (caption, hashtag_block) for a given story and platform."""
    tags: list[str] = list(VIRAL_BASE)
    tags += SUBREDDIT_TAGS.get(subreddit.lower(), [f"#{subreddit.lower()}"])
    tags += SENTIMENT_TAGS.get(sentiment, SENTIMENT_TAGS["neutral"])
    tags += INTENSITY_TAGS.get(intensity, [])
    tags += _extract_keywords(title)

    if platform == "youtube":
        tags += YOUTUBE_EXTRA
    else:
        tags += INSTAGRAM_EXTRA

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_tags: list[str] = []
    for tag in tags:
        low = tag.lower()
        if low not in seen:
            seen.add(low)
            unique_tags.append(tag)

    max_tags = 30 if platform == "instagram" else 20
    hashtag_block = " ".join(unique_tags[:max_tags])

    caption_title = title[:150] if len(title) > 150 else title
    if platform == "youtube":
        caption = f"{caption_title} #Shorts\n\n{hashtag_block}"
    else:
        caption = f"{caption_title}\n\n{hashtag_block}"

    return caption, hashtag_block
