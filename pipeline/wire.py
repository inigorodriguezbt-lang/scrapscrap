"""Pull the wire from RSS/Atom feeds and the arXiv API.

This replaces account scraping as the paper's ingestion layer. It emits exactly
the record shape pipeline/cluster.py already consumes, so everything downstream
-- clustering, /write-edition, stylecheck, build -- works unchanged.

Two outlets independently covering the same event is stronger corroboration
than two accounts posting about it, so the paper's two-source rule means more
here than it did on social ingestion.

Usage:
    python -m pipeline.wire                 # collect the last 24h
    python -m pipeline.wire --hours 12
    python -m pipeline.wire --check         # verify every feed, write nothing
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import json
import re
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

from .common import RAW_DIR, ROOT, utcnow

ATOM = {"a": "http://www.w3.org/2005/Atom"}
DC = "{http://purl.org/dc/elements/1.1/}date"
UA = "Mozilla/5.0 (compatible; LatentTimes/1.0; newsroom wire reader)"
FEEDS_PATH = ROOT / "config" / "feeds.yaml"


def load_feeds() -> dict:
    with FEEDS_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


def parse_date(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        return email.utils.parsedate_to_datetime(raw).astimezone(dt.timezone.utc)
    except Exception:
        pass
    text = raw.strip().replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(text[:25], fmt)
            return parsed.astimezone(dt.timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
        except Exception:
            continue
    return None


def strip_html(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()


def field(node, *names) -> str:
    for name in names:
        value = node.findtext(name)
        if value:
            return value
        value = node.findtext(f"a:{name}", default=None, namespaces=ATOM)
        if value:
            return value
    return ""


def link_of(node) -> str:
    raw = node.findtext("link")
    if raw and raw.strip():
        return raw.strip()
    for link in node.findall("a:link", ATOM):
        if link.get("rel") in (None, "alternate") and link.get("href"):
            return link.get("href")
    return ""


def read_feed(source: dict, cutoff: dt.datetime) -> tuple[list[dict], str]:
    """Return (records, status). One broken feed must not stop the edition."""
    try:
        root = ET.fromstring(get(source["url"]))
    except Exception as exc:
        return [], f"FAIL {type(exc).__name__}"

    entries = root.findall(".//item") or root.findall(".//a:entry", ATOM)
    records, skipped = [], 0

    for entry in entries:
        published = parse_date(field(entry, "pubDate", "published", "updated") or entry.findtext(DC))
        if published is None or published < cutoff:
            skipped += 1
            continue

        title = strip_html(field(entry, "title"))
        summary = strip_html(field(entry, "description", "summary", "content"))[:600]
        url = link_of(entry)
        if not title:
            continue

        records.append({
            "id": url or f"{source['name']}:{title[:60]}",
            "handle": source["name"],
            "author": source["name"],
            "weight": source.get("weight", 1.0),
            "tier": source.get("tier", "press"),
            # Title carries the event; the summary gives clustering more to bite on.
            "text": f"{title}. {summary}" if summary else title,
            "title": title,
            "created_at": published.isoformat(),
            "url": url,
            "links": [url] if url else [],
            "likes": 0, "reposts": 0, "replies": 0,
            "is_repost": False, "is_reply": False,
        })

    return records, f"{len(records)} new, {skipped} older"


def read_arxiv(cfg: dict, cutoff: dt.datetime) -> tuple[list[dict], str]:
    if not cfg.get("enabled"):
        return [], "disabled"
    query = "+OR+".join(f"cat:{c}" for c in cfg["categories"])
    url = (f"http://export.arxiv.org/api/query?search_query={query}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={cfg['max_results']}")
    try:
        root = ET.fromstring(get(url, timeout=30))
    except Exception as exc:
        return [], f"FAIL {type(exc).__name__}"

    records = []
    for entry in root.findall("a:entry", ATOM):
        published = parse_date(entry.findtext("a:published", default=None, namespaces=ATOM))
        if published is None or published < cutoff:
            continue
        title = strip_html(entry.findtext("a:title", default="", namespaces=ATOM))
        summary = strip_html(entry.findtext("a:summary", default="", namespaces=ATOM))[:600]
        link = link_of(entry)
        records.append({
            "id": link or title[:60], "handle": "arXiv", "author": "arXiv",
            "weight": cfg.get("weight", 1.0), "tier": cfg.get("tier", "primary"),
            "text": f"{title}. {summary}", "title": title,
            "created_at": published.isoformat(), "url": link,
            "links": [link] if link else [],
            "likes": 0, "reposts": 0, "replies": 0,
            "is_repost": False, "is_reply": False,
        })
    return records, f"{len(records)} new"


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect the wire from feeds.")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--check", action="store_true", help="verify feeds, write nothing")
    args = ap.parse_args()

    cfg = load_feeds()
    cutoff = utcnow() - dt.timedelta(hours=args.hours if not args.check else 24 * 30)
    records, failures = [], []

    for source in cfg["feeds"]:
        found, status = read_feed(source, cutoff)
        records.extend(found)
        if status.startswith("FAIL"):
            failures.append(source["name"])
        print(f"  {'!' if status.startswith('FAIL') else '·'} {source['name']:<18} {status}")

    found, status = read_arxiv(cfg.get("arxiv", {}), cutoff)
    records.extend(found)
    print(f"  {'!' if status.startswith('FAIL') else '·'} {'arXiv':<18} {status}")

    if args.check:
        print(f"\n{len(cfg['feeds']) + 1} sources checked, {len(failures)} failing"
              + (f": {', '.join(failures)}" if failures else ""))
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"wire-{utcnow().strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    outlets = len({r["handle"] for r in records})
    print(f"\n{len(records)} items from {outlets} sources → {out}")
    if failures:
        print(f"failing: {', '.join(failures)}")


if __name__ == "__main__":
    main()
