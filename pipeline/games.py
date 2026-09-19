"""Puzzles cut from the paper's own stories.

Two of the games draw on the archive rather than on hand-written data, so
each headline the paper publishes is also a puzzle:

  redact  — a headline with three words blacked out; guess them
  splice  — two headlines joined at a seam; find the seam

The pools are shuffled with a fixed seed so today's puzzle does not change
between builds. They still shift as editions are added, which is fine for
test builds and is noted on the hub.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

STOP = set("""a an the and or but of to in on at for with by from as is are was were be been
has have had this that these those it its into over under after before about than then
their there they them his her him she he we our you your who whom which what when where
why how not no nor so if up out off down per via up amid against among between through
during without within says said say new more most less least very only also still""".split())

CONNECTIVES = {"and", "to", "for", "in", "after", "with", "of", "on", "at", "as", "that",
               "while", "before", "over", "months", "until", "despite", "amid", "against"}


def words(headline: str) -> list[str]:
    return headline.split()


def clean(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def redact_puzzle(story: dict) -> dict | None:
    toks = words(story["headline"])
    cands = [i for i, w in enumerate(toks)
             if len(clean(w)) >= 5 and clean(w) not in STOP and not clean(w).isdigit()]
    if len(cands) < 3:
        return None
    # Spread the blanks across the headline: first, middle, last candidate.
    picks = sorted({cands[0], cands[len(cands) // 2], cands[-1]})
    if len(picks) < 3:
        return None
    return {
        "id": story["cluster_id"],
        "words": toks,
        "blanks": picks,
        "answers": {str(i): clean(toks[i]) for i in picks},
        "url": f"story/{story['cluster_id']}/",
    }


def splice_pair(a: dict, b: dict, rnd: random.Random) -> dict | None:
    wa, wb = words(a["headline"]), words(b["headline"])
    if len(wa) < 6 or len(wb) < 6:
        return None
    # The suffix reads best when it starts on a connective; the prefix can
    # end anywhere past its third word.
    seams_b = [j for j, w in enumerate(wb) if clean(w) in CONNECTIVES and 2 <= j <= len(wb) - 3]
    j = rnd.choice(seams_b) if seams_b else len(wb) // 2
    i = rnd.randint(3, max(3, len(wa) - 3))
    spliced = wa[:i] + wb[j:]
    return {
        "words": spliced,
        "seam": i - 1,                       # index of the last word from A
        "a": {"headline": a["headline"], "url": f"story/{a['cluster_id']}/"},
        "b": {"headline": b["headline"], "url": f"story/{b['cluster_id']}/"},
    }


def build_games(stories: list[dict], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(stories, key=lambda s: s["cluster_id"])

    rnd = random.Random(7)
    redact = [p for p in (redact_puzzle(s) for s in ordered) if p]
    rnd.shuffle(redact)

    rnd = random.Random(11)
    pairs = [(a, b) for a in ordered for b in ordered if a is not b]
    rnd.shuffle(pairs)
    splice = [p for p in (splice_pair(a, b, rnd) for a, b in pairs[:120]) if p]

    (out_dir / "redact.json").write_text(json.dumps({"puzzles": redact}, ensure_ascii=False))
    (out_dir / "splice.json").write_text(json.dumps({"pool": splice}, ensure_ascii=False))
    return {"redact": len(redact), "splice": len(splice)}
