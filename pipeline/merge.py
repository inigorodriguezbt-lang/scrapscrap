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

from .common import load_config


def _key(story: dict) -> str:
    return story.get("cluster_id", "")


def merge(edition: dict, incoming: list[dict], front_slots: int) -> tuple[dict, list[str], list[str]]:
    """Return the merged edition, the ids added, and the ids skipped."""
    existing = edition.get("stories", []) or []
    known = {_key(s) for s in existing}

    added, skipped = [], []
    fresh = []
    for story in incoming:
        cid = _key(story)
        if not cid:
            skipped.append("(no cluster_id)")
            continue
        if cid in known:
            skipped.append(cid)          # already published; leave it alone
            continue
        known.add(cid)
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

    print(f"{before} → {len(edition['stories'])} stories in {args.edition.name}")
    if added:
        print("  added:   " + ", ".join(added))
    if skipped:
        print("  skipped: " + ", ".join(skipped) + "  (already published)")


if __name__ == "__main__":
    main()
