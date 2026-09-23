"""Paths, config loading, and the small text helpers shared across the pipeline."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "paper.yaml"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRIEFS_DIR = DATA_DIR / "briefs"
EDITIONS_DIR = DATA_DIR / "editions"
DIST_DIR = ROOT / "dist"
SITE_DIR = ROOT / "site"


DISCOVERED_PATH = ROOT / "config" / "discovered_sources.yaml"


def load_config() -> dict:
    """Load paper.yaml, folding in the discovered source list when enabled.

    The curated entries in paper.yaml win on conflict: a crawl can tell us how
    often an account is cited, but not whether it speaks for a lab. Discovered
    accounts are added, never allowed to overwrite a hand-set tier or weight.
    """
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    if cfg.get("source_list") == "merged" and DISCOVERED_PATH.exists():
        with DISCOVERED_PATH.open(encoding="utf-8") as fh:
            discovered = (yaml.safe_load(fh) or {}).get("sources", []) or []

        curated = {s["handle"].lower(): s for s in cfg.get("sources", [])}
        merged = list(cfg.get("sources", []))
        for source in discovered:
            if source["handle"].lower() not in curated:
                merged.append(source)
        cfg["sources"] = merged

    muted = {h.lower() for h in cfg.get("muted_sources", []) or []}
    if muted:
        cfg["sources"] = [s for s in cfg["sources"] if s["handle"].lower() not in muted]

    return cfg


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Words too common in this beat to say anything about *which* story a post is.
STOPWORDS = set("""
a an and are as at be been but by for from has have how in into is it its of on
or that the their they this to was were what when where which who will with you
your we our us i he she them his her not no do does did can could would should
just new now today more most very much many some all any out up down über over
ai model models llm open source release released launch launches launched
announcing announced announce introducing introduce introduced excited thrilled
today's here thread via rt amp http https com www t co
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-\.\+]{1,}")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, minus handles, URLs, and beat-specific noise."""
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = text.lower()
    return [t for t in _TOKEN_RE.findall(text) if t not in STOPWORDS and len(t) > 2]


def normalize_url(url: str) -> str:
    """Strip tracking junk so the same link from two accounts compares equal."""
    url = re.sub(r"[?#].*$", "", url.strip())
    url = re.sub(r"^https?://(www\.)?", "", url)
    return url.rstrip("/").lower()
