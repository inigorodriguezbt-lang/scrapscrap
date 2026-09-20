"""Draft the paper's X posts, and hold them for review.

Every post uses the house template — headline, blank line, standfirst, blank
line, link — set out in style/09-social.md. The rest of that file comes from
measuring 72 posts across six newspapers; the two findings that decide
everything are that every post carried a link (72 of 72), and that none
carried a hashtag or an emoji.

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

# The house template is headline / standfirst / link, so the length is
# already governed upstream: the style checker caps a headline at 14 words
# and a standfirst at 32. What is left is the platform's own limit, and a
# post that somehow exceeds it falls back to the headline alone rather than
# being cut mid-sentence.
MAX_POST = 280
MAX_WIRE = 170           # the fallback form: headline and link only
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
    """Headline, then the link. The fallback, when there is no standfirst."""
    return f"{story['headline']}\n{url}"


def compose_house(story: dict, url: str) -> str:
    """The house template: headline, standfirst, link, each its own block.

    The headline runs exactly as it runs in the paper — no trailing period
    added, no rewording — so the post and the page say the same thing. The
    standfirst is the second block because it was already written to carry
    the fact the headline had to leave out, which is the job the sampled
    papers give that block. The link is last and alone, so the preview card
    attaches to it.
    """
    turn = (story.get("standfirst") or "").strip()
    if not turn:
        return compose_wire(story, url)
    return f"{story['headline']}\n\n{turn}\n\n{url}"


def compose(story: dict, cfg: dict) -> dict:
    url = story_url(story, cfg)
    style = "house"
    text = compose_house(story, url)

    # A post that still overruns falls back rather than being trimmed
    # mid-thought; a truncated sentence is worse than a plain headline.
    if weight(text) > MAX_POST:
        text, style = compose_wire(story, url), "wire (standfirst too long)"

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
    if post["style"] == "house":
        blocks = [b for b in text.split("\n\n") if b.strip()]
        if len(blocks) != 3:
            problems.append(f"{len(blocks)} blocks, the house template has three")
    if EMOJI.search(text):
        problems.append("emoji — none appeared in 72 sampled posts")
    if "#" in text:
        problems.append("hashtag — none appeared in 72 sampled posts")
    cap = MAX_POST if post["style"] == "house" else MAX_WIRE
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

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = QUEUE_DIR / f"{edition.get('edition_date', 'queue')}.json"
    out.write_text(json.dumps({
        "edition_date": edition.get("edition_date"),
        "drafted_at": utcnow().isoformat(),
        "status": "pending_review",
        "posts": posts,
    }, indent=2), encoding="utf-8")
    print(f"Queued for review → {out}")
    print("Nothing has been posted. Approve with /publish.")


if __name__ == "__main__":
    main()
