"""Finds: the interesting things, from where they actually turn up first.

The wire (pipeline/wire.py) reads newsrooms and company blogs. That is the
source of record, and on its own it makes a dull paper: policy consultations,
funding rounds and trade figures, because that is what newsrooms file. The
releases people download, the demos they try and the repos they star show up
somewhere else first.

This collects those, from free public APIs:

    Hugging Face   trending models, trending Spaces (demos), daily papers
    Hacker News    AI stories on the front page, and Show HN launches

and writes a ranked list to data/finds/<date>.json. The desk reads it next to
the brief. A find is not a story: it is a pointer to a public artifact, which
the desk opens and reports from (see style/11-beat.md). Most become snippets;
the best become stories.

Finds already carried as a snippet or a story source are left out, so the list
is only ever new things.

Usage:
    python -m pipeline.discover            # write today's finds
    python -m pipeline.discover --print    # print them, write nothing
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request

import yaml

from .common import DATA_DIR, EDITIONS_DIR, ROOT, normalize_url, utcnow
from .snippets import fingerprints as snippet_fingerprints

CONFIG = ROOT / "config" / "discover.yaml"
FINDS_DIR = DATA_DIR / "finds"
UA = "Mozilla/5.0 (compatible; TheAIPost/1.0; +https://theaipost.net)"


def load_cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def get_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def _when(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=dt.timezone.utc)


def _fresh(raw: str | None, max_age: dt.timedelta) -> bool:
    stamp = _when(raw)
    return stamp is not None and utcnow() - stamp <= max_age


def _skip(name: str, tags: list[str], words: list[str]) -> bool:
    hay = (name + " " + " ".join(tags)).lower()
    return any(w in hay for w in words)


def find(kind, title, url, source_name, signal, created_at, summary="", rank=0.0, extra=None) -> dict:
    return {"kind": kind, "title": title, "url": url,
            "source": {"name": source_name, "url": url},
            "signal": signal, "created_at": created_at,
            "summary": summary[:400], "rank": round(rank, 3), **(extra or {})}


# ── Hugging Face ─────────────────────────────────────────────────────────────

def hf_models(cfg: dict, max_age) -> list[dict]:
    c = cfg["huggingface"]["models"]
    rows = get_json(f"https://huggingface.co/api/models?sort=trendingScore&limit={c['limit']}")
    out = []
    for i, m in enumerate(rows):
        mid, tags = m.get("id", ""), m.get("tags", [])
        if not mid or _skip(mid, tags, cfg["huggingface"]["skip"]):
            continue
        if not _fresh(m.get("createdAt"), max_age):
            continue        # an old favourite still trending is not news
        org = mid.split("/")[0]
        task = m.get("pipeline_tag") or "model"
        lic = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), None)
        signal = (f"#{i + 1} trending model on Hugging Face; {m.get('likes', 0):,} likes, "
                  f"{m.get('downloads', 0):,} downloads")
        out.append(find("model", f"{mid} ({task})", f"https://huggingface.co/{mid}", org,
                        signal, m.get("createdAt"), rank=100 - i,
                        extra={"task": task, "license": lic}))
    return out[: c["keep"]]


def hf_spaces(cfg: dict, max_age) -> list[dict]:
    c = cfg["huggingface"]["spaces"]
    rows = get_json(f"https://huggingface.co/api/spaces?sort=trendingScore&limit={c['limit']}")
    out = []
    for i, s in enumerate(rows):
        sid = s.get("id", "")
        if not sid or s.get("likes", 0) < c["min_likes"]:
            continue
        if _skip(sid, s.get("tags", []), cfg["huggingface"]["skip"]):
            continue
        if not _fresh(s.get("createdAt"), max_age):
            continue
        signal = f"#{i + 1} trending Space (live demo) on Hugging Face; {s.get('likes', 0):,} likes"
        out.append(find("demo", sid, f"https://huggingface.co/spaces/{sid}", sid.split("/")[0],
                        signal, s.get("createdAt"), rank=80 - i))
    return out[: c["keep"]]


def hf_papers(cfg: dict, max_age) -> list[dict]:
    c = cfg["huggingface"]["papers"]
    rows = get_json("https://huggingface.co/api/daily_papers?limit=50")
    out = []
    for row in rows:
        p = row.get("paper", {})
        votes = p.get("upvotes", 0)
        if votes < c["min_upvotes"]:
            continue
        org = (row.get("organization") or p.get("organization") or {}).get("fullname")
        extra = {"project_page": p.get("projectPage"), "github": p.get("githubRepo")}
        signal = f"{votes} upvotes on Hugging Face daily papers" + (f"; from {org}" if org else "")
        out.append(find("paper", p.get("title", ""), f"https://huggingface.co/papers/{p.get('id')}",
                        org or "arXiv", signal, row.get("publishedAt"),
                        summary=p.get("summary") or row.get("summary") or "", rank=votes,
                        extra={k: v for k, v in extra.items() if v}))
    out.sort(key=lambda f: f["rank"], reverse=True)
    return out[: c["keep"]]


# ── Hacker News ──────────────────────────────────────────────────────────────

def _is_ai(title: str, terms: list[str]) -> bool:
    t = title.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", t) for term in terms)


def _hn(query: str) -> list[dict]:
    return get_json(f"https://hn.algolia.com/api/v1/search?{query}").get("hits", [])


def hn_front(cfg: dict, max_age) -> list[dict]:
    c, terms = cfg["hackernews"]["front_page"], cfg["hackernews"]["ai_terms"]
    out = []
    for h in _hn("tags=front_page&hitsPerPage=60"):
        title, pts = h.get("title") or "", h.get("points") or 0
        if pts < c["min_points"] or not _is_ai(title, terms):
            continue
        link = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
        host = urllib.parse.urlparse(link).netloc.removeprefix("www.")
        signal = f"{pts} points, {h.get('num_comments') or 0} comments on the Hacker News front page"
        out.append(find("hn", title, link, host, signal, h.get("created_at"), rank=pts,
                        extra={"discussion": f"https://news.ycombinator.com/item?id={h['objectID']}"}))
    out.sort(key=lambda f: f["rank"], reverse=True)
    return out[: c["keep"]]


def hn_show(cfg: dict, max_age) -> list[dict]:
    c, terms = cfg["hackernews"]["show_hn"], cfg["hackernews"]["ai_terms"]
    since = int(time.time()) - 2 * 86400
    q = urllib.parse.quote(f"created_at_i>{since},points>{c['min_points']}")
    out = []
    for h in _hn(f"tags=show_hn&numericFilters={q}&hitsPerPage=60"):
        title = h.get("title") or ""
        if not _is_ai(title, terms):
            continue
        link = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
        kind = "repo" if "github.com/" in link else "launch"
        signal = f"Show HN, {h.get('points') or 0} points, {h.get('num_comments') or 0} comments"
        out.append(find(kind, title.removeprefix("Show HN: "), link,
                        urllib.parse.urlparse(link).netloc.removeprefix("www."),
                        signal, h.get("created_at"), rank=h.get("points") or 0,
                        extra={"discussion": f"https://news.ycombinator.com/item?id={h['objectID']}"}))
    out.sort(key=lambda f: f["rank"], reverse=True)
    return out[: c["keep"]]


# ── assembly ─────────────────────────────────────────────────────────────────

def carried(days: int = 7) -> set[str]:
    """Links the paper has already used, as a snippet or a story source."""
    seen = set(snippet_fingerprints(days))
    for path in sorted(EDITIONS_DIR.glob("*.json"))[-days:]:
        if path.name.endswith(".new.json"):
            continue
        for story in json.loads(path.read_text(encoding="utf-8")).get("stories", []):
            seen.update(normalize_url(s["url"]) for s in story.get("sources", []) if s.get("url"))
    return seen


COLLECTORS = [("Hugging Face models", hf_models), ("Hugging Face Spaces", hf_spaces),
              ("Hugging Face papers", hf_papers), ("Hacker News", hn_front),
              ("Show HN", hn_show)]


def collect() -> tuple[list[dict], list[str]]:
    cfg = load_cfg()
    max_age = dt.timedelta(days=cfg.get("max_age_days", 21))
    already = carried()
    finds, report = [], []
    for name, fn in COLLECTORS:
        try:
            got = fn(cfg, max_age)
        except Exception as exc:              # one dead source must not stop the cycle
            report.append(f"! {name:<20} FAIL {type(exc).__name__}")
            continue
        fresh = [f for f in got if normalize_url(f["url"]) not in already]
        finds.extend(fresh)
        report.append(f"· {name:<20} {len(fresh)} new, {len(got) - len(fresh)} already carried")
    return finds, report


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect finds from Hugging Face and Hacker News.")
    ap.add_argument("--print", action="store_true", help="print, write nothing")
    args = ap.parse_args()

    finds, report = collect()
    print("\n".join(report))
    if args.print:
        for f in finds:
            print(f"  [{f['kind']:<6}] {f['title'][:70]:<70}  {f['signal']}")
        return

    day = utcnow().date().isoformat()
    FINDS_DIR.mkdir(parents=True, exist_ok=True)
    out = FINDS_DIR / f"{day}.json"
    out.write_text(json.dumps({"generated_at": utcnow().isoformat(timespec="seconds"),
                               "finds": finds}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"\n{len(finds)} finds → {out}")


if __name__ == "__main__":
    main()
