# 08 · Charts

**A chart is a claim, not an ornament.** It costs the reader attention and the
page space, and most news stories should not have one.

## The test

A chart earns its place only when **all three** are true:

1. The story turns on a comparison, a trend, or a distribution.
2. Prose handles it badly — the reader would have to hold more than three
   numbers in their head at once to follow the sentence.
3. We have the underlying data, from a source we cite.

If any one fails, write the sentence instead.

## The three-number rule

Three numbers or fewer belong in a sentence. Always.

> **Chart not needed:** Revenue rose from $2.1bn to $3.4bn.
>
> **Chart not needed:** Three of the five labs reported lower results.
>
> **Chart earns its place:** quarterly revenue across eleven quarters, where
> the shape of the curve is the story.

A two-bar chart is a sentence that took up a column inch. A pie chart with
three slices is a sentence that also made the reader do geometry.

## What the forms are for

| Form | Use for | Do not use for |
|---|---|---|
| Line | change over time, 5+ points | categories |
| Bar | comparing categories | time series with many points |
| Stacked bar | composition, few parts | anything where the middle bands matter |
| Scatter | relationship between two variables | anything with under ~15 points |
| Table | exact values the reader will compare | a trend |

Pie charts are near-useless above three slices, and at three slices a sentence
is better. We do not run them.

## Honesty rules

These are not aesthetic preferences. Breaking them misleads.

- **Bar charts start at zero.** No exceptions. A truncated bar axis exaggerates
  a difference and is the most common way a chart lies.
- A line chart may use a non-zero axis, but the axis must be labelled clearly.
- Never use a second y-axis to imply two series are correlated.
- Never use area or volume to encode a single number — humans read areas badly.
- Label the data source under every chart, in the same form as a photo credit:
  `(Chart: The Latent Times. Data: company filings)`.
- If the data is a company's own unaudited figure, the source line says so.

## When the data is one party's

A chart built from a vendor's own benchmark is a vendor's claim rendered in our
typeface, and it borrows our authority for their number. Either attribute it in
the chart's own title — `Nvidia's reported throughput gain` — or do not draw it.

## Accessibility

- Never encode meaning in colour alone; use position, label or pattern too.
- Charts carry alt text stating the takeaway, not the chart type:
  `Revenue grew each quarter from 2024, with the steepest rise in Q3 2026`.
- Contrast must hold in both light and dark rendering of the page.

## The house chart system

The charts are drawn by the newsroom design system (`pipeline/ds/`, kept
verbatim) through `pipeline/charts_ds.py`, which holds the presets we run.
`python -m pipeline.charts_ds list` prints them in three tiers.

**Reach for the first tier before the plain forms.** A bar chart shows the
numbers; a dumbbell, a slope or a waterfall shows what the numbers did. When
the data has the shape for a sharper form, the plain bar or line is the wrong
choice, not the safe one.

| The data is | Reach for | Not |
|---|---|---|
| a gap per category, before/after or A/B | dumbbell, dotPlot | grouped bar |
| several things at two points in time | slope | two bars each |
| ranked magnitudes, 5–12 rows | lollipop | horizontal bar |
| gains and losses around zero | divergingBar, deltaDot | bar with negatives |
| rank over time | bump | multi-line |
| how a total was built or eaten | waterfall | stacked bar |
| a series with uncertainty | rangeBand, forecastCone | line |
| every point in each group | strip, box, violin | bar of averages |
| a matrix | heatmap, cohort | table |
| shares of a whole | treemap, stacked100 | pie (never) |
| flows | sankey | anything else |

Pie, donut, gauge, ring, radial and dual-axis forms are not in the registry
and the style check refuses them.

**The three-part test still comes first.** A sharp form is no reason to run a
chart the story does not need; most stories need none.

A story that runs a chart carries a `chart_spec` (preset, title, subtitle,
data in the preset's shape, source line). Render it when the story is written:

    python -m pipeline.charts_ds story data/editions/<date>.json <cluster_id>

The PNG lands in `site/assets/charts/` and is committed with the story; the
deploy runner has no browser and only checks that it is there.
