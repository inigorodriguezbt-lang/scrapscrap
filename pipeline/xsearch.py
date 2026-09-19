"""Search X through a paid provider, behind an interface.

X gates timeline reads behind a login, so reading it costs credentials or money
(see docs/x-access.md). This module talks to a provider interface rather than to
any one vendor: the providers here are small businesses, and one of them
shutting down should be a config change, not a rewrite.

Output matches the record shape pipeline/cluster.py consumes, so X results can
be clustered alongside the RSS wire.

Configure with environment variables, never a committed key:
    export XQUIK_API_KEY=xq_...
    export X_PROVIDER=xquik          # or: twitterapi

Usage:
    python -m pipeline.xsearch --query "from:OpenAI since:2026-09-18"
    python -m pipeline.xsearch --query "blackwell ultra" --limit 50
    python -m pipeline.xsearch --check
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .common import RAW_DIR, utcnow


class ProviderError(RuntimeError):
    pass


class Provider:
    """Minimum surface the paper needs from any X data vendor."""

    name = "abstract"
    env_key = ""

    def __init__(self) -> None:
        self.key = os.environ.get(self.env_key, "")

    @property
    def configured(self) -> bool:
        return bool(self.key)

    def search(self, query: str, limit: int) -> list[dict]:
        raise NotImplementedError

    # Shared: turn a vendor row into the paper's record shape.
    def _record(self, *, tweet_id, author, text, created, url, likes, reposts, replies) -> dict:
        return {
            "id": str(tweet_id),
            "handle": author,
            "author": author,
            "weight": 1.0,
            # An X post is someone speaking for themselves. Only the writer,
            # reading it, can decide whether that is a primary source here.
            "tier": "commentary",
            "text": text,
            "created_at": created,
            "url": url,
            "links": [url] if url else [],
            "likes": likes or 0,
            "reposts": reposts or 0,
            "replies": replies or 0,
            "is_repost": False,
            "is_reply": False,
            "provider": self.name,
        }


class Xquik(Provider):
    name = "xquik"
    env_key = "XQUIK_API_KEY"
    BASE = "https://api.xquik.com/v1"

    def search(self, query: str, limit: int) -> list[dict]:
        url = f"{self.BASE}/tweets/search?" + urllib.parse.urlencode(
            {"query": query, "limit": limit})
        req = urllib.request.Request(url, headers={
            "x-api-key": self.key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"xquik HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}")
        except Exception as exc:
            raise ProviderError(f"xquik {type(exc).__name__}: {exc}")

        rows = payload.get("data") or payload.get("tweets") or payload.get("results") or []
        out = []
        for row in rows:
            author = (row.get("author") or {})
            handle = author.get("username") or author.get("screen_name") or row.get("username") or "unknown"
            tid = row.get("id") or row.get("id_str") or ""
            out.append(self._record(
                tweet_id=tid,
                author=handle,
                text=row.get("text") or row.get("full_text") or "",
                created=row.get("created_at") or utcnow().isoformat(),
                url=row.get("url") or (f"https://x.com/{handle}/status/{tid}" if tid else ""),
                likes=row.get("like_count") or row.get("favorite_count"),
                reposts=row.get("retweet_count"),
                replies=row.get("reply_count"),
            ))
        return out


class TwitterAPIio(Provider):
    name = "twitterapi"
    env_key = "TWITTERAPI_IO_KEY"
    BASE = "https://api.twitterapi.io/twitter"

    def search(self, query: str, limit: int) -> list[dict]:
        url = f"{self.BASE}/tweet/advanced_search?" + urllib.parse.urlencode(
            {"query": query, "queryType": "Latest"})
        req = urllib.request.Request(url, headers={"X-API-Key": self.key})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read())
        except Exception as exc:
            raise ProviderError(f"twitterapi {type(exc).__name__}: {exc}")

        out = []
        for row in (payload.get("tweets") or [])[:limit]:
            author = (row.get("author") or {}).get("userName", "unknown")
            out.append(self._record(
                tweet_id=row.get("id", ""), author=author,
                text=row.get("text", ""),
                created=row.get("createdAt") or utcnow().isoformat(),
                url=row.get("url", ""), likes=row.get("likeCount"),
                reposts=row.get("retweetCount"), replies=row.get("replyCount"),
            ))
        return out


PROVIDERS = {p.name: p for p in (Xquik, TwitterAPIio)}


def get_provider() -> Provider:
    name = os.environ.get("X_PROVIDER", "xquik").lower()
    if name not in PROVIDERS:
        raise SystemExit(f"Unknown X_PROVIDER {name!r}. Options: {', '.join(PROVIDERS)}")
    return PROVIDERS[name]()


def main() -> None:
    ap = argparse.ArgumentParser(description="Search X through a paid provider.")
    ap.add_argument("--query", help="X search string; advanced operators allowed")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--check", action="store_true", help="report configuration only")
    ap.add_argument("--out", type=Path, help="write JSONL here instead of stdout")
    args = ap.parse_args()

    provider = get_provider()

    if args.check:
        print(f"provider : {provider.name}")
        print(f"env var  : {provider.env_key}")
        print(f"key set  : {'yes' if provider.configured else 'NO'}")
        if not provider.configured:
            print(f"\nNot configured. Set {provider.env_key}, or use the hosted MCP server:")
            print("  claude mcp add --transport http xquik https://xquik.com/mcp \\")
            print('    --header "x-api-key: $XQUIK_API_KEY"')
            print("\nSee docs/x-access.md for costs and the terms-of-service question.")
        return

    if not args.query:
        ap.error("--query is required unless --check is given")

    if not provider.configured:
        sys.exit(f"{provider.env_key} is not set. Run --check, or see docs/x-access.md.")

    records = provider.search(args.query, args.limit)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"{len(records)} posts → {args.out}")
    else:
        for record in records:
            print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
