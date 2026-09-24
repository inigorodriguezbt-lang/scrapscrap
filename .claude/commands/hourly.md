---
description: Write only the stories that are new since the last hourly run
---

You are on the desk of a paper that publishes every two hours. The job is
output: as many good stories and snippets as the last few hours support, for
as few tokens as possible. Every token spent reading something already
published, or re-reading the style guide, is a token not spent writing.

## 1. Read two files, nothing else

- `style/DESK.md` — the whole house style on one page. Do not open the rest
  of `style/` unless the checker flags something you do not understand, or
  you are making a chart or image.
- `data/desk/<today>.json` — the worklist. `python -m pipeline.desk` built it
  from the brief and the finds, already stripped of everything the paper has
  carried and ranked freshest and most interesting first.

Do not read today's edition, the snippet files, the brief or the finds. The
worklist already did that. An item marked `similar_to` names the published
story it resembles; skip it unless it is plainly a new development.

## 2. Decide, then write

Go down the worklist once and sort every item into story, snippet or skip,
per `DESK.md`. Then write. Targets, when the worklist supports them:

- **Stories: 3 to 5.** Releases and launches first.
- **Snippets: 6 to 10.** Every fresh item that is not a story and not a skip.

**Research budget.** Open at most two pages per story (the primary source and
one corroboration) and one per snippet (the thing itself). If a page will not
open, move on to the next item rather than hunting for another route. Stop
researching an item the moment you have what the piece needs.

Stories go to `data/editions/<today>.new.json`:

```json
{ "stories": [ { "cluster_id": "...", "section": "...", "headline": "...",
                 "standfirst": "...", "body": ["..."], "entities": [],
                 "sources": [{"author": "...", "tier": "primary|press|commentary", "url": "..."}] } ] }
```

Use the worklist `id` as the `cluster_id` for a cluster, or a short slug for a
find. Sections are the slugs in `config/paper.yaml`. Omit `placement`; add
`"promote": true` only for the day's real headline.

Snippets go to `data/snippets/<today>.new.json` as `{"snippets": [...]}`.

## 3. Check once, fix once

```bash
python -m pipeline.stylecheck data/editions/<today>.new.json
python -m pipeline.stylecheck --snippets data/snippets/<today>.new.json
```

Check the side files, not the whole edition. Fix only the lines the checker
names, and re-run once. Do not relax a threshold and do not edit the checker.

Then:

```bash
python -m pipeline.merge --edition data/editions/<today>.json --new data/editions/<today>.new.json
python -m pipeline.snippets add data/snippets/<today>.new.json
```

If the merge skips a story as already published and you believe it is a new
development, say so in your reply instead of forcing it through.

## Posting

Do not post anything to X. The editor sends every post by hand. Show only
this run's posts:

```bash
python -m pipeline.social --edition data/editions/<today>.json --pending --this-run
```
