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

## Pending

The house chart design system is supplied separately. Until it lands, the rule
above stands unchanged: **most stories need no chart.** Apply the three-part
test first, and only then reach for the design system.
