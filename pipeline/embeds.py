"""Embeds: X posts and videos placed inside a story, by link alone.

A story carries `embeds`, a list of `{"url": ..., "after": N}`: the link, and
the paragraph (1-based) it follows; without `after` it goes at the end. On the
site an X post renders as the platform's own embed and a YouTube link as a
player. In the copy file and the email the bare link sits on its own line at
the same spot, which is what an article editor needs to turn it into an embed
when the text is pasted in.
"""

from __future__ import annotations

import re

X_POST = re.compile(r"^https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/\w+/status/(\d+)")
YOUTUBE = re.compile(r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)|youtu\.be/)"
                     r"([\w-]{11})")


def kind(url: str) -> str:
    """'x', 'youtube' or 'link'."""
    if X_POST.match(url or ""):
        return "x"
    if YOUTUBE.match(url or ""):
        return "youtube"
    return "link"


def youtube_id(url: str) -> str:
    m = YOUTUBE.match(url or "")
    return m.group(1) if m else ""


def clean(story: dict) -> list[dict]:
    """Valid embeds only, each with a paragraph slot inside the body."""
    n = len(story.get("body") or [])
    out = []
    for e in story.get("embeds") or []:
        url = (e.get("url") if isinstance(e, dict) else e) or ""
        if not re.match(r"^https?://\S+$", url):
            continue
        after = e.get("after") if isinstance(e, dict) else None
        after = after if isinstance(after, int) and 1 <= after <= n else n
        out.append({"url": url, "after": after, "kind": kind(url), "youtube_id": youtube_id(url)})
    return out


def after(story: dict, paragraph: int) -> list[dict]:
    """The embeds that follow paragraph `paragraph` (1-based)."""
    return [e for e in clean(story) if e["after"] == paragraph]
