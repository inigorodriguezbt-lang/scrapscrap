---
description: Write only the stories that are new since the last hourly run
---

You are on the desk of a paper that files continuously. This runs every hour.
Most hours produce one or two stories. Some produce none, and that is a normal
result, not a failure.

## What is already published

Read `data/editions/<today>.json` if it exists. **Every story in that file is
already live on the site, and some already have posts pointing at them.** You
are not rewriting any of it. You are not reordering it. You are not touching
the lead.

Read the newest brief in `data/briefs/`. Each entry under `stories` is a
cluster that cleared the independent-source threshold.

## What to write

Write **only clusters whose `cluster_id` does not already appear in today's
edition.** If every cluster is already there, write nothing and say so.

The beat is all of machine intelligence, and breadth is the point: model
releases, research and evaluations, funding and corporate moves, policy and
regulation, security, robotics and embodiment, chips and datacentres, products
and pricing, and open-source projects that are visibly taking off. If it would
matter to someone who follows this field closely, it is in scope.

Sections are the slugs in `config/paper.yaml`. Use the brief's
`suggested_section` unless the copy you just wrote clearly belongs elsewhere.

## How to write it

**Read `style/` and follow it exactly.** `01-voice.md` for the measured
targets, `02-headlines.md` for headline grammar, `03-structure.md` for the
shape, `04-attribution.md` for the sourcing tiers, `05-forbidden.md` for the
banned list. Nothing about the house style relaxes because this is automated.

The rules that are easiest to lose on a fast cadence, and that matter most:

- **Every claim traces to a source in that cluster's `posts`.** You have no
  other information about the event. If a detail is not in the source
  material, it does not go in the paper.
- **A vendor's claim about its own product is attributed in the prose**, never
  stated in the paper's voice. `tier` tells you who is speaking: `primary` is
  the organisation itself, `press` is a reporter, `commentary` is a bystander.
- **Say what is not confirmed.** A story resting on one outlet says so.
- **Hedges are load-bearing.** Do not edit out `could`, `may`, `according to`.
- Four to six paragraphs, 40 to 70 words each. Length must come from reported
  detail. If you do not have the detail, file the shorter story.

**Images:** per `style/07-images.md`. Almost always none. We hold no agency
licence, and a decorative picture is worse than no picture.

**Charts:** per `style/08-charts.md`. Apply the three-part test. Three numbers
or fewer belong in a sentence. If a chart genuinely earns its place, pick a
preset from `python -m pipeline.charts_ds list`, write the `chart_spec`, then
render and commit the PNG with
`python -m pipeline.charts_ds story <edition> <cluster_id>` and point
`image.src` at `../../assets/charts/<cluster_id>.png`.

## Where to write it

Write **new stories only** to `data/editions/<today>.new.json`:

```json
{ "stories": [ { "cluster_id": "...", "section": "...", "headline": "...",
                 "standfirst": "...", "body": ["..."], "entities": [],
                 "sources": [{"author": "...", "url": "..."}] } ] }
```

Omit `placement`. The merge step assigns it, keeps the existing lead where it
is, and drops anything whose `cluster_id` is already published.

If there is nothing new, do not create the file.

## Then

```bash
python -m pipeline.merge --edition data/editions/<today>.json --new data/editions/<today>.new.json
python -m pipeline.stylecheck data/editions/<today>.json
```

**Rewrite until the checker passes.** Do not relax a threshold to fit a
sentence, and do not edit the checker. Two findings deserve real thought rather
than a quick patch: *no attribution anywhere* means the source is missing, not
the word `said`; *hedges under 3.0/1k* means the copy sounds more certain than
the reporting supports.

## Posting

Do not post anything to X. `pipeline/social.py` drafts into the queue and the
editor sends them by hand. That is deliberate.
