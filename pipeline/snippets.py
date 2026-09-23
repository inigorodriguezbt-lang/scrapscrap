"""Snippets: one-line items too small for a story, too good to throw away.

A snippet is found while researching a lead — a version bump, a price change,
a benchmark figure, a repo getting attention, one sourced line from a lab
chief. It gets a single sentence of fact (`text`), shown in the front-page
rail, and a single sentence of context (`why`), used only in the newsletter.

Snippets live in their own files, `data/snippets/<date>.json`, and never touch
the edition files. That keeps them out of ten load-bearing call sites in the
build (placement, dedupe, the style gate, archive counts, sitemap, feed,
preview cards, story pages) and out of the way of the hourly desk job, which
rewrites the edition file every hour.

A snippet has no page of its own: there is no body to put on one. The rail
links straight to the source.

Usage:
    python -m pipeline.snippets add data/snippets/<date>.new.json
    python -m pipeline.snippets list [--days 3]

The `.new.json` side file is a list of snippets, or `{"snippets": [...]}`.
Each needs `text`, `why`, `source: {name, url}`; `id`, `tag` and
`published_at` are filled in when missing. Items repeating a source link
already carried in the last seven days are skipped, not duplicated.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as _date, timedelta
from pathlib import Path

from .common import DATA_DIR, normalize_url, utcnow

SNIPPETS_DIR = DATA_DIR / "snippets"
DEDUPE_DAYS = 7


def path_for(day: str) -> Path:
    return SNIPPETS_DIR / f"{day}.json"


def read_day(day: str) -> list[dict]:
    p = path_for(day)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("snippets", [])


def recent_days(days: int, today: str | None = None) -> list[str]:
    """ISO dates, newest first, for the last `days` days including today."""
    end = _date.fromisoformat(today) if today else utcnow().date()
    return [(end - timedelta(days=i)).isoformat() for i in range(days)]


def load_snippets(days: int = 3, today: str | None = None) -> list[dict]:
    """Every snippet from the last `days` days, newest first."""
    items = [s for d in recent_days(days, today) for s in read_day(d)]
    return sorted(items, key=lambda s: s.get("published_at") or "", reverse=True)


def load_all() -> list[dict]:
    """Every snippet ever filed, newest first. The archive page reads this."""
    items = []
    for p in sorted(SNIPPETS_DIR.glob("*.json")):
        if p.name.endswith(".new.json"):
            continue
        day = json.loads(p.read_text(encoding="utf-8"))
        for s in day.get("snippets", []):
            s.setdefault("date", day.get("date", p.stem))
            items.append(s)
    return sorted(items, key=lambda s: s.get("published_at") or "", reverse=True)


def fingerprints(days: int = DEDUPE_DAYS, today: str | None = None) -> set[str]:
    """Normalised source links already used, so a snippet never repeats one."""
    return {normalize_url(s["source"]["url"])
            for s in load_snippets(days, today) if s.get("source", {}).get("url")}


def slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:6]) or "snippet"


def add(items: list[dict], day: str) -> tuple[list[str], list[str]]:
    """Append new snippets to `day`'s file. Returns (added ids, skipped reasons).

    Never rewrites what is already there, which is the same rule the hourly
    desk follows for stories: published copy stays as it was published.
    """
    existing = read_day(day)
    seen_urls = fingerprints(today=day)
    seen_ids = {s["id"] for s in existing}
    added, skipped = [], []
    now = utcnow().isoformat(timespec="seconds")

    for item in items:
        url = (item.get("source") or {}).get("url", "")
        key = normalize_url(url) if url else ""
        if key and key in seen_urls:
            skipped.append(f"{item.get('id') or slug(item.get('text', ''))}: source already carried")
            continue
        sid = item.get("id") or slug(item.get("text", ""))
        base, n = sid, 2
        while sid in seen_ids:
            sid, n = f"{base}-{n}", n + 1
        item["id"] = sid
        item.setdefault("published_at", now)
        existing.append(item)
        seen_ids.add(sid)
        if key:
            seen_urls.add(key)
        added.append(sid)

    if added:
        SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
        path_for(day).write_text(
            json.dumps({"date": day, "snippets": existing}, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
    return added, skipped


def main() -> None:
    ap = argparse.ArgumentParser(description="Add or list snippets.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add snippets from a side file")
    a.add_argument("new", type=Path)
    a.add_argument("--date", help="edition date (default: today, UTC)")
    a.add_argument("--keep-new", action="store_true", help="leave the side file in place")
    l = sub.add_parser("list", help="print recent snippets")
    l.add_argument("--days", type=int, default=3)
    args = ap.parse_args()

    if args.cmd == "list":
        for s in load_snippets(args.days):
            print(f"{(s.get('published_at') or '')[:16]}  {s['text']}  — {s['source']['name']}")
        return

    raw = json.loads(args.new.read_text(encoding="utf-8"))
    items = raw.get("snippets", []) if isinstance(raw, dict) else raw
    if not items:
        sys.exit(f"No snippets in {args.new}.")
    day = args.date or utcnow().date().isoformat()
    added, skipped = add(items, day)
    print(f"{len(added)} added, {len(skipped)} skipped → {path_for(day)}")
    for reason in skipped:
        print(f"  skipped  {reason}")
    if not args.keep_new:
        args.new.unlink()


if __name__ == "__main__":
    main()
