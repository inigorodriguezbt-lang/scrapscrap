"""Render a story chart as a static PNG, in the paper's ink-on-white register.

Charts are rare here by policy (style/08-charts.md): a chart must carry a
comparison prose handles badly, on data we cite. Three numbers or fewer stay
in a sentence.

Design decisions, following the house dataviz method:
  - horizontal bars, zero-baselined, because the job is comparing magnitudes
  - one ink colour, so identity is carried by position and direct labels rather
    than by hue, which is colourblind-safe by construction
  - no legend: a single series is named by its panel title
  - recessive rules, no gridlines, no decoration
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = "#121212"
MUTED = "#727272"
RULE = "#d8d8d8"
BAR = "#1c1c1c"

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _f(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def bars(panels: list[dict], source: str, out: Path,
         width: int = 1000, scale: int = 2) -> Path:
    """panels: [{title, rows: [(label, value)], note?}] with values as percents."""
    W = width * scale
    pad = 40 * scale
    label_w = 300 * scale
    row_h = 52 * scale
    panel_gap = 34 * scale

    height = pad * 2 + 26 * scale
    for p in panels:
        height += 34 * scale + len(p["rows"]) * row_h + panel_gap

    img = Image.new("RGB", (W, height), "white")
    d = ImageDraw.Draw(img)

    f_title = _f(SANS_B, 19 * scale)
    f_label = _f(SERIF, 21 * scale)
    f_value = _f(SANS_B, 20 * scale)
    f_note = _f(SANS, 16 * scale)

    bar_x = pad + label_w
    bar_max = W - pad - bar_x - 80 * scale
    y = pad

    for panel in panels:
        d.text((pad, y), panel["title"].upper(), font=f_title, fill=MUTED)
        y += 30 * scale
        d.line([(pad, y), (W - pad, y)], fill=INK, width=2 * scale)
        y += 14 * scale

        for label, value in panel["rows"]:
            cy = y + row_h // 2
            d.text((pad, cy - 13 * scale), label, font=f_label, fill=INK)
            # Zero-baselined, proportional to 100%. Never a truncated axis.
            w = int(bar_max * (value / 100))
            bh = 22 * scale
            d.rounded_rectangle([bar_x, cy - bh // 2, bar_x + w, cy + bh // 2],
                                radius=4 * scale, fill=BAR)
            # Direct label: four bars is few enough to label every one.
            d.text((bar_x + w + 12 * scale, cy - 12 * scale),
                   f"{value:g}%", font=f_value, fill=INK)
            y += row_h

        if panel.get("note"):
            d.text((pad, y), panel["note"], font=f_note, fill=MUTED)
            y += 22 * scale
        y += panel_gap

    d.line([(pad, height - pad - 8 * scale), (W - pad, height - pad - 8 * scale)],
           fill=RULE, width=scale)
    d.text((pad, height - pad + 4 * scale), source, font=f_note, fill=MUTED)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return out
