"""Render a link-preview card for each story.

A shared story used to show the same generic nameplate whatever it was, which
wastes the largest element of the post. Each story now gets its own card
carrying its headline, so the reader sees what they are being offered before
they click.

1200x630 is the size X, Slack and iMessage crop to.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
MARGIN = 72
INK = "#121212"
MUTED = "#727272"
RULE = "#c7c7c7"

NAMEPLATE = Path("site/assets/fonts/oldlondon.ttf")
SERIF_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


def _fit(draw, text, font_path, start, max_width, max_lines):
    """Shrink until the headline fits the box in at most max_lines."""
    size = start
    while size > 28:
        font = _font(font_path, size)
        # Roughly how many characters fit on a line at this size.
        avg = draw.textlength("n", font=font) or size * 0.5
        wrapped = textwrap.wrap(text, width=max(12, int(max_width / avg)))
        if len(wrapped) <= max_lines:
            widest = max((draw.textlength(l, font=font) for l in wrapped), default=0)
            if widest <= max_width:
                return font, wrapped
        size -= 4
    return _font(font_path, size), textwrap.wrap(text, width=30)[:max_lines]


def render(story: dict, out: Path, paper_name: str = "The AI Post") -> Path:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Nameplate, small, top left.
    name_font = _font(NAMEPLATE, 52)
    d.text((MARGIN, MARGIN - 8), paper_name, font=name_font, fill=INK)
    rule_y = MARGIN + 66
    d.line([(MARGIN, rule_y), (W - MARGIN, rule_y)], fill=INK, width=2)

    # Section kicker.
    kicker = (story.get("section_name") or "").upper()
    if story.get("entities"):
        kicker = f"{kicker} · {' · '.join(story['entities']).upper()}"
    if kicker:
        d.text((MARGIN, rule_y + 22), kicker[:58], font=_font(SANS, 19), fill=MUTED)

    # Headline: the reason the card exists.
    font, lines = _fit(d, story["headline"], SERIF_BOLD, 66, W - MARGIN * 2, 4)
    y = rule_y + 68
    for line in lines:
        d.text((MARGIN, y), line, font=font, fill=INK)
        y += font.size + 10

    # Footer rule and source count.
    foot = H - MARGIN - 26
    d.line([(MARGIN, foot - 18), (W - MARGIN, foot - 18)], fill=RULE, width=1)
    n = len(story.get("sources") or [])
    if n:
        d.text((MARGIN, foot), f"{n} {'source' if n == 1 else 'sources'}",
               font=_font(SANS, 19), fill=MUTED)
    d.text((W - MARGIN - 152, foot), "theaipost.net", font=_font(SANS, 19), fill=MUTED)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return out
