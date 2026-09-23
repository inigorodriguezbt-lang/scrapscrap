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
    python -m pipeline.xsearch --sources 100 --budget 100   # the hourly sweep
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


def _iso(value) -> str:
    """The API returns unix seconds; the rest of the pipeline wants ISO."""
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(int(value), dt.timezone.utc).isoformat()
    return value or utcnow().isoformat()


def load_watermark(path: Path) -> int | None:
    """Epoch of the newest post the last sweep already paid for."""
    try:
        return int(json.loads(path.read_text(encoding="utf-8"))["last_epoch"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_watermark(path: Path, records: list[dict], fallback: int) -> int:
    """Advance the mark past the newest row we just bought.

    Billing is one credit per delivered post, so a sweep that re-asks for
    posts it already holds pays for them twice. The mark is what stops that.
    """
    if not records:
        # Nothing new. Holding the mark still matters: nudging it forward on
        # every quiet sweep would walk past posts that land in the skipped
        # seconds, and a quiet sweep costs nothing anyway.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_epoch": fallback}, indent=1) + "\n", encoding="utf-8")
        return fallback

    newest = fallback
    for record in records:
        try:
            stamp = dt.datetime.fromisoformat(record["created_at"])
        except (ValueError, KeyError, TypeError):
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
        newest = max(newest, int(stamp.timestamp()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_epoch": newest + 1}, indent=1) + "\n", encoding="utf-8")
    return newest + 1


def source_batches(count: int, per_batch: int = 20, min_faves: int = 0) -> list[str]:
    """`(from:a OR from:b ...)` over the top `count` configured handles.

    Batched because a single query carrying 100 handles is long enough that
    the search rejects it. Twenty per request is tested and works.
    `min_faves` drops the low-traction posts before they are billed.
    """
    from .common import load_config
    handles = [s["handle"] for s in load_config().get("sources", [])][:count]
    tail = f" min_faves:{min_faves}" if min_faves else ""
    return ["(" + " OR ".join(f"from:{h}" for h in handles[i:i + per_batch]) + ")" + tail
            for i in range(0, len(handles), per_batch)]


def budgeted_plan(count: int, budget: int) -> list[tuple[str, int]]:
    """(query, limit) pairs whose limits add up to no more than `budget`.

    Credits are the constraint, so the cap is per cycle across every query,
    not per query. config/discover.yaml sets the split: the account sweep
    gets `sweep_share`, the discovery queries share what is left.
    """
    import yaml
    from .common import ROOT
    x = yaml.safe_load((ROOT / "config" / "discover.yaml").read_text(encoding="utf-8")).get("x", {})
    sweep = source_batches(count, min_faves=x.get("min_faves", 0))
    extra = x.get("queries", []) or []
    sweep_total = min(budget, x.get("sweep_share", budget)) if extra else budget
    plan = [(q, sweep_total // len(sweep)) for q in sweep] if sweep else []
    left = budget - sum(n for _, n in plan)
    if extra and left > 0:
        plan += [(q, left // len(extra)) for q in extra]
    return [(q, n) for q, n in plan if n > 0]


class Provider:
    """Minimum surface the paper needs from any X data vendor."""

    name = "abstract"
    env_key = ""

    def __init__(self) -> None:
        self.key = os.environ.get(self.env_key, "")

    @property
    def configured(self) -> bool:
        return bool(self.key)

    def search(self, query: str, limit: int, since_epoch: int | None = None) -> list[dict]:
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
    # The live REST surface is xquik.com/api/v1, and the search parameter is
    # "q". An earlier guess at api.xquik.com/v1 with "query" 404s.
    BASE = "https://xquik.com/api/v1"

    def search(self, query: str, limit: int, since_epoch: int | None = None) -> list[dict]:
        params = {"q": query, "limit": limit}
        if since_epoch:
            # Only posts newer than the last run. Without this the same rows
            # come back every sweep and every one of them is billed again.
            params["sinceTime"] = int(since_epoch)
        url = f"{self.BASE}/x/tweets/search?" + urllib.parse.urlencode(params)
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
                created=_iso(row.get("created_at")),
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
    ap.add_argument("--sources", type=int, metavar="N",
                    help="sweep the top N configured handles instead of --query")
    ap.add_argument("--budget", type=int, metavar="N",
                    help="with --sources: at most N posts this cycle across the "
                         "sweep and the discovery queries in config/discover.yaml")
    ap.add_argument("--state", type=Path,
                    help="high-water-mark file; only posts newer than the last "
                         "run are fetched, so none is paid for twice")
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

    if not args.query and not args.sources:
        ap.error("--query or --sources is required unless --check is given")

    if not provider.configured:
        sys.exit(f"{provider.env_key} is not set. Run --check, or see docs/x-access.md.")

    since = load_watermark(args.state) if args.state else None
    if args.sources and args.budget:
        plan = budgeted_plan(args.sources, args.budget)
    elif args.sources:
        plan = [(q, args.limit) for q in source_batches(args.sources)]
    else:
        plan = [(args.query, args.limit)]

    records: list[dict] = []
    for query, limit in plan:
        records.extend(provider.search(query, limit, since_epoch=since)[:limit])

    seen: set[str] = set()
    records = [r for r in records if not (r["id"] in seen or seen.add(r["id"]))]

    if args.state:
        mark = save_watermark(args.state, records, since or int(utcnow().timestamp()))
        window = "everything" if since is None else f"since {_iso(since)}"
        print(f"{len(records)} posts, {window}; next sweep starts at {_iso(mark)}")

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
