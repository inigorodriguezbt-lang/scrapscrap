"""Fold newly written stories into today's edition without disturbing it.

The edition writer used to produce a whole edition in one pass, which is fine
once a day and destructive every hour: a second run would rewrite stories that
are already on the site and already linked from posts the editor has sent.

So the hourly loop splits in two. Claude writes only the stories it has not
written before, into a side file, and this merges them. Copy that is already
published is never touched here -- existing entries are carried across byte for
byte, and a new story whose cluster_id is already in the edition is dropped
rather than duplicated.

Placement is mechanical on purpose. The lead is not churned hourly: whatever is
leading keeps leading unless a human moves it. New stories enter the front,
the front is capped at the configured slot count, and what overflows drops to
inside, oldest first.

Usage:
    python -m pipeline.merge --edition data/editions/2026-09-21.json \\
                             --new data/editions/2026-09-21.new.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import DATA_DIR, EDITIONS_DIR, load_config, normalize_url, tokenize

# What this run actually added, so the post drafter can show the editor those
# and not the whole backlog. A run that adds nothing writes an empty list,
# which is the correct answer to "what should I send now".
LAST_RUN = DATA_DIR / "state" / "last_run.json"

# Two headlines this alike, about the same beat, are the same event.
# Measured against the pair that slipped through: "Trump says he will form an
# AI Force and name an AI czar" against "Trump wants to name an 'AI czar' to
# head new 'AI Force'" scores 0.50.
SAME_STORY = 0.45
MIN_SHARED_TOKENS = 2


def _key(story: dict) -> str:
    return story.get("cluster_id", "")


def _urls(story: dict) -> set[str]:
    return {normalize_url(src.get("url", "")) for src in story.get("sources", []) if src.get("url")}


def _words(story: dict) -> set[str]:
    return set(tokenize(story.get("headline", "")))


def published_fingerprints(window_hours: int = 96) -> list[dict]:
    """Everything the paper has run recently, as things to compare against.

    Deduplicating on cluster_id alone cannot work: the id is a hash of the
    post ids in the cluster, so the same event picked up an hour later with
    one extra post hashes to something entirely different. The paper ran the
    same Trump story twice that way. So compare what the story is about.
    """
    # `--new` lives in this directory too, and a bare *.json glob picks it up:
    # the incoming story then matches itself and every hourly run merges
    # nothing. Side files are not published editions, so skip them.
    editions = sorted(p for p in EDITIONS_DIR.glob("*.json")
                      if not p.name.endswith(".new.json"))
    out = []
    for path in editions[-6:]:
        try:
            edition = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for story in edition.get("stories", []) or []:
            out.append({"id": _key(story), "urls": _urls(story), "words": _words(story),
                        "headline": story.get("headline", ""), "date": path.stem})
    return out


def already_published(story: dict, published: list[dict]) -> str | None:
    """Why this story is a repeat, or None if it is genuinely new."""
    cid, urls, words = _key(story), _urls(story), _words(story)
    for prior in published:
        if cid and cid == prior["id"]:
            return f"same cluster id as {prior['headline'][:48]!r}"
        shared_urls = urls & prior["urls"]
        if shared_urls:
            return f"shares a source with {prior['headline'][:48]!r} ({prior['date']})"
        if words and prior["words"]:
            overlap = words & prior["words"]
            union = words | prior["words"]
            if len(overlap) >= MIN_SHARED_TOKENS and len(overlap) / len(union) >= SAME_STORY:
                return (f"reads as {prior['headline'][:48]!r} ({prior['date']}), "
                        f"{len(overlap)}/{len(union)} words shared")
    return None


def merge(edition: dict, incoming: list[dict], front_slots: int) -> tuple[dict, list[str], list[str]]:
    """Return the merged edition, the ids added, and the ids skipped."""
    existing = edition.get("stories", []) or []
    published = published_fingerprints()

    added, skipped = [], []
    fresh = []
    for story in incoming:
        cid = _key(story)
        if not cid:
            skipped.append("(no cluster_id)")
            continue
        repeat = already_published(story, published)
        if repeat:
            skipped.append(f"{story.get('headline', cid)[:44]!r} — {repeat}")
            continue
        published.append({"id": cid, "urls": _urls(story), "words": _words(story),
                          "headline": story.get("headline", ""), "date": "this run"})
        fresh.append(story)
        added.append(cid)

    if not fresh:
        return edition, added, skipped

    lead = next((s for s in existing if s.get("placement") == "lead"), None)
    rest = [s for s in existing if s is not lead]

    # New stories sit directly under the lead, newest first, then everything
    # that was already there keeps its relative order beneath them.
    ordered = ([lead] if lead else []) + fresh + rest

    # One lead, front_slots on the front, the remainder inside.
    for index, story in enumerate(ordered):
        if story is lead:
            story["placement"] = "lead"
        elif lead is None and index == 0:
            story["placement"] = "lead"
        elif index <= front_slots:
            story["placement"] = "front"
        else:
            story["placement"] = "inside"

    edition["stories"] = ordered
    return edition, added, skipped


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--edition", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True,
                    help="stories written this run; deleted once merged")
    ap.add_argument("--keep-new", action="store_true", help="do not delete --new")
    args = ap.parse_args()

    if not args.new.exists():
        print(f"{args.new} absent; nothing written this run.")
        return

    payload = json.loads(args.new.read_text(encoding="utf-8"))
    incoming = payload.get("stories", payload if isinstance(payload, list) else [])
    if not incoming:
        print("No new stories in this run.")
        LAST_RUN.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN.write_text(json.dumps({"added": []}, indent=1) + "\n", encoding="utf-8")
        if not args.keep_new:
            args.new.unlink()
        return

    if args.edition.exists():
        edition = json.loads(args.edition.read_text(encoding="utf-8"))
    else:
        edition = {"edition_date": args.edition.stem, "stories": []}

    slots = load_config()["editorial"].get("front_page_slots", 7)
    before = len(edition.get("stories", []))
    edition, added, skipped = merge(edition, incoming, slots)

    args.edition.parent.mkdir(parents=True, exist_ok=True)
    args.edition.write_text(json.dumps(edition, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    if not args.keep_new:
        args.new.unlink()

    LAST_RUN.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN.write_text(json.dumps({"added": added}, indent=1) + "\n", encoding="utf-8")

    print(f"{before} → {len(edition['stories'])} stories in {args.edition.name}")
    if added:
        print("  added:   " + ", ".join(added))
    if skipped:
        print("  skipped: " + ", ".join(skipped) + "  (already published)")


if __name__ == "__main__":
    main()
