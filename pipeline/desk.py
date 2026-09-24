"""The desk's worklist: everything fresh and unpublished, in one short file.

A cycle used to read the brief, the finds, today's edition and the snippet
files, then spend tokens researching items only to find they had already run.
This does that bookkeeping for free, before the model starts: it merges the
brief's clusters with the finds, drops anything the paper has already carried
(same source link, or a headline that reads as a published one), and ranks
what is left, freshest and most interesting first.

The model reads data/desk/<date>.json and nothing else to decide what to write.

Usage:
    python -m pipeline.desk              # write the worklist
    python -m pipeline.desk --print      # show it
"""

from __future__ import annotations

import argparse
import json

import re

from .common import BRIEFS_DIR, DATA_DIR, EDITIONS_DIR, normalize_url, utcnow

# The clustering tokenizer drops company names as beat noise, which is right
# for grouping posts and wrong here: "Meta" is what makes two headlines match.
_STOP = set("""a an the and or of to in on for with at by from as is are was be its it this that
says said say new after over into about than more has have will would can could may their
they them how what why who when which our your his her not but just now""".split())


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9$][a-z0-9$.,-]*[a-z0-9]|[a-z0-9]", text.lower())
    out = []
    for w in words:
        w = w.replace(",", "")
        w = re.sub(r"(\d)-gram(s)?$|grams?$", r"\1", w) if w[0].isdigit() else w
        if w not in _STOP and len(w) > 1:
            out.append(w.rstrip("s") if len(w) > 4 and not w[0].isdigit() else w)
    return out
from .merge import already_published, published_fingerprints
from .snippets import fingerprints as snippet_fingerprints, load_snippets

DESK_DIR = DATA_DIR / "desk"
FINDS_DIR = DATA_DIR / "finds"
MAX_ITEMS = 25

# How a find's kind ranks against another's when both are fresh. Releases and
# things people can try come first; tips from newsrooms after.
KIND_WEIGHT = {"model": 3.0, "repo": 3.0, "launch": 2.5, "demo": 2.5, "update": 2.0,
               "tip": 2.0, "hn": 2.0, "paper": 1.5}
INTEREST_WEIGHT = {"want": 3.0, "neutral": 1.0, "dull": -2.0}


def _latest(directory, pattern="*.json"):
    files = sorted(p for p in directory.glob(pattern) if not p.name.endswith(".new.json"))
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else {}


def _snippet_headlines(days=2):
    return [{"id": "", "urls": set(), "words": set(s["text"].lower().split()[:14]),
             "headline": s["text"], "date": "snippet"} for s in load_snippets(days)]


def _recent_stories(days=2):
    """(headline, token set) for every story in the last `days` editions.

    Headline, standfirst, lede and slug together: our headlines are
    rewritten, so the source's wording rarely matches the headline alone.
    """
    files = sorted(p for p in EDITIONS_DIR.glob("*.json") if not p.name.endswith(".new.json"))
    out = []
    for path in files[-days:]:
        for s in json.loads(path.read_text(encoding="utf-8")).get("stories", []):
            lede = (s.get("body") or [""])[0]
            words = set(tokenize(" ".join([s.get("headline", ""), s.get("standfirst", ""), lede,
                                           s.get("cluster_id", "").replace("-", " ")])))
            out.append((s.get("headline", ""), words))
    return out


def similar_to(title: str, recent) -> str | None:
    """The published headline this candidate most resembles, if any.

    Flagged rather than dropped: a real new development on a covered story
    would otherwise vanish. The model skips a flagged item in one glance.
    """
    words = set(tokenize(title))
    best, best_n = None, 0
    for headline, pub in recent:
        n = len(words & pub)
        if n > best_n:
            best, best_n = headline, n
    return best if words and best_n >= 3 and best_n / len(words) >= 0.3 else None


def candidates() -> list[dict]:
    published = published_fingerprints(window_hours=72)
    carried = snippet_fingerprints(7)
    out = []

    for c in _latest(BRIEFS_DIR).get("stories", []):
        first = c["posts"][0]
        probe = {"cluster_id": c["cluster_id"], "headline": first["text"][:120],
                 "sources": [{"url": p["url"]} for p in c["posts"] if p.get("url")]}
        if already_published(probe, published):
            continue
        if any(normalize_url(p.get("url", "")) in carried for p in c["posts"]):
            continue
        age = min((utcnow() - __import__("datetime").datetime.fromisoformat(p["created_at"])
                   ).total_seconds() / 3600 for p in c["posts"])
        out.append({
            "id": c["cluster_id"], "kind": "cluster", "interest": c.get("interest", "neutral"),
            "age_hours": round(age, 1), "sources": len(c["independent_sources"]),
            "single_source": c.get("single_source", False),
            "title": first["text"][:160],
            "links": [p["url"] for p in c["posts"] if p.get("url")][:4],
            "posts": [{"author": p["author"], "tier": p.get("tier"), "text": p["text"][:400],
                       "url": p["url"], "at": p["created_at"]} for p in c["posts"][:4]],
            "score": INTEREST_WEIGHT.get(c.get("interest"), 1.0) + c.get("score", 0) / 5,
        })

    for f in _latest(FINDS_DIR).get("finds", []):
        links = [f["url"]] + f.get("credits", [])[:3]
        if any(normalize_url(u) in carried for u in links):
            continue
        probe = {"cluster_id": "", "headline": f["title"], "sources": [{"url": u} for u in links]}
        if already_published(probe, published):
            continue
        age = f.get("age_hours") or 24.0
        out.append({
            "id": f"find:{f['kind']}:{normalize_url(f['url'])[:60]}", "kind": f["kind"],
            "age_hours": age, "title": f["title"][:160], "signal": f.get("signal", ""),
            "links": links, "summary": (f.get("summary") or "")[:300],
            "score": KIND_WEIGHT.get(f["kind"], 1.0) + max(0.0, 3.0 - age / 4),
        })

    recent = _recent_stories()
    for item in out:
        hit = similar_to(item["title"], recent)
        if hit:
            item["similar_to"] = hit
            item["score"] -= 3.0            # still listed, never first
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:MAX_ITEMS]


def main() -> None:
    ap = argparse.ArgumentParser(description="Write the desk's worklist.")
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    items = candidates()
    if args.print:
        for i in items:
            flag = f"   ≈ {i['similar_to'][:50]}" if i.get("similar_to") else ""
            print(f"{i['score']:5.1f} {i['age_hours']:>5}h [{i['kind']:<7}] {i['title'][:80]}{flag}")
        return
    DESK_DIR.mkdir(parents=True, exist_ok=True)
    day = utcnow().date().isoformat()
    path = DESK_DIR / f"{day}.json"
    path.write_text(json.dumps({"generated_at": utcnow().isoformat(timespec="seconds"),
                                "items": items}, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"{len(items)} fresh, unpublished candidates → {path}")


if __name__ == "__main__":
    main()
