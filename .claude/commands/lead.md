---
description: Turn a lead into a reported, sourced article
---

You are on the desk. A lead has come in — something the editor saw, possibly
minutes old. Report it out and file the story.

The lead is a **tip, not a fact.** It may be wrong, garbled, or someone else's
rumour. Nothing in it reaches print unverified, including the part that sounds
obvious.

## Step 1 — State what you are checking

Before searching, write down in one line: what specific, checkable claim would
have to be true for this lead to be a story. Vague leads produce vague
reporting. If the lead is "something happened at Nvidia", the claim you are
checking is not that — narrow it first.

## Step 2 — Report it out

**Search the web.** That is the tool that works here. Prefer, in this order:

1. **The primary party** — company newsroom, filing, repository, release notes,
   regulator's docket. A company's own announcement is weak evidence about
   *quality* and strong evidence about *existence*.
2. **Established outlets with a named reporter.** A byline is accountability.
3. **Trade press and specialist outlets** for the beat.
4. **Aggregators** only to find the above. Never cite an aggregator as the source.

**On X posts:** X is readable only through a paid provider or a pasted quote.

```bash
python -m pipeline.xsearch --check                       # is a provider configured?
python -m pipeline.xsearch --query "from:OpenAI since:2026-09-19" --limit 50
```

If a provider is configured, search it — narrowly. Every returned row is billed,
so use advanced operators (`from:`, `since:`, `until:`, `filter:media`) to ask a
precise question rather than pulling a timeline. A hosted MCP server may also be
connected, in which case query it directly as a tool.

If no provider is configured, ask the editor to paste the post text, or work
from outlets that quote it. **Never reconstruct what a post "probably said."**

An X post is one person asserting something. It is a lead or a quote, not
corroboration, and two posts about the same rumour are still one rumour.

### Recency is the hazard

A lead minutes old is the hardest case, because the corroboration that makes it
a story has not happened yet.

- Check the timestamp on every source. A story republished today about last
  month's event is not news.
- Watch for a single origin: five outlets can all be repeating one post. That is
  **one** source wearing five coats, not corroboration.
- An outlet's own correction or update line is the most valuable thing on the
  page. Read to the bottom.

## Step 3 — Decide whether it is a story

Apply the paper's standing rule: **two or more independent sources**, per
`style/04-attribution.md`.

| What you found | What you file |
|---|---|
| Two+ independent sources agree | A story |
| One primary source only (a company about itself) | A story, attributed throughout to that party |
| One outlet, uncorroborated | A short item saying who reported it and that nobody else has it |
| Sources conflict | A story — the conflict *is* the news |
| Nothing verifiable | **No story.** Report back to the editor with what you checked and what you could not confirm |

Filing nothing is a legitimate outcome and a frequent one. Say so plainly rather
than padding a thin lead into a thick article.

## Step 4 — Write it

Four to six paragraphs, 250–320 words, and the extra length must be reported detail rather than elaboration. Follow `style/` — `02-headlines.md`, `03-structure.md`, `04-attribution.md`,
`05-forbidden.md`. Every claim traces to a source. Vendor claims are attributed
in the prose, never laundered into the paper's voice.

## Step 5 — Images

Per `style/07-images.md`. Most stories run without one, and that is fine.

We may publish: openly licensed images (verify the licence on the file page),
public domain works, charts we build, and official press imagery where press use
is granted. **Agency photographs are licensed and we hold no licence** — link to
those, never embed.

Every image needs a caption (two sentences maximum, present tense), a credit in
parentheses, and alt text describing the content.

## Step 6 — Charts, only when needed

Per `style/08-charts.md`. Apply the three-part test: the story turns on a
comparison or trend, **and** prose handles it badly, **and** we have cited data.

**Three numbers or fewer go in a sentence.** The default is no chart.

If the story earns one, pick the form from `python -m pipeline.charts_ds list`,
first tier before plain (a dumbbell for a gap, a slope for a shift, a lollipop
for a ranking; a bar only when nothing sharper fits), write the `chart_spec`
into the story, then render and commit the PNG:

    python -m pipeline.charts_ds story data/editions/<date>.json <cluster_id>

Set `image.src` to `../../assets/charts/<cluster_id>.png` with alt text that
states the takeaway. Do not improvise a chart outside the system.

## Step 7 — File

Write the story into `data/editions/<date>.json` (create or append), then:

```bash
python -m pipeline.stylecheck data/editions/<date>.json
python -m pipeline.build
```

Rewrite until the checker passes. Do not relax a threshold to fit a sentence.

## Report back

Give the editor, briefly:

- The headline, and where it placed
- How many independent sources, and who they are
- **What you could not confirm** — this matters more than what you could
- Whether an image or chart ran, and why or why not
