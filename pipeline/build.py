"""Render the written editions into a static site.

Reads every file in data/editions/, renders the newest as the front page, and
gives each story, section, and back issue its own page. Output is plain HTML in
dist/ -- no server, no database, deployable anywhere.

Usage:
    python -m pipeline.build
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .common import DIST_DIR, EDITIONS_DIR, SITE_DIR, load_config, utcnow


def long_date(iso: str) -> str:
    day = datetime.strptime(iso, "%Y-%m-%d")
    # Strip the zero-pad without %-d, which is not portable.
    return day.strftime("%A, %B ") + str(day.day) + day.strftime(", %Y")


def load_editions() -> list[dict]:
    editions = []
    for path in sorted(EDITIONS_DIR.glob("*.json")):
        edition = json.loads(path.read_text(encoding="utf-8"))
        edition.setdefault("edition_date", path.stem)
        editions.append(edition)
    return editions


def decorate(stories: list[dict], sections: list[dict]) -> list[dict]:
    """Attach display names, and make the template's assumptions safe."""
    names = {s["slug"]: s["name"] for s in sections}
    for story in stories:
        story["section_name"] = names.get(story.get("section"), "Dispatches")
        story.setdefault("entities", [])
        story.setdefault("sources", [])
        story.setdefault("body", [])
        story.setdefault("standfirst", "")
    return stories


def render_site() -> None:
    cfg = load_config()
    sections = cfg["sections"]
    editions = load_editions()

    env = Environment(
        loader=FileSystemLoader(SITE_DIR / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    for sub in ("story", "section", "issue"):
        (DIST_DIR / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(SITE_DIR / "style.css", DIST_DIR / "style.css")

    latest = editions[-1] if editions else {"edition_date": utcnow().strftime("%Y-%m-%d"), "stories": []}
    stories = decorate(latest.get("stories", []), sections)

    all_sources = {s["author"] for story in stories for s in story["sources"]}
    base = {
        "paper": cfg["paper"],
        "sections": sections,
        "min_sources": cfg["editorial"]["min_independent_sources"],
        "edition_number": len(editions),
        "edition_date_long": long_date(latest["edition_date"]),
        "generated_at_short": utcnow().strftime("%H:%M UTC"),
        "story_count": len(stories),
        "source_count": len(all_sources),
        "current_section": None,
    }

    by_placement = lambda kind: [s for s in stories if s.get("placement") == kind]
    lead_list = by_placement("lead")
    lead = lead_list[0] if lead_list else (stories[0] if stories else None)
    front = [s for s in by_placement("front") if s is not lead]

    # The rail carries the next few front-page items; the deck carries the rest.
    env.get_template("front.html").stream(
        **base, rel="", stories=stories, lead=lead,
        briefs=front[:4], front=front[4:], inside=by_placement("inside"),
    ).dump(str(DIST_DIR / "index.html"))

    for story in stories:
        env.get_template("story.html").stream(
            **{**base, "current_section": story.get("section")},
            rel="../", story=story,
        ).dump(str(DIST_DIR / "story" / f"{story['cluster_id']}.html"))

    for section in sections:
        env.get_template("section.html").stream(
            **{**base, "current_section": section["slug"]},
            rel="../", section=section,
            stories=[s for s in stories if s.get("section") == section["slug"]],
        ).dump(str(DIST_DIR / "section" / f"{section['slug']}.html"))

    issues = []
    for edition in reversed(editions):
        date = edition["edition_date"]
        issue_stories = decorate(edition.get("stories", []), sections)
        issues.append({"date": date, "date_long": long_date(date), "count": len(issue_stories)})
        env.get_template("front.html").stream(
            **{**base, "edition_date_long": long_date(date), "story_count": len(issue_stories)},
            rel="../", stories=issue_stories,
            lead=next((s for s in issue_stories if s.get("placement") == "lead"), None),
            briefs=[s for s in issue_stories if s.get("placement") == "front"][:4],
            front=[s for s in issue_stories if s.get("placement") == "front"][4:],
            inside=[s for s in issue_stories if s.get("placement") == "inside"],
        ).dump(str(DIST_DIR / "issue" / f"{date}.html"))

    env.get_template("archive.html").stream(**base, rel="", issues=issues).dump(
        str(DIST_DIR / "archive.html")
    )

    pages = len(list(DIST_DIR.rglob("*.html")))
    print(f"Rendered {pages} pages → {DIST_DIR}")
    print(f"  front page: {len(stories)} stories, {len(all_sources)} sources, {len(issues)} back issues")


if __name__ == "__main__":
    render_site()
