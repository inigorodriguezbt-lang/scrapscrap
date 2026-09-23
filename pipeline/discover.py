"""Finds: the interesting things, from where they actually turn up first.

The wire (pipeline/wire.py) reads newsrooms and company blogs. That is the
source of record, and on its own it makes a dull paper: policy consultations,
funding rounds and trade figures, because that is what newsrooms file. The
releases people download, the demos they try and the repos they star show up
somewhere else first.

This collects those, from free public APIs:

    Tips           HuggingNews, Techmeme, TestingCatalog: what broke in the
                   last few hours, with the primary links each one credits
    Hugging Face   trending models, trending Spaces (demos), daily papers
    Hacker News    AI stories on the front page, and Show HN launches

Every source has a freshness window (config/discover.yaml, max_age_hours).
The paper publishes every two hours; a thing that is merely popular but days
old is not news, so it is left out rather than ranked low.

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

from concurrent.futures import ThreadPoolExecutor

from .common import DATA_DIR, EDITIONS_DIR, ROOT, normalize_url, utcnow
from .snippets import fingerprints as snippet_fingerprints
from .wire import parse_date, strip_html

CONFIG = ROOT / "config" / "discover.yaml"
FINDS_DIR = DATA_DIR / "finds"
UA = "Mozilla/5.0 (compatible; TheAIPost/1.0; +https://theaipost.net)"


def load_cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def get_json(url: str, timeout: int = 20):
    return json.loads(get(url, timeout))


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


def _age_hours(raw) -> float | None:
    stamp = raw if isinstance(raw, dt.datetime) else _when(raw)
    return None if stamp is None else round((utcnow() - stamp).total_seconds() / 3600, 1)


def find(kind, title, url, source_name, signal, created_at, summary="", rank=0.0, extra=None) -> dict:
    if isinstance(created_at, dt.datetime):
        created_at = created_at.isoformat(timespec="seconds")
    return {"kind": kind, "title": title, "url": url,
            "source": {"name": source_name, "url": url},
            "signal": signal, "created_at": created_at, "age_hours": _age_hours(created_at),
            "summary": summary[:400], "rank": round(rank, 3), **(extra or {})}


# ── Tips: fast newsrooms ─────────────────────────────────────────────────────

X_STATUS = re.compile(r"https?://(?:x|twitter)\.com/\w+/status/\d+")
X_EPOCH_MS = 1288834974657


def x_posted_at(url: str) -> dt.datetime | None:
    """When an X post was made, read from its id (ids are timestamped)."""
    try:
        post_id = int(url.rstrip("/").rsplit("/", 1)[1])
    except (ValueError, IndexError):
        return None
    return dt.datetime.fromtimestamp(((post_id >> 22) + X_EPOCH_MS) / 1000, dt.timezone.utc)


def _hn_page(url: str) -> dict | None:
    try:
        html = get(url, timeout=15).decode("utf-8", "replace")
    except Exception:
        return None
    title = re.search(r"<title>(.*?)(?: \| HuggingNews)?</title>", html, re.S)
    published = re.search(r'"datePublished":"([^"]+)"', html)
    return {"title": strip_html(title.group(1)) if title else "",
            "published": published.group(1) if published else None,
            "credits": sorted(set(X_STATUS.findall(html)))}


def huggingnews(cfg: dict, max_age) -> list[dict]:
    """Stories HuggingNews filed or updated inside the window.

    Only the headline is kept, as a tip, and the X posts it credits, which
    are the primary sources. None of its prose is stored or used.
    """
    cutoff = utcnow() - max_age
    days = {utcnow().date(), (utcnow() - dt.timedelta(days=1)).date()}
    entries = []
    for day in sorted(days):
        try:
            xml = get(f"https://huggingnews.com/sitemaps/stories-{day.isoformat()}.xml").decode()
        except Exception:
            continue
        for loc, mod in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml):
            stamp = _when(mod)
            if stamp and stamp >= cutoff:
                entries.append((loc, stamp))
    entries.sort(key=lambda e: e[1], reverse=True)
    entries = entries[: cfg["tips"]["huggingnews"]["max_pages"]]
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = list(pool.map(lambda e: _hn_page(e[0]), entries))
    out = []
    for (loc, stamp), page in zip(entries, pages):
        if not page or not page["title"]:
            continue
        # HuggingNews re-files "updates" on events a day or two old, so its
        # own timestamp says nothing about freshness. The credited posts do:
        # the oldest is when the event broke, the newest is the latest turn.
        dated = sorted((t, u) for u in page["credits"] if (t := x_posted_at(u)))
        if not dated:
            continue
        broke, (latest, latest_url) = dated[0][0], dated[-1]
        if broke < cutoff:
            # An old event. Keep it only if something new was said about it
            # inside the last few hours, and point at that post.
            if utcnow() - latest > dt.timedelta(hours=3):
                continue
            kind, primary, when = "update", latest_url, latest
            signal = (f"new post {_age_hours(latest)}h ago on an event that broke "
                      f"{_age_hours(broke)}h ago; HuggingNews credits {len(dated)} X posts")
        else:
            kind, primary, when = "tip", dated[0][1], broke
            signal = (f"broke {_age_hours(broke)}h ago; HuggingNews credits "
                      f"{len(dated)} X posts")
        out.append(find(kind, page["title"], primary, "HuggingNews (tip)", signal, when,
                        rank=100 - (_age_hours(when) or 0),
                        extra={"credits": [u for _, u in dated], "tip_url": loc}))
    return out


def tip_feeds(cfg: dict, max_age) -> list[dict]:
    from xml.etree import ElementTree as ET
    cutoff = utcnow() - max_age
    terms = cfg["hackernews"]["ai_terms"]
    out = []
    for feed in cfg["tips"].get("feeds", []):
        try:
            root = ET.fromstring(get(feed["url"]))
        except Exception:
            continue
        for item in root.findall(".//item"):
            stamp = parse_date(item.findtext("pubDate"))
            if stamp is None or stamp < cutoff:
                continue
            title = strip_html(item.findtext("title") or "")
            if feed.get("ai_only") and not _is_ai(title, terms):
                continue
            desc = item.findtext("description") or ""
            # Techmeme's item links to itself; the story it points at is the
            # first outbound link in the description. That is the source.
            outbound = [u for u in re.findall(r'HREF="(https?://[^"]+)"', desc, re.I)
                        if "techmeme.com" not in u]
            link = outbound[0] if outbound else (item.findtext("link") or "").strip()
            title = re.sub(r"\s*\([^()]*/[^()]*\)\s*$", "", title)   # drop "(Reporter/Outlet)"
            out.append(find("tip", title, link, f"{feed['name']} (tip)",
                            f"on {feed['name']} {_age_hours(stamp)}h ago", stamp,
                            rank=100 - (_age_hours(stamp) or 0)))
    return out


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
        if votes < c["min_upvotes"] or not _fresh(p.get("submittedOnDailyAt"), max_age):
            continue
        org = (row.get("organization") or p.get("organization") or {}).get("fullname")
        extra = {"project_page": p.get("projectPage"), "github": p.get("githubRepo")}
        signal = f"{votes} upvotes on Hugging Face daily papers" + (f"; from {org}" if org else "")
        out.append(find("paper", p.get("title", ""), f"https://huggingface.co/papers/{p.get('id')}",
                        org or "arXiv", signal, p.get("submittedOnDailyAt") or row.get("publishedAt"),
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
        if not _fresh(h.get("created_at"), max_age):
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
    since = int(time.time() - max_age.total_seconds())
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


# (label, collector, key into max_age_hours)
COLLECTORS = [("HuggingNews", huggingnews, "tips"), ("Techmeme, TestingCatalog", tip_feeds, "tips"),
              ("Hugging Face models", hf_models, "models"), ("Hugging Face Spaces", hf_spaces, "spaces"),
              ("Hugging Face papers", hf_papers, "papers"), ("Hacker News", hn_front, "hn"),
              ("Show HN", hn_show, "show_hn")]


def collect() -> tuple[list[dict], list[str]]:
    cfg = load_cfg()
    windows = cfg.get("max_age_hours", {})
    already = carried()
    finds, report = [], []
    for name, fn, key in COLLECTORS:
        max_age = dt.timedelta(hours=windows.get(key, 24))
        try:
            got = fn(cfg, max_age)
        except Exception as exc:              # one dead source must not stop the cycle
            report.append(f"! {name:<20} FAIL {type(exc).__name__}")
            continue
        fresh = [f for f in got if normalize_url(f["url"]) not in already
                 and not (set(map(normalize_url, f.get("credits", []))) & already)]
        finds.extend(fresh)
        report.append(f"· {name:<24} {len(fresh)} new, {len(got) - len(fresh)} already carried"
                      f"  (last {windows.get(key, 24)}h)")
    finds.sort(key=lambda f: f["age_hours"] if f["age_hours"] is not None else 999)
    return finds, report


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect fresh finds: tips, Hugging Face, Hacker News.")
    ap.add_argument("--print", action="store_true", help="print, write nothing")
    args = ap.parse_args()

    finds, report = collect()
    print("\n".join(report))
    if args.print:
        for f in finds:
            print(f"  {f['age_hours']:>5}h [{f['kind']:<6}] {f['title'][:70]:<70}  {f['signal']}")
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
