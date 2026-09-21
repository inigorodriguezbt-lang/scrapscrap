"""Draft the paper's X posts, and hold them for review.

Every rule here comes from measuring 72 posts across six newspapers; the
findings are in style/09-social.md. The two that decide everything: every post
carried a link (72 of 72), and none carried a hashtag or an emoji.

Nothing here posts anything. It drafts into data/queue/ and stops. Publishing
happens only after the editor approves — see .claude/commands/publish.md.

Usage:
    python -m pipeline.social --edition data/editions/2026-09-19.json
    python -m pipeline.social --edition ... --check      # validate, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .common import DATA_DIR, load_config, utcnow

QUEUE_DIR = DATA_DIR / "queue"

# Calibrated to the sample rather than to a round number. Wire posts ran to a
# median of 108 characters, sell posts to 223. A single cap set between them
# silently demoted every sell post to wire.
MAX_WIRE = 170
MAX_SELL = 260
URL_LENGTH = 23          # X counts every link as 23 characters

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿]"
)
HYPE = re.compile(
    r"\b(huge|massive|insane|wild|breakthrough|game.?chang\w+|revolutionary|"
    r"unprecedented|you won'?t believe|thread)\b", re.I)


def story_url(story: dict, cfg: dict) -> str:
    base = cfg["paper"].get("site_url", "").rstrip("/")
    return f"{base}/story/{story['cluster_id']}/"


def weight(text: str) -> int:
    """X counts a URL as 23 characters however long it is."""
    without = re.sub(r"https?://\S+", "", text)
    links = len(re.findall(r"https?://\S+", text))
    return len(without) + links * URL_LENGTH


def compose_wire(story: dict, url: str) -> str:
    """Headline, then the link. The default, and the honest one."""
    return f"{story['headline']}\n{url}"


def compose_sell(story: dict, url: str) -> str:
    """Two blocks: the fact, then the thing that complicates it.

    Only earns its place on the lead, and only when the second block carries
    something the headline left out.
    """
    hook = story["headline"].rstrip(".")
    turn = (story.get("standfirst") or "").strip()
    if not turn:
        return compose_wire(story, url)
    return f"{hook}.\n\n{turn}\n\n{url}"


def compose(story: dict, cfg: dict) -> dict:
    url = story_url(story, cfg)
    style = "sell" if story.get("placement") == "lead" else "wire"
    text = compose_sell(story, url) if style == "sell" else compose_wire(story, url)

    # A sell post that still overruns falls back rather than being trimmed
    # mid-thought; a truncated sentence is worse than a plain headline.
    if style == "sell" and weight(text) > MAX_SELL:
        text, style = compose_wire(story, url), "wire (sell too long)"

    return {
        "cluster_id": story["cluster_id"],
        "style": style,
        "text": text,
        "chars": weight(text),
        "url": url,
        "status": "pending_review",
    }


def validate(post: dict) -> list[str]:
    text = post["text"]
    problems = []

    if not re.search(r"https?://\S+", text):
        problems.append("no link — every post in the sample carried one")
    if "/story/" in text and text.rstrip().split("\n")[-1].strip() != post["url"]:
        problems.append("link should be the final line")
    if EMOJI.search(text):
        problems.append("emoji — none appeared in 72 sampled posts")
    if "#" in text:
        problems.append("hashtag — none appeared in 72 sampled posts")
    cap = MAX_SELL if post["style"].startswith("sell") else MAX_WIRE
    if post["chars"] > cap:
        problems.append(f"{post['chars']} characters, over {cap} for a {post['style']} post")
    if HYPE.search(text):
        problems.append(f"hype wording: {HYPE.search(text).group(0)!r}")
    if text.rstrip().endswith("?"):
        problems.append("ends on a question")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Draft X posts for an edition.")
    ap.add_argument("--edition", type=Path, required=True)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--pending", action="store_true",
                    help="print only the posts the editor has not sent yet")
    args = ap.parse_args()

    cfg = load_config()
    edition = json.loads(args.edition.read_text(encoding="utf-8"))
    stories = edition.get("stories", [])
    if not stories:
        raise SystemExit("No stories in that edition.")

    if not cfg["paper"].get("site_url"):
        raise SystemExit("paper.site_url is not set in config/paper.yaml; a post needs a URL.")

    posts, failures = [], 0
    for story in stories:
        post = compose(story, cfg)
        problems = validate(post)
        post["problems"] = problems
        failures += bool(problems)
        posts.append(post)

        head = story["headline"][:52]
        print(f"\n[{post['style']}] {head}  ({post['chars']} chars)")
        for line in post["text"].split("\n"):
            print(f"    {line}" if line else "")
        for problem in problems:
            print(f"    ERROR  {problem}")

    print(f"\n{'─' * 58}")
    print(f"{len(posts)} drafted · {failures} with problems")

    if args.check:
        raise SystemExit(1 if failures else 0)

    if args.pending:
        pass        # handled after the queue is written, so statuses are current

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = QUEUE_DIR / f"{edition.get('edition_date', 'queue')}.json"

    # On an hourly cadence this file is rewritten every run. Carry over what
    # the editor has already done to each post, or a tweet sent at 09:00 looks
    # unsent again at 10:00 and gets posted twice.
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8")).get("posts", [])
        except (OSError, ValueError):
            previous = []
        kept = {p.get("cluster_id"): p for p in previous}
        for post in posts:
            before = kept.get(post["cluster_id"])
            if not before:
                continue
            for field in ("status", "note", "posted_url", "site_published_at"):
                if before.get(field):
                    post[field] = before[field]

    out.write_text(json.dumps({
        "edition_date": edition.get("edition_date"),
        "drafted_at": utcnow().isoformat(),
        "status": "pending_review",
        "posts": posts,
    }, indent=2), encoding="utf-8")
    print(f"Queued for review → {out}")
    print("Nothing has been posted. The editor sends these by hand.")

    if args.pending:
        unsent = [p for p in posts if p.get("status", "pending_review") == "pending_review"]
        print(f"\n{'═' * 58}\n{len(unsent)} post(s) waiting to be sent\n")
        for post in unsent:
            print(post["text"])
            print(f"\n{'─' * 58}\n")


if __name__ == "__main__":
    main()
