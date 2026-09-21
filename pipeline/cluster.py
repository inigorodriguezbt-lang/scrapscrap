"""Turn a pile of raw posts into candidate stories.

The rule that matters: a cluster only becomes a story once several INDEPENDENT
accounts have touched the same event inside the time window. One account posting
loudly is not news; three accounts converging on the same thing is.

Similarity is IDF-weighted token cosine, boosted hard when two posts share an
outbound link -- in practice a shared link is near-proof of the same event.

Usage:
    python -m pipeline.cluster                 # newest raw file
    python -m pipeline.cluster --raw data/raw/posts-20260918T120000Z.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import (
    BRIEFS_DIR,
    RAW_DIR,
    load_config,
    normalize_url,
    tokenize,
    utcnow,
)


# ── similarity ───────────────────────────────────────────────────────────────

def build_idf(docs: list[list[str]]) -> dict[str, float]:
    """Rare words carry the signal; 'model' and 'release' carry almost none."""
    n = len(docs)
    df: Counter[str] = Counter()
    for tokens in docs:
        df.update(set(tokens))
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def to_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    vec = {term: (1 + math.log(count)) * idf.get(term, 1.0) for term, count in tf.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {term: v / norm for term, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


# A token this rare is almost always a proper noun -- a model name, a chip, a
# company. Two posts sharing one are very likely about the same event.
RARE_IDF = 1.9


def rare_overlap(post_a: dict, post_b: dict) -> set[str]:
    return {
        term
        for term in post_a["_rare"] & post_b["_rare"]
        # A bare number ("400k") corroborates only alongside a real name.
        if not term.replace(".", "").replace("-", "").isdigit()
    }


def similarity(post_a: dict, post_b: dict) -> float:
    """Cosine, lifted when two posts share a link or a distinctive proper noun."""
    score = cosine(post_a["_vec"], post_b["_vec"])

    if post_a["_links"] & post_b["_links"]:
        # A shared outbound link is near-proof of the same event.
        score = max(score, 0.62) + 0.20

    shared_rare = rare_overlap(post_a, post_b)
    if len(shared_rare) >= 2:
        score = max(score, 0.55)
    elif len(shared_rare) == 1:
        score = max(score, 0.40)

    return min(score, 1.0)


def centroid(posts: list[dict]) -> dict[str, float]:
    """Mean vector of a cluster, renormalized.

    Matching a cluster's centroid catches the post that restates an event in
    different words -- a press rewrite typically fails a pairwise comparison
    against any single member while matching the group's theme clearly.
    """
    total: dict[str, float] = {}
    for post in posts:
        for term, weight in post["_vec"].items():
            total[term] = total.get(term, 0.0) + weight
    norm = math.sqrt(sum(v * v for v in total.values())) or 1.0
    return {term: v / norm for term, v in total.items()}


# ── clustering ───────────────────────────────────────────────────────────────

def cluster_posts(posts: list[dict], threshold: float) -> list[list[dict]]:
    """Greedy agglomeration against cluster centroids.

    Single-pass and O(posts x clusters), which is plenty for a few thousand
    posts per edition and avoids pulling in a clustering dependency.
    """
    clusters: list[dict] = []

    # Newest first, so the earliest-breaking post tends to seed its cluster.
    for post in sorted(posts, key=lambda p: p["created_at"]):
        best, best_score = None, 0.0
        for cluster in clusters:
            pairwise = max(similarity(post, member) for member in cluster["posts"])
            # Established clusters also get judged on their overall theme.
            thematic = 0.0
            if len(cluster["posts"]) >= 2:
                thematic = cosine(post["_vec"], centroid(cluster["posts"]))
            score = max(pairwise, thematic)
            if score > best_score:
                best, best_score = cluster, score

        if best is not None and best_score >= threshold:
            best["posts"].append(post)
        else:
            clusters.append({"posts": [post]})

    return [c["posts"] for c in clusters]


# ── editorial scoring ────────────────────────────────────────────────────────

def classify(text: str, sections: list[dict]) -> str:
    """Seed classification by keyword hits. Claude re-checks this when writing."""
    lowered = text.lower()
    scores = {}
    for section in sections:
        total = 0.0
        for keyword in section["keywords"]:
            hits = lowered.count(keyword)
            if hits:
                # "training run" is a sharper signal than "chip"; reward specificity.
                total += hits * (1.0 + 0.5 * keyword.count(" "))
        scores[section["slug"]] = total
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else sections[0]["slug"]


def find_entities(text: str, entities: list[str]) -> list[str]:
    found = []
    for entity in entities:
        if re.search(rf"\b{re.escape(entity)}\b", text, flags=re.IGNORECASE):
            found.append(entity)
    return found


def score_cluster(posts: list[dict], now: datetime) -> float:
    """Rank on corroboration first, then reach, then freshness.

    Corroboration dominates deliberately: a story carried by five accounts
    outranks one loud post with big numbers, which is the whole editorial stance.
    """
    independent = {p["handle"] for p in posts}
    corroboration = math.log(len(independent) + 1) * 3.0

    source_weight = sum(p.get("weight", 1.0) for p in posts) / len(posts)
    primary_bonus = 1.5 if any(p.get("tier") == "primary" for p in posts) else 0.0

    engagement = sum(p["likes"] + 2 * p["reposts"] for p in posts)
    reach = math.log(engagement + 1) * 0.6

    newest = max(datetime.fromisoformat(p["created_at"]) for p in posts)
    age_hours = (now - newest).total_seconds() / 3600
    freshness = max(0.0, 2.5 - (age_hours / 6.0))

    return round(corroboration * source_weight + primary_bonus + reach + freshness, 3)


# ── assembly ─────────────────────────────────────────────────────────────────

def _read_window(path: Path, cutoff: datetime) -> list[dict]:
    posts = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                post = json.loads(line)
                stamp = datetime.fromisoformat(post["created_at"])
            except (ValueError, KeyError):
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if stamp >= cutoff:
                posts.append(post)
    return posts


def load_recent_posts(raw_path: Path | None, window_hours: int) -> list[dict]:
    """Every raw file inside the window, wire and X alike.

    Reading one file was enough when the whole edition came from a single
    nightly scrape. On an hourly cadence the window spans many files, and
    the X sweep writes x-*.jsonl rather than posts-*.jsonl, so globbing only
    posts-* silently dropped everything the paid search returned.
    """
    cutoff = utcnow() - timedelta(hours=window_hours)
    if raw_path is not None:
        return _read_window(raw_path, cutoff)

    posts, seen_ids = [], set()
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        if path.name == "posts-fixture.jsonl":
            continue
        for post in _read_window(path, cutoff):
            if post["id"] in seen_ids:      # the same post can land in two sweeps
                continue
            seen_ids.add(post["id"])
            posts.append(post)
    return posts


def build_briefs(raw_path: Path | None) -> dict:
    cfg = load_config()
    rules = cfg["editorial"]
    posts = load_recent_posts(raw_path, rules["window_hours"])
    if not posts:
        # A quiet hour is a normal result on this cadence, not a failure. The
        # caller writes an empty brief, the writer files nothing, and the
        # workflow's gate stops before it republishes an unchanged site.
        return {
            "generated_at": utcnow().isoformat(),
            "edition_date": utcnow().strftime("%Y-%m-%d"),
            "source_file": str(raw_path or RAW_DIR),
            "posts_considered": 0, "clusters_found": 0, "stories_declared": 0,
            "front_page_slots": rules.get("front_page_slots", 7),
            "stories": [],
        }

    # Deduplicate verbatim reposts of the same text by the same account.
    seen: set[tuple[str, str]] = set()
    unique = []
    for post in posts:
        key = (post["handle"], post["text"][:180])
        if key not in seen:
            seen.add(key)
            unique.append(post)
    posts = unique

    token_docs = [tokenize(p["text"]) for p in posts]
    idf = build_idf(token_docs)
    for post, tokens in zip(posts, token_docs):
        post["_vec"] = to_vector(tokens, idf)
        post["_links"] = {normalize_url(u) for u in post.get("links", [])}
        post["_rare"] = {t for t in set(tokens) if idf.get(t, 0.0) >= RARE_IDF}

    clusters = cluster_posts(posts, rules["cluster_threshold"])
    now = utcnow()
    sections = cfg["sections"]

    stories = []
    for group in clusters:
        independent = sorted({p["handle"] for p in group})
        if len(independent) < rules["min_independent_sources"]:
            continue

        combined = " ".join(p["text"] for p in group)
        links = sorted({u for p in group for u in p.get("links", [])})

        stories.append({
            "cluster_id": "c" + hashlib.sha1(
                "|".join(sorted(p["id"] for p in group)).encode("utf-8")
            ).hexdigest()[:8],
            "score": score_cluster(group, now),
            "suggested_section": classify(combined, sections),
            "entities": find_entities(combined, cfg["entities"]),
            "independent_sources": independent,
            "source_count": len(independent),
            "first_seen": min(p["created_at"] for p in group),
            "last_seen": max(p["created_at"] for p in group),
            "links": links,
            # Everything Claude needs to write the piece, and nothing else.
            "posts": [
                {
                    "author": p["author"],
                    "tier": p.get("tier"),
                    "text": p["text"],
                    "url": p["url"],
                    "created_at": p["created_at"],
                    "engagement": p["likes"] + 2 * p["reposts"],
                }
                for p in sorted(group, key=lambda p: p["created_at"])
            ],
        })

    stories.sort(key=lambda s: s["score"], reverse=True)
    stories = stories[: rules["max_stories_per_edition"]]

    return {
        "generated_at": now.isoformat(),
        "edition_date": now.strftime("%Y-%m-%d"),
        "source_file": raw_path.name if raw_path else str(RAW_DIR),
        "posts_considered": len(posts),
        "clusters_found": len(clusters),
        "stories_declared": len(stories),
        "front_page_slots": rules["front_page_slots"],
        "stories": stories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Cluster raw posts into story briefs.")
    parser.add_argument("--raw", type=Path, help="raw JSONL file (default: newest)")
    args = parser.parse_args()

    raw_path = args.raw
    if raw_path is None and not any(RAW_DIR.glob("*.jsonl")):
        raise SystemExit("No raw files. Run: python -m pipeline.wire")

    briefs = build_briefs(raw_path)

    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    out = BRIEFS_DIR / f"{briefs['edition_date']}.json"
    out.write_text(json.dumps(briefs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"{briefs['posts_considered']} posts → {briefs['clusters_found']} clusters "
        f"→ {briefs['stories_declared']} stories (>= "
        f"{load_config()['editorial']['min_independent_sources']} independent sources)"
    )
    print(f"Brief → {out}")
    for story in briefs["stories"][:8]:
        srcs = ", ".join(story["independent_sources"][:4])
        print(f"  {story['score']:6.2f}  [{story['suggested_section']:<14}] {srcs}")


if __name__ == "__main__":
    main()
