"""The copy file: this run's articles, in full, ready to copy and paste.

The editor wants every new story's headline and full text off the site and
into their hands without pasting a wall of text into the chat. So each cycle
writes one Markdown file with just this run's stories (the ids the merge step
recorded in data/state/last_run.json): headline, standfirst, body, the live
URL, and the post drafted for it. The cycle sends that file; the chat reply
stays a short list of headlines.

It also writes `<name>.txt`, the body of the email the cycle sends the
editor: the same articles in clean plain text, without the X posts. Plain
text, not HTML: an earlier HTML body reached the inbox escaped, as raw code.

Usage:
    python -m pipeline.copydesk                      # today's edition
    python -m pipeline.copydesk --edition data/editions/2026-09-24.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from .common import DATA_DIR, EDITIONS_DIR, load_config, utcnow
from .embeds import after as embeds_after
from .merge import LAST_RUN

COPY_DIR = DATA_DIR / "copy"
RULE = "-" * 60


def this_run_ids() -> list[str]:
    try:
        return json.loads(LAST_RUN.read_text(encoding="utf-8"))["added"]
    except (OSError, ValueError, KeyError):
        return []


def queued_post(day: str, cluster_id: str) -> str:
    """The drafted X post for a story, if pipeline.social has queued one."""
    try:
        queue = json.loads((DATA_DIR / "queue" / f"{day}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    for post in queue.get("posts", []):
        if post.get("cluster_id") == cluster_id:
            return post.get("text", "")
    return ""


def render(stories: list[dict], day: str, site: str, posts: bool = True) -> str:
    stamp = utcnow().strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# The AI Post: {len(stories)} new {'story' if len(stories) == 1 else 'stories'}",
           f"_{stamp}_", ""]
    for s in stories:
        url = f"{site}/story/{s['cluster_id']}/"
        out += [RULE, "", f"## {s['headline']}", "", f"**{s.get('standfirst', '')}**", ""]
        # Embeds go on their own line after their paragraph: pasted into an
        # article editor, a bare X or YouTube link becomes the embed.
        for i, para in enumerate(s.get("body", []), 1):
            out += [para + "\n"]
            out += [e["url"] + "\n" for e in embeds_after(s, i)]
        out += [f"Read it on the site: {url}", ""]
        sources = ", ".join(src.get("author", "") for src in s.get("sources", []) if src.get("author"))
        if sources:
            out += [f"_Sources: {sources}_", ""]
        post = queued_post(day, s["cluster_id"]) if posts else ""
        if post:
            out += ["Post for X:", "", "```", post, "```", ""]
    return "\n".join(out).rstrip() + "\n"


def to_plain(markdown: str) -> str:
    """The copy file as clean plain text: no Markdown markers, links bare.

    This is the email body. Plain text is what the sending step can pass on
    without mangling it, and it pastes into an article editor as-is, with
    each embed link on its own line.
    """
    lines = []
    for line in markdown.split("\n"):
        line = re.sub(r"^#{1,2} ", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", line)
        lines.append(line)
    return "\n".join(lines)


def to_email_html(markdown: str) -> str:
    """The copy file as an email body: readable on a phone, easy to copy from."""
    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
        return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', text)

    out, code, buf = [], False, []
    for line in markdown.split("\n"):
        if line.startswith("```"):
            if code:
                out.append('<pre style="background:#f4f4f4;padding:10px;white-space:pre-wrap;'
                           'font-family:inherit">' + html.escape("\n".join(buf)) + "</pre>")
                buf = []
            code = not code
            continue
        if code:
            buf.append(line)
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2 style='margin-top:28px'>{inline(line[3:])}</h2>")
        elif re.fullmatch(r"-{10,}", line):
            out.append("<hr>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    return ("<div style='font-family:Georgia,serif;font-size:16px;line-height:1.5;"
            "max-width:680px'>" + "\n".join(out) + "</div>\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Write this run's stories to a copy file.")
    ap.add_argument("--edition", type=Path)
    ap.add_argument("--ids", nargs="*", help="cluster ids (default: this run's, from last_run.json)")
    args = ap.parse_args()

    edition_path = args.edition or EDITIONS_DIR / f"{utcnow().date().isoformat()}.json"
    day = edition_path.stem
    edition = json.loads(edition_path.read_text(encoding="utf-8"))
    wanted = args.ids if args.ids else this_run_ids()
    by_id = {s["cluster_id"]: s for s in edition.get("stories", [])}
    stories = [by_id[i] for i in wanted if i in by_id]
    if not stories:
        print("No new stories this run; no copy file written.")
        return

    site = load_config()["paper"].get("site_url", "").rstrip("/")
    COPY_DIR.mkdir(parents=True, exist_ok=True)
    out = COPY_DIR / f"{day}-{utcnow().strftime('%H%M')}.md"
    out.write_text(render(stories, day, site), encoding="utf-8")
    # The email version: the same articles without the X posts, as HTML for
    # the body and plain text for the fallback.
    email = render(stories, day, site, posts=False)
    out.with_suffix(".txt").write_text(to_plain(email), encoding="utf-8")
    print(f"{len(stories)} stories → {out} (+ .txt email body, without X posts)")
    for s in stories:
        print(f"  · {s['headline']}")


if __name__ == "__main__":
    main()
