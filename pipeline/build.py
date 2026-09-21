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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .cards import render as render_card
from .common import DIST_DIR, EDITIONS_DIR, SITE_DIR, load_config, utcnow


def long_date(iso: str) -> str:
    day = datetime.strptime(iso, "%Y-%m-%d")
    # Strip the zero-pad without %-d, which is not portable.
    return day.strftime("%A, %B ") + str(day.day) + day.strftime(", %Y")


def relative_time(stamp: str | None) -> str:
    """A newspaper's rail is timestamped; that is what makes it read as live."""
    if not stamp:
        return "—"
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return "—"
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    minutes = (utcnow() - when).total_seconds() / 60
    if minutes < 1:
        return "now"
    if minutes < 60:
        return f"{int(minutes)}m"
    if minutes < 1440:
        return f"{int(minutes // 60)}h"
    return when.strftime("%d %b")


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
        story.setdefault("image", None)
        story.setdefault("topic", None)
        story["time_label"] = relative_time(story.get("published_at"))
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
    # A hyphen inside a name ("Atlas-3", "GPT-5") must not become a line
    # break in a headline. U+2011 is the non-breaking hyphen.
    import re as _re
    env.filters["nbhy"] = lambda text: _re.sub(r"(?<=\w)-(?=\w)", "\u2011", text or "")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    for sub in ("story", "section", "issue"):
        (DIST_DIR / sub).mkdir(parents=True, exist_ok=True)

    def page(*parts: str) -> str:
        """A page at /a/b/ is written to a/b/index.html, so the URL carries
        no .html extension. Returns the path to dump into."""
        target = DIST_DIR.joinpath(*parts)
        target.mkdir(parents=True, exist_ok=True)
        return str(target / "index.html")
    import hashlib
    css_bytes = (SITE_DIR / "style.css").read_bytes()
    css_version = hashlib.sha256(css_bytes).hexdigest()[:8]
    shutil.copy(SITE_DIR / "style.css", DIST_DIR / "style.css")
    assets = SITE_DIR / "assets"
    if assets.exists():
        shutil.copytree(assets, DIST_DIR / "assets", dirs_exist_ok=True)

    latest = editions[-1] if editions else {"edition_date": utcnow().strftime("%Y-%m-%d"), "stories": []}
    stories = decorate(latest.get("stories", []), sections)

    # A paper that files continuously cannot show one edition file and stop.
    # At 00:01 today's edition holds nothing, and yesterday's front page
    # disappears even though the news on it is hours old. So the front page
    # is a rolling window: today's stories first, keeping their placements,
    # then recent ones carried forward beneath them, oldest dropping off by
    # age rather than by the calendar. They carry their own timestamps, so a
    # reader can see what is fresh and what is not.
    carry_hours = cfg["editorial"].get("front_page_carry_hours", 48)
    cutoff = utcnow() - timedelta(hours=carry_hours)
    seen_front = {s["cluster_id"] for s in stories}
    carried = []
    for edition in reversed(editions[:-1]):
        for story in decorate(edition.get("stories", []), sections):
            if story["cluster_id"] in seen_front:
                continue
            try:
                when = datetime.fromisoformat(story.get("published_at") or "")
            except ValueError:
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when < cutoff:
                continue
            seen_front.add(story["cluster_id"])
            # Carried stories never take the lead or a front slot; they fill
            # the rail and the band, where the timestamp does the work.
            story["placement"] = "inside"
            carried.append(story)
    carried.sort(key=lambda s: s.get("published_at") or "", reverse=True)
    stories = stories + carried

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
        "topics": cfg.get("topics", []),
        "site_url": cfg["paper"].get("site_url", "").rstrip("/"),
        # Cache-buster: changes whenever the stylesheet does.
        "css_version": css_version,
    }

    by_placement = lambda kind: [s for s in stories if s.get("placement") == kind]
    lead_list = by_placement("lead")
    lead = lead_list[0] if lead_list else (stories[0] if stories else None)
    front = [s for s in by_placement("front") if s is not lead]
    inside = by_placement("inside")

    # Broadsheet composition: two secondaries under the lead, three down the
    # left column, everything else timestamped in the right-hand rail.
    env.get_template("front.html").stream(
        **base, rel="", stories=stories, lead=lead,
        second=front[:2], left=front[2:5],
        latest=(front[5:] + inside)[:9],
        inside=inside[:8],
    ).dump(str(DIST_DIR / "index.html"))

    # Every edition's stories get a page, not just today's, otherwise the
    # archive links into nothing.
    seen_ids: set[str] = set()
    all_stories = []
    for edition in reversed(editions):
        for story in decorate(edition.get("stories", []), sections):
            if story["cluster_id"] not in seen_ids:
                seen_ids.add(story["cluster_id"])
                all_stories.append(story)

    # One preview card per story, so a shared link carries its own headline
    # rather than the same nameplate every time.
    cards_dir = DIST_DIR / "assets" / "cards"
    # Charts are rendered when the story is written (pipeline/charts_ds.py
    # needs a browser, which the deploy runner does not have) and committed
    # under site/assets/charts/, so here they only need to exist.
    for story in all_stories:
        render_card(story, cards_dir / f"{story['cluster_id']}.png",
                    paper_name=cfg["paper"]["name"])
        if story.get("chart_spec"):
            chart = SITE_DIR / "assets" / "charts" / f"{story['cluster_id']}.png"
            if not chart.exists():
                raise SystemExit(f"{story['cluster_id']}: chart_spec set but {chart} is missing; "
                                 f"run: python -m pipeline.charts_ds story <edition> {story['cluster_id']}")

    for story in all_stories:
        env.get_template("story.html").stream(
            **{**base, "current_section": story.get("section"),
               "page_title": story["headline"],
               "page_description": story.get("standfirst") or cfg["paper"]["tagline"],
               "page_path": f"story/{story['cluster_id']}/",
               "page_type": "article",
               "page_image": f"assets/cards/{story['cluster_id']}.png"},
            rel="../../", story=story,
        ).dump(page("story", story["cluster_id"]))

    for section in sections:
        env.get_template("section.html").stream(
            **{**base, "current_section": section["slug"],
               "page_title": f"{section['name']} · {cfg['paper']['name']}",
               "page_path": f"section/{section['slug']}/"},
            rel="../../", section=section,
            stories=[s for s in stories if s.get("section") == section["slug"]],
        ).dump(page("section", section["slug"]))

    issues = []
    for edition in reversed(editions):
        date = edition["edition_date"]
        issue_stories = decorate(edition.get("stories", []), sections)
        issues.append({"date": date, "date_long": long_date(date), "count": len(issue_stories)})
        issue_front = [s for s in issue_stories if s.get("placement") == "front"]
        issue_inside = [s for s in issue_stories if s.get("placement") == "inside"]
        env.get_template("front.html").stream(
            **{**base, "edition_date_long": long_date(date), "story_count": len(issue_stories)},
            rel="../../", stories=issue_stories,
            lead=next((s for s in issue_stories if s.get("placement") == "lead"), None),
            second=issue_front[:2], left=issue_front[2:5],
            latest=(issue_front[5:] + issue_inside)[:9], inside=issue_inside[:8],
        ).dump(page("issue", date))

    # Games. Three daily puzzles, generated with a uniqueness solver at build
    # time and shipped without their solutions.
    from .puzzles import build_puzzles
    build_puzzles(DIST_DIR / "assets" / "games")
    games = [
        {"slug": "lanterns", "name": "Lanterns", "glyph": "🟦⬜⬜🟦", "kicker": "Light the room",
         "pitch": "Place lanterns so every square is lit and no two lanterns can see each other. Against the clock."},
        {"slug": "camp", "name": "Camp", "glyph": "⬜🟦⬜🟦", "kicker": "Pitch the tents",
         "pitch": "One tent beside every tree. Tents never touch. The margins tell you how many go in each line."},
        {"slug": "nine", "name": "Nine", "glyph": "🟦🟦🟦", "kicker": "Find the words",
         "pitch": "Nine letters, one nine-letter word hiding in them. Find as many words as you can; the nine is the prize."},
    ]
    env.get_template("games/index.html").stream(
        **{**base, "topics": None, "current_section": "games", "page_title": f"Games · {cfg['paper']['name']}",
           "page_description": "One puzzle a day, the same for everyone.", "page_path": "games/"},
        rel="../", games=games,
    ).dump(page("games"))
    for g in games:
        env.get_template(f"games/{g['slug']}.html").stream(
            **{**base, "topics": None, "current_section": "games", "page_title": f"{g['name']} · Games · {cfg['paper']['name']}",
               "page_description": g["pitch"], "page_path": f"games/{g['slug']}/"},
            rel="../../", game_name=g["name"], game_kicker=g["kicker"],
        ).dump(page("games", g["slug"]))

    env.get_template("archive.html").stream(**base, rel="../", issues=issues).dump(
        page("archive")
    )

    site = base["site_url"]
    host = site.replace("https://", "").replace("http://", "")

    # Custom domain for GitHub Pages.
    (DIST_DIR / "CNAME").write_text(host + "\n", encoding="utf-8")

    (DIST_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")

    # Sitemap over every page actually rendered.
    urls = []
    for path in sorted(DIST_DIR.rglob("*.html")):
        rel_path = path.relative_to(DIST_DIR).as_posix()
        if rel_path == "404.html":
            continue
        # /a/b/index.html is served at /a/b/ — publish the clean form.
        clean = "" if rel_path == "index.html" else rel_path.removesuffix("/index.html") + "/"
        loc = f"{site}/" + clean
        urls.append(f"  <url><loc>{loc}</loc></url>")
    (DIST_DIR / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")

    # Atom feed. A newspaper without a feed is not readable by machines.
    def esc(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))
    entries = []
    for story in stories:
        url = f"{site}/story/{story['cluster_id']}/"
        published = story.get("published_at") or utcnow().isoformat()
        entries.append(
            f"  <entry>\n    <id>{url}</id>\n"
            f"    <title>{esc(story['headline'])}</title>\n"
            f'    <link rel="alternate" type="text/html" href="{url}"/>\n'
            f"    <updated>{published}</updated>\n"
            f"    <summary>{esc(story.get('standfirst') or '')}</summary>\n"
            f"    <category term=\"{esc(story.get('section_name') or '')}\"/>\n  </entry>")
    (DIST_DIR / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <id>{site}</id>\n  <title>{esc(cfg['paper']['name'])}</title>\n"
        f"  <subtitle>{esc(cfg['paper']['tagline'])}</subtitle>\n"
        f"  <updated>{utcnow().isoformat()}</updated>\n"
        f'  <link rel="self" href="{site}/feed.xml"/>\n'
        f'  <link rel="alternate" href="{site}"/>\n'
        + "\n".join(entries) + "\n</feed>\n", encoding="utf-8")

    env.get_template("notfound.html").stream(
        **{**base, "page_title": f"Page not found · {cfg['paper']['name']}"}, rel=""
    ).dump(str(DIST_DIR / "404.html"))

    pages = len(list(DIST_DIR.rglob("*.html")))
    print(f"Rendered {pages} pages → {DIST_DIR}")
    print(f"  {host} · sitemap {len(urls)} urls · feed {len(entries)} entries")
    print(f"  front page: {len(stories)} stories, {len(all_sources)} sources, {len(issues)} back issues")


if __name__ == "__main__":
    render_site()
