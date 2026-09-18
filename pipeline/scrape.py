"""Pull recent posts from the paper's source accounts into a raw JSONL log.

This is the wire service. It makes no editorial decisions -- it only collects.
Clustering (pipeline/cluster.py) decides what is a story.

Usage:
    python -m pipeline.scrape --hours 24
    python -m pipeline.scrape --hours 24 --limit 80

Requires a twscrape account pool to be set up once:
    twscrape add_accounts accounts.txt username:password:email:email_password
    twscrape login_accounts
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .common import RAW_DIR, load_config, utcnow


def _post_to_record(tweet, source) -> dict:
    """Flatten a twscrape tweet into the only shape the rest of the pipeline knows."""
    urls = []
    for link in getattr(tweet, "links", None) or []:
        url = getattr(link, "url", None) or getattr(link, "expandedUrl", None)
        if url:
            urls.append(url)

    return {
        "id": str(tweet.id),
        "handle": source["handle"],
        "author": getattr(tweet.user, "username", source["handle"]),
        "weight": source.get("weight", 1.0),
        "tier": source.get("tier", "commentary"),
        "text": tweet.rawContent,
        "created_at": tweet.date.astimezone(timezone.utc).isoformat(),
        "url": f"https://x.com/{getattr(tweet.user, 'username', source['handle'])}/status/{tweet.id}",
        "links": urls,
        "likes": getattr(tweet, "likeCount", 0) or 0,
        "reposts": getattr(tweet, "retweetCount", 0) or 0,
        "replies": getattr(tweet, "replyCount", 0) or 0,
        "is_repost": getattr(tweet, "retweetedTweet", None) is not None,
        "is_reply": getattr(tweet, "inReplyToTweetId", None) is not None,
    }


async def collect(hours: int, limit: int) -> list[dict]:
    try:
        from twscrape import API
    except ImportError:
        sys.exit(
            "twscrape is not installed.\n"
            "  pip install -r requirements.txt\n"
            "then set up an account pool -- see README 'Wiring the scraper'."
        )

    cfg = load_config()
    api = API()
    cutoff = utcnow() - timedelta(hours=hours)
    records: list[dict] = []

    for source in cfg["sources"]:
        handle = source["handle"]
        try:
            user = await api.user_by_login(handle)
            if user is None:
                print(f"  ! {handle}: not found, skipping", file=sys.stderr)
                continue

            kept = 0
            async for tweet in api.user_tweets_and_replies(user.id, limit=limit):
                # The timeline is newest-first, so the first post older than the
                # cutoff means every post after it is older too.
                if tweet.date.astimezone(timezone.utc) < cutoff:
                    break
                records.append(_post_to_record(tweet, source))
                kept += 1

            print(f"  · {handle}: {kept} posts")
        except Exception as exc:  # one bad account must not kill the edition
            print(f"  ! {handle}: {type(exc).__name__}: {exc}", file=sys.stderr)

        # Be unhurried. twscrape rotates accounts, but pacing reduces flags.
        await asyncio.sleep(1.0)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect posts from source accounts.")
    parser.add_argument("--hours", type=int, default=24, help="lookback window")
    parser.add_argument("--limit", type=int, default=60, help="max posts per account")
    args = parser.parse_args()

    print(f"Collecting the last {args.hours}h from source accounts…")
    records = asyncio.run(collect(args.hours, args.limit))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = RAW_DIR / f"posts-{stamp}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n{len(records)} posts → {out}")


if __name__ == "__main__":
    main()
