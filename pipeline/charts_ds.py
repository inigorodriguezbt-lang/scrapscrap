"""House chart presets, drawn by the design system's own renderer.

The design system (pipeline/ds/, copied verbatim, never edited) ships a
data-driven SVG renderer: give `_chart.js` a JSON block and it computes the
geometry. This module keeps a registry of the forms we run, feeds each one
its JSON in a headless Chromium, and rasterises the result to a PNG in the
system's colours and typefaces. Nothing about how a chart looks is decided
here; that is the system's job.

What is decided here:

  - Which forms we run at all. Pie, donut and dual-axis charts are ruled out
    by style/08-charts.md; the ring, gauge and radial forms encode a single
    number as an area, which readers misjudge, so they are out too.
  - Which forms come first. Every dataset has a plain form (a bar, a line)
    and usually a sharper one that shows the same numbers with the story
    already in the geometry: a dumbbell for a gap, a slope for a shift, a
    waterfall for how a total was built. The plain forms are the fallback,
    not the default, so they sit in the last tier.
  - Where the source line goes. The system has no credit line; the paper
    requires one under every chart, so it is added outside the renderer.

Whether a story gets a chart at all is a separate question, answered by
style/08-charts.md before any of this runs. Most stories should not.

Usage:
    python -m pipeline.charts_ds list
    python -m pipeline.charts_ds gallery OUT_DIR       # every preset's demo
    python -m pipeline.charts_ds render SPEC.json OUT.png
    python -m pipeline.charts_ds story EDITION.json CLUSTER_ID

A story's `chart_spec` looks like:
    {"preset": "dumbbell", "title": "...", "subtitle": "...",
     "data": {...the preset's JSON shape...},
     "source": "Chart: The AI Post. Data: ..."}
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import dataclass
from pathlib import Path

DS_DIR = Path(__file__).resolve().parent / "ds"
SITE_CHARTS = Path(__file__).resolve().parent.parent / "site" / "assets" / "charts"

# Native width of every chart in the system (its SVG viewBox), plus the
# .chart padding from _chart.css. The PNG is rendered at this width times
# the device scale so the SVG is never resampled.
CHART_WIDTH = 640
CHART_PAD = 24


@dataclass(frozen=True)
class Preset:
    name: str          # renderer key in _chart.js TYPES
    tier: int          # 1 = reach for first, 2 = sound, 3 = plain fallback
    job: str           # the question the form answers
    shape: str         # the JSON the renderer expects
    demo: dict         # sample data, used by the self-check and the gallery


_TREND = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]

PRESETS: dict[str, Preset] = {p.name: p for p in [
    # ── Tier 1: the story is in the geometry ─────────────────────────────
    Preset("dumbbell", 1, "a before/after or A/B gap per category; the gap is the story",
           "data:[{label,before,after}], beforeLabel, afterLabel",
           {"beforeLabel": "2025", "afterLabel": "2026",
            "data": [{"label": "Coding", "before": 41, "after": 72}, {"label": "Maths", "before": 38, "after": 66},
                     {"label": "Vision", "before": 55, "after": 61}, {"label": "Agents", "before": 12, "after": 47},
                     {"label": "Long context", "before": 60, "after": 58}]}),
    Preset("slope", 1, "several entities at two points in time; who rose, who fell",
           "data:[{label,left,right}], leftLabel, rightLabel",
           {"leftLabel": "Jan", "rightLabel": "Sep",
            "data": [{"label": "Lab A", "left": 31, "right": 44}, {"label": "Lab B", "left": 28, "right": 22},
                     {"label": "Lab C", "left": 19, "right": 21}, {"label": "Lab D", "left": 12, "right": 8}]}),
    Preset("lollipop", 1, "ranked magnitudes, five to twelve rows; sharper than a bar",
           "data:[{label,value}], format?",
           {"format": "%", "data": [{"label": "Making beds", "value": 67}, {"label": "Folding towels", "value": 62},
                                    {"label": "Loading dishes", "value": 51}, {"label": "Tidying toys", "value": 40},
                                    {"label": "Watering plants", "value": 33}]}),
    Preset("divergingBar", 1, "gains and losses around zero",
           "data:[{label,value}] with signed values, format?",
           {"format": "%", "data": [{"label": "Nvidia", "value": 12}, {"label": "AMD", "value": 7},
                                    {"label": "Intel", "value": -3}, {"label": "Arm", "value": -8},
                                    {"label": "Broadcom", "value": 4}]}),
    Preset("dotPlot", 1, "two measures per category side by side",
           "data:[{label,a,b}], aLabel, bLabel",
           {"aLabel": "Claimed", "bLabel": "Independent",
            "data": [{"label": "SWE-bench", "a": 74, "b": 69}, {"label": "GPQA", "a": 81, "b": 78},
                     {"label": "MMLU", "a": 90, "b": 89}, {"label": "HumanEval", "a": 95, "b": 92},
                     {"label": "ARC", "a": 60, "b": 41}]}),
    Preset("bump", 1, "rank over time",
           "labels:[...], series:[{name,ranks:[...]}]",
           {"labels": ["2023", "2024", "2025", "2026"],
            "series": [{"name": "OpenAI", "ranks": [1, 1, 2, 2]}, {"name": "Anthropic", "ranks": [3, 2, 1, 1]},
                       {"name": "Google", "ranks": [2, 3, 3, 3]}, {"name": "Meta", "ranks": [4, 4, 4, 5]},
                       {"name": "xAI", "ranks": [5, 5, 5, 4]}]}),
    Preset("waterfall", 1, "how a total was built up or eaten away",
           "data:[{label,value,type:start|add|sub|end}], format?",
           {"data": [{"label": "2025", "value": 120, "type": "start"}, {"label": "Cloud", "value": 45, "type": "add"},
                     {"label": "Licences", "value": 18, "type": "add"}, {"label": "Compute", "value": -32, "type": "sub"},
                     {"label": "Staff", "value": -14, "type": "sub"}, {"label": "2026", "value": 137, "type": "end"}]}),
    Preset("rangeBand", 1, "a series with a band of uncertainty around it",
           "labels:[...], values:[{lo,hi,value}], format?",
           {"labels": _TREND, "values": [{"lo": 20, "hi": 30, "value": 25}, {"lo": 24, "hi": 36, "value": 30},
                                         {"lo": 28, "hi": 40, "value": 33}, {"lo": 30, "hi": 46, "value": 38},
                                         {"lo": 36, "hi": 52, "value": 44}, {"lo": 40, "hi": 58, "value": 49},
                                         {"lo": 44, "hi": 66, "value": 55}, {"lo": 50, "hi": 74, "value": 62}]}),
    Preset("forecastCone", 1, "history joined to a projection that widens",
           "labels:[...], history:[...], p10:[...], p50:[...], p90:[...], format?",
           {"labels": ["2022", "2023", "2024", "2025", "2026", "2027", "2028"],
            "history": [10, 14, 21, 30],
            "p10": [None, None, None, 30, 34, 38, 42], "p50": [None, None, None, 30, 40, 52, 66],
            "p90": [None, None, None, 30, 48, 70, 96]}),
    Preset("strip", 1, "every point in each group; a distribution, not an average",
           "groups:[{label,points:[...]}]",
           {"groups": [{"label": "Model A", "points": [61, 63, 64, 66, 67, 67, 68, 70, 72, 75]},
                       {"label": "Model B", "points": [50, 58, 60, 66, 71, 74, 78, 80, 84, 90]},
                       {"label": "Model C", "points": [40, 41, 43, 45, 45, 46, 48, 49, 50, 52]}]}),
    Preset("heatmap", 1, "a matrix of values; where the hot spots are",
           "rows:[...], cols:[...], values:[[...]]",
           {"rows": ["Coding", "Maths", "Writing", "Vision"], "cols": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "values": [[12, 18, 25, 31, 40], [8, 9, 14, 15, 20], [30, 28, 26, 24, 22], [5, 7, 6, 9, 12]]}),
    Preset("calendar", 1, "daily values across a year",
           "values:[[7 per week]...], monthLabels?:[{week,label}]",
           {"values": [[((w * 7 + d) * 7919) % 23 for d in range(7)] for w in range(40)],
            "monthLabels": [{"week": 0, "label": "Jan"}, {"week": 9, "label": "Mar"}, {"week": 18, "label": "May"},
                            {"week": 26, "label": "Jul"}, {"week": 35, "label": "Sep"}]}),
    Preset("sparklineGrid", 1, "many small series, each with its headline number",
           "items:[{label,values:[...],value,change}]",
           {"items": [{"label": "Tokens/day", "values": [3, 4, 4, 5, 7, 8, 11], "value": "11bn", "change": "+37%"},
                      {"label": "Latency", "values": [9, 8, 8, 7, 7, 6, 5], "value": "5s", "change": "-44%"},
                      {"label": "Users", "values": [1, 2, 2, 3, 3, 4, 6], "value": "6m", "change": "+50%"},
                      {"label": "Errors", "values": [2, 3, 2, 4, 3, 2, 1], "value": "1%", "change": "-50%"}]}),
    Preset("deltaBar", 1, "this period against the last, with the change written on it",
           "data:[{label,value,prev}], prevLabel, valueLabel, format?",
           {"prevLabel": "2025", "valueLabel": "2026",
            "data": [{"label": "Nvidia", "value": 46, "prev": 30}, {"label": "TSMC", "value": 32, "prev": 26},
                     {"label": "ASML", "value": 9, "prev": 8}, {"label": "Samsung", "value": 14, "prev": 17},
                     {"label": "SK Hynix", "value": 12, "prev": 7}]}),
    Preset("deltaDot", 1, "signed change by category, size showing magnitude",
           "data:[{label,value}] with signed values, format?",
           {"format": "%", "data": [{"label": "Chips", "value": 18}, {"label": "Cloud", "value": 9},
                                    {"label": "Software", "value": 3}, {"label": "Ads", "value": -4},
                                    {"label": "Devices", "value": -11}, {"label": "Media", "value": -2}]}),
    Preset("tornado", 2, "which input moves the answer most",
           "data:[{label,lo,hi}] ordered widest first; keep labels short, the widest bar's value sits in the label column",
           {"data": [{"label": "Chip price", "lo": -30, "hi": 28}, {"label": "Demand", "lo": -18, "hi": 22},
                     {"label": "Power cost", "lo": -12, "hi": 10}, {"label": "Tariffs", "lo": -9, "hi": 4},
                     {"label": "FX", "lo": -3, "hi": 3}]}),
    Preset("timeline", 1, "milestones in order on a line",
           "events:[{label,date,side?:above|below}]",
           {"events": [{"label": "Filed", "date": "Mar 2024"}, {"label": "Hearing", "date": "Nov 2024", "side": "below"},
                       {"label": "Ruling", "date": "Jun 2025"}, {"label": "Appeal", "date": "Feb 2026", "side": "below"},
                       {"label": "Decision", "date": "Sep 2026"}]}),
    Preset("ranking", 1, "a league table with movement since last time",
           "rows:[{rank,label,value,prev?,highlight?}], format?",
           {"rows": [{"rank": 1, "label": "Claude Opus 5", "value": 1402, "prev": 2, "highlight": True},
                     {"rank": 2, "label": "GPT-5.5", "value": 1398, "prev": 1},
                     {"rank": 3, "label": "Gemini 3 Ultra", "value": 1390, "prev": 3},
                     {"rank": 4, "label": "Grok 5", "value": 1371, "prev": 6},
                     {"rank": 5, "label": "Llama 5", "value": 1355, "prev": 4}]}),
    Preset("sankey", 1, "flows from sources to destinations",
           "nodes:[{id,label,side:left|right,value}], links:[{from,to,value}]",
           {"nodes": [{"id": "vc", "label": "Venture", "side": "left", "value": 60},
                      {"id": "corp", "label": "Corporate", "side": "left", "value": 40},
                      {"id": "chips", "label": "Chips", "side": "right", "value": 45},
                      {"id": "models", "label": "Models", "side": "right", "value": 35},
                      {"id": "apps", "label": "Applications", "side": "right", "value": 20}],
            "links": [{"from": "vc", "to": "models", "value": 30}, {"from": "vc", "to": "apps", "value": 20},
                      {"from": "vc", "to": "chips", "value": 10}, {"from": "corp", "to": "chips", "value": 35},
                      {"from": "corp", "to": "models", "value": 5}]}),
    Preset("treemap", 1, "shares of a whole, more than three parts (never a pie)",
           "data:[{label,value}]",
           {"data": [{"label": "Nvidia", "value": 78}, {"label": "AMD", "value": 9},
                     {"label": "Google TPU", "value": 6}, {"label": "Amazon", "value": 4},
                     {"label": "Other", "value": 3}]}),
    Preset("stream", 1, "how a composition shifts over time",
           "labels:[...], series:[{name,values:[...]}]",
           {"labels": _TREND, "series": [{"name": "Text", "values": [40, 42, 44, 45, 46, 46, 47, 48]},
                                         {"name": "Code", "values": [10, 14, 18, 22, 26, 30, 33, 36]},
                                         {"name": "Image", "values": [8, 9, 10, 12, 13, 14, 16, 18]},
                                         {"name": "Video", "values": [1, 1, 2, 3, 5, 7, 10, 14]}]}),
    Preset("cohort", 1, "retention by cohort over successive periods",
           "rows:[{label,values:[...]}], colHeaders?:[...]",
           {"colHeaders": ["M0", "M1", "M2", "M3", "M4", "M5"],
            "rows": [{"label": "Jan", "values": [100, 62, 48, 41, 38, 36]}, {"label": "Feb", "values": [100, 66, 52, 45, 41]},
                     {"label": "Mar", "values": [100, 70, 55, 49]}, {"label": "Apr", "values": [100, 72, 58]},
                     {"label": "May", "values": [100, 75]}]}),
    Preset("connectedScatter", 1, "two variables traced through time",
           "data:[{label,x,y}] in time order, yFormat?",
           {"data": [{"label": "2020", "x": 10, "y": 5}, {"label": "2021", "x": 14, "y": 8}, {"label": "2022", "x": 22, "y": 9},
                     {"label": "2023", "x": 35, "y": 15}, {"label": "2024", "x": 48, "y": 26}, {"label": "2025", "x": 70, "y": 30},
                     {"label": "2026", "x": 92, "y": 44}]}),


    # ── Tier 2: sound forms for the data they fit ────────────────────────
    Preset("scatter", 3, "relationship between two variables, fifteen or more points",
           "data:[{x,y,label?,highlight?}], xLabel, yLabel, xFormat?, yFormat?; x ticks print raw decimals unless xFormat is '%' or 'x'",
           {"xLabel": "Parameters (bn)", "yLabel": "Score",
            "data": [{"x": x, "y": y, "highlight": x == 70} for x, y in
                     [(1, 30), (3, 38), (7, 45), (8, 44), (13, 52), (20, 55), (34, 58), (40, 61), (52, 60),
                      (65, 64), (70, 72), (80, 66), (110, 70), (140, 71), (180, 74), (240, 76)]]}),
    Preset("bubble", 2, "three variables at once; size is the third",
           "data:[{x,y,r,label}], xFormat?, yFormat?",
           {"data": [{"x": 20, "y": 70, "r": 40, "label": "OpenAI"}, {"x": 35, "y": 60, "r": 30, "label": "Anthropic"},
                     {"x": 50, "y": 50, "r": 60, "label": "Google"}, {"x": 65, "y": 30, "r": 25, "label": "Meta"},
                     {"x": 80, "y": 40, "r": 15, "label": "Mistral"}]}),
    Preset("box", 2, "spread and outliers per group",
           "data:[{label,min,q1,median,q3,max,outliers?}], format?",
           {"data": [{"label": "Model A", "min": 40, "q1": 55, "median": 62, "q3": 70, "max": 84},
                     {"label": "Model B", "min": 30, "q1": 48, "median": 58, "q3": 66, "max": 80, "outliers": [95]},
                     {"label": "Model C", "min": 50, "q1": 60, "median": 66, "q3": 72, "max": 78},
                     {"label": "Model D", "min": 20, "q1": 35, "median": 45, "q3": 60, "max": 75}]}),
    Preset("histogram", 2, "how values are distributed across bins",
           "bins:[{label,value}]",
           {"bins": [{"label": "0–10", "value": 3}, {"label": "10–20", "value": 8}, {"label": "20–30", "value": 15},
                     {"label": "30–40", "value": 22}, {"label": "40–50", "value": 18}, {"label": "50–60", "value": 9},
                     {"label": "60–70", "value": 4}]}),
    Preset("violin", 2, "distribution shape per group",
           "groups:[{label,points:[...]}], format?",
           {"groups": [{"label": "Humans", "points": [50, 55, 58, 60, 62, 62, 63, 65, 68, 70, 72, 80]},
                       {"label": "Model", "points": [30, 45, 60, 61, 62, 62, 63, 64, 66, 70, 85, 90]}]}),
    Preset("stackedHbar", 2, "composition across categories, few parts",
           "categories:[...], series:[{name,values:[...]}]",
           {"categories": ["OpenAI", "Anthropic", "Google", "Meta"],
            "series": [{"name": "Compute", "values": [60, 55, 40, 70]}, {"name": "Staff", "values": [25, 30, 35, 20]},
                       {"name": "Other", "values": [15, 15, 25, 10]}]}),
    Preset("stacked100", 2, "composition as shares, each row summing to 100",
           "categories:[...], series:[{name,values:[...]}]",
           {"categories": ["2023", "2024", "2025", "2026"],
            "series": [{"name": "Cloud", "values": [50, 55, 60, 64]}, {"name": "On-prem", "values": [40, 33, 27, 22]},
                       {"name": "Edge", "values": [10, 12, 13, 14]}]}),
    Preset("errorBars", 2, "estimates with their confidence intervals",
           "data:[{label,value,lo,hi}], format?",
           {"format": "%", "data": [{"label": "Run 1", "value": 56, "lo": 50, "hi": 62}, {"label": "Run 2", "value": 54, "lo": 47, "hi": 61},
                                    {"label": "Run 3", "value": 60, "lo": 55, "hi": 65}, {"label": "Run 4", "value": 49, "lo": 42, "hi": 56},
                                    {"label": "Run 5", "value": 58, "lo": 53, "hi": 63}]}),
    Preset("gantt", 2, "who is doing what, when",
           "rows:[{label,start,end}], timeLabels:[...] one more label than the last end value",
           {"timeLabels": ["Jan", "Apr", "Jul", "Oct", "Dec"],
            "rows": [{"label": "Training", "start": 0, "end": 2}, {"label": "Evals", "start": 1.5, "end": 3},
                     {"label": "Red team", "start": 2.5, "end": 3.5}, {"label": "Launch", "start": 3.5, "end": 4}]}),
    Preset("kpiRow", 2, "three or four hero numbers in a row; not a chart, a strip",
           "items:[{label,value,suffix?,note?}]",
           {"items": [{"label": "Trials", "value": "420"}, {"label": "Completed", "value": "56", "suffix": "%"},
                      {"label": "Homes", "value": "30"}, {"label": "Interventions", "value": "0"}]}),
    Preset("calloutNumber", 2, "one number, very large, when the number is the story",
           "value, unit?, caption?, eyebrowText?, note?",
           {"value": "56", "unit": "%", "caption": "of household tasks completed, 30 unseen homes", "eyebrowText": "Figure Helix 2.5"}),

    # ── Tier 3: plain forms; the fallback when nothing above fits ────────
    Preset("hbar", 3, "categories compared, when a lollipop would be too light",
           "data:[{label,value}], format?",
           {"format": "%", "data": [{"label": "Beds", "value": 67}, {"label": "Towels", "value": 62},
                                    {"label": "Dishes", "value": 51}, {"label": "Toys", "value": 40}, {"label": "Plants", "value": 33}]}),
    Preset("bar", 3, "categories compared, vertical",
           "data:[{label,value}], format?",
           {"data": [{"label": "2022", "value": 12}, {"label": "2023", "value": 21}, {"label": "2024", "value": 35},
                     {"label": "2025", "value": 52}, {"label": "2026", "value": 71}]}),
    Preset("line", 3, "change over time, one or more series, five or more points",
           "labels:[...], series:[{name,values:[...]}] or values:[...], format?",
           {"labels": _TREND, "series": [{"name": "Revenue", "values": [12, 15, 18, 24, 29, 35, 44, 52]},
                                         {"name": "Costs", "values": [10, 12, 15, 19, 22, 27, 31, 36]}]}),
    Preset("area", 3, "a single series over time with its volume shaded",
           "labels:[...], values:[...], format?",
           {"labels": _TREND, "values": [5, 8, 12, 15, 22, 28, 35, 44]}),
    Preset("groupedBar", 3, "two or three series compared per category",
           "categories:[...], series:[{name,values:[...]}], format?",
           {"categories": ["Coding", "Maths", "Writing", "Vision"],
            "series": [{"name": "Model A", "values": [72, 66, 80, 61]}, {"name": "Model B", "values": [65, 70, 74, 68]}]}),
    Preset("step", 3, "a value that changes in jumps, like a price or a policy",
           "labels:[...], values:[...], format?",
           {"labels": _TREND, "values": [10, 10, 15, 15, 15, 20, 20, 30]}),
]}

# Ruled out. The reason is the house rule, not taste.
EXCLUDED: dict[str, str] = {
    "pie": "style/08: pie charts are not run",
    "donut": "style/08: pie charts are not run",
    "multiDonut": "style/08: pie charts are not run",
    "donutMatrix": "style/08: pie charts are not run",
    "polarArea": "style/08: area used to encode a single number",
    "radialBar": "style/08: arc length exaggerates outer rings",
    "gauge": "style/08: area used to encode a single number",
    "ringProgress": "style/08: area used to encode a single number",
    "dualAxis": "style/08: a second y-axis implies a correlation",
    "radar": "readers misjudge polygon area; use dotPlot or groupedBar",
    "funnel": "width encodes nothing; use waterfall or lollipop",
    "pyramid": "width encodes nothing; use lollipop",
    "population": "bin labels are drawn over the bars, black on black; use divergingBar",
}


# ── rendering ────────────────────────────────────────────────────────────────

# The supplied renderer still carries the parent system's lime, rgb(205,240,81),
# hardcoded in three heat ramps (heatmap, cohort, calendar); everything else
# in it uses the newsroom palette, and its own comment describes the ramp as
# ink100 to action blue. The renderer is kept verbatim, so the cells are
# re-tinted after it runs, from the blue tint to action blue, and cell text
# on the dark end goes white for contrast.
RETINT_JS = """
(function () {
  var lo = [234, 242, 254], hi = [22, 109, 252];
  document.querySelectorAll('#chart-host rect[fill^="rgb("]').forEach(function (r) {
    var m = /rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/.exec(r.getAttribute('fill'));
    if (!m) return;
    var t = (255 - (+m[1])) / 50;                 // red channel: 255 - t*(255-205)
    if (t < 0 || t > 1.001) return;
    var c = lo.map(function (a, i) { return Math.round(a + (hi[i] - a) * t); });
    r.setAttribute('fill', 'rgb(' + c.join(',') + ')');
    var n = r.nextElementSibling;
    if (t > 0.55 && n && n.tagName === 'text') n.setAttribute('fill', '#ffffff');
  });
})();
"""

def page_html(spec: dict) -> str:
    """The page the renderer runs in. Assets are the system's own, by path."""
    preset = PRESETS.get(spec["preset"])
    if preset is None:
        why = EXCLUDED.get(spec["preset"])
        raise ValueError(f"chart preset {spec['preset']!r} is "
                         f"{'excluded: ' + why if why else 'not in the registry'}")
    payload = {"type": preset.name, **spec.get("data", {})}
    for key in ("eyebrow", "title", "subtitle"):
        if spec.get(key):
            payload[key] = spec[key]
    source = html.escape(spec.get("source", ""))
    css = (DS_DIR / "colors_and_type.css").as_uri(), (DS_DIR / "charts" / "_chart.css").as_uri()
    js = (DS_DIR / "charts" / "_chart.js").as_uri()
    # The credit line is the paper's requirement, not the system's, so it
    # is styled here from the system's tokens rather than added to its CSS.
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{css[0]}"><link rel="stylesheet" href="{css[1]}">
<style>
#frame {{ width: {CHART_WIDTH + 2 * CHART_PAD}px; background: #fff; }}
#frame .source {{ margin: 0 {CHART_PAD}px; padding: 8px 0 20px; border-top: 1px solid #e0e0e0;
                  font-size: 11px; color: #767676; font-family: Arial, Helvetica, sans-serif; }}
</style></head><body>
<div id="frame"><div class="chart" id="chart-host"></div>{f'<div class="source">{source}</div>' if source else ''}</div>
<script id="chart-data" type="application/json">{json.dumps(payload)}</script>
<script src="{js}"></script>
</body></html>"""


def _chromium() -> str | None:
    """Prefer a preinstalled Chromium over the one Playwright wants to download.

    The web sandbox ships Chromium at a fixed path that rarely matches the
    revision the pip package pins; without this, every render would stop at
    'run playwright install'. None lets Playwright use its own download."""
    import glob
    import os
    candidates = [os.environ.get("CHROMIUM_PATH"), "/opt/pw-browsers/chromium",
                  *sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"), reverse=True)]
    return next((c for c in candidates if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)


def render(spec: dict, out: Path, scale: int = 2) -> Path:
    """Rasterise one chart. Raises if the renderer rejects the JSON."""
    from playwright.sync_api import sync_playwright  # heavy; only needed here

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    page_path = out.with_suffix(".html")
    page_path.write_text(page_html(spec), encoding="utf-8")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"], executable_path=_chromium())
        page = browser.new_page(device_scale_factor=scale, viewport={"width": 900, "height": 900})
        page.goto(page_path.as_uri())
        page.evaluate("document.fonts.ready")
        if not page.evaluate("document.fonts.check('700 18px Carnas')"):
            raise RuntimeError("Carnas did not load; the chart would fall back to Arial Black")
        error = page.evaluate("(document.querySelector('#chart-host div[style]') || {}).textContent || ''")
        if error.startswith("Unknown chart type"):
            raise RuntimeError(error)
        if not page.evaluate("!!document.querySelector('#chart-host svg')"):
            raise RuntimeError(f"{spec['preset']}: renderer produced no SVG")
        page.evaluate(RETINT_JS)
        page.locator("#frame").screenshot(path=str(out), type="png")
        browser.close()
    page_path.unlink()
    return out


def render_story_chart(story: dict, out_dir: Path = SITE_CHARTS) -> Path:
    """Render a story's chart_spec to the committed assets directory."""
    spec = story.get("chart_spec")
    if not spec:
        raise ValueError(f"{story.get('cluster_id')}: no chart_spec")
    return render(spec, Path(out_dir) / f"{story['cluster_id']}.png")


# ── CLI ──────────────────────────────────────────────────────────────────────

def _list() -> None:
    for tier, heading in ((1, "Reach for these first"), (2, "Sound for the data they fit"), (3, "Plain fallback")):
        print(f"\n{heading}")
        for p in PRESETS.values():
            if p.tier == tier:
                print(f"  {p.name:<18} {p.job}\n  {'':<18} {p.shape}")
    print("\nRuled out")
    for name, why in EXCLUDED.items():
        print(f"  {name:<18} {why}")


def _gallery(out_dir: Path) -> None:
    """Render every preset's demo; a failure here means the registry lies."""
    failures = []
    for p in PRESETS.values():
        spec = {"preset": p.name, "eyebrow": f"Preset · {p.name}", "title": p.job[:1].upper() + p.job[1:],
                "subtitle": "Demonstration data", "data": p.demo,
                "source": "Chart: The AI Post. Data: demonstration only"}
        try:
            render(spec, out_dir / f"{p.tier}-{p.name}.png")
            print(f"ok   {p.name}")
        except Exception as e:  # noqa: BLE001 — report every failure, then exit non-zero
            failures.append(p.name)
            print(f"FAIL {p.name}: {e}")
    if failures:
        sys.exit(f"{len(failures)} preset(s) failed: {', '.join(failures)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    g = sub.add_parser("gallery"); g.add_argument("out_dir", type=Path)
    r = sub.add_parser("render"); r.add_argument("spec", type=Path); r.add_argument("out", type=Path)
    s = sub.add_parser("story"); s.add_argument("edition", type=Path); s.add_argument("cluster_id")
    args = ap.parse_args()

    if args.cmd == "list":
        _list()
    elif args.cmd == "gallery":
        _gallery(args.out_dir)
    elif args.cmd == "render":
        print(render(json.loads(args.spec.read_text()), args.out))
    elif args.cmd == "story":
        edition = json.loads(args.edition.read_text())
        story = next((s for s in edition["stories"] if s["cluster_id"] == args.cluster_id), None)
        if story is None:
            sys.exit(f"no story {args.cluster_id!r} in {args.edition}")
        print(render_story_chart(story))


if __name__ == "__main__":
    main()
