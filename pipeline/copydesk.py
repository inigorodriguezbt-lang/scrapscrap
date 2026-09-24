"""The copy file: this run's articles, in full, ready to copy and paste.

The editor wants every new story's headline and full text off the site and
into their hands without pasting a wall of text into the chat. So each cycle
writes one Markdown file with just this run's stories (the ids the merge step
recorded in data/state/last_run.json): headline, standfirst, body, the live
URL, and the post drafted for it. The cycle sends that file; the chat reply
stays a short list of headlines.

Usage:
    python -m pipeline.copydesk                      # today's edition
    python -m pipeline.copydesk --edition data/editions/2026-09-24.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import DATA_DIR, EDITIONS_DIR, load_config, utcnow
from .merge import LAST_RUN

COPY_DIR = DATA_DIR / "copy"
RULE = "-" * 60


def this_run_ids() -> list[str]:
    try:
        return json.loads(LAST_RUN.read_text(encoding="utf-8"))["added"]
    except (OSError, ValueError, KeyError):
        return []


def queued_post(day: str, cluster_id: str) -> str:
    """The drafted X post for a story, if pipeline.social has queued one."""
    try:
        queue = json.loads((DATA_DIR / "queue" / f"{day}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    for post in queue.get("posts", []):
        if post.get("cluster_id") == cluster_id:
            return post.get("text", "")
    return ""


def render(stories: list[dict], day: str, site: str) -> str:
    stamp = utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# The AI Post: {len(stories)} new {'story' if len(stories) == 1 else 'stories'}",
           f"_{stamp}_", ""]
    for s in stories:
        url = f"{site}/story/{s['cluster_id']}/"
        out += [RULE, "", f"## {s['headline']}", "", f"**{s.get('standfirst', '')}**", ""]
        out += [p + "\n" for p in s.get("body", [])]
        out += [f"Read it on the site: {url}", ""]
        sources = ", ".join(src.get("author", "") for src in s.get("sources", []) if src.get("author"))
        if sources:
            out += [f"_Sources: {sources}_", ""]
        post = queued_post(day, s["cluster_id"])
        if post:
            out += ["Post for X:", "", "```", post, "```", ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Write this run's stories to a copy file.")
    ap.add_argument("--edition", type=Path)
    ap.add_argument("--ids", nargs="*", help="cluster ids (default: this run's, from last_run.json)")
    args = ap.parse_args()

    edition_path = args.edition or EDITIONS_DIR / f"{utcnow().date().isoformat()}.json"
    day = edition_path.stem
    edition = json.loads(edition_path.read_text(encoding="utf-8"))
    wanted = args.ids if args.ids else this_run_ids()
    by_id = {s["cluster_id"]: s for s in edition.get("stories", [])}
    stories = [by_id[i] for i in wanted if i in by_id]
    if not stories:
        print("No new stories this run; no copy file written.")
        return

    site = load_config()["paper"].get("site_url", "").rstrip("/")
    COPY_DIR.mkdir(parents=True, exist_ok=True)
    out = COPY_DIR / f"{day}-{utcnow().strftime('%H%M')}.md"
    out.write_text(render(stories, day, site), encoding="utf-8")
    print(f"{len(stories)} stories → {out}")
    for s in stories:
        print(f"  · {s['headline']}")


if __name__ == "__main__":
    main()
