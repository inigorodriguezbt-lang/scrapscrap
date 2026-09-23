# 10 · Snippets

A snippet is the thing you find while reporting a lead that is worth knowing
but not worth 300 words. It runs in the right-hand rail of the front page, on
`/snippets/`, and in the daily newsletter.

## What qualifies

- **Small product and model news** — a version bump, a price change, an API
  addition, a model reaching a new provider.
- **One-line datapoints** — a benchmark result, a funding figure, a usage
  number, stated with who measured it.
- **Developer and repo finds** — a notable open-source release, a tool, a
  technique that is getting attention.
- **Quotes** — one sourced line from a lab chief, researcher or official that
  stands on its own.

If it needs a second source to be safe, a second paragraph to be clear, or a
caveat to be fair, it is a story, not a snippet. If it is already a story in
today's edition, it is neither.

## The shape

```json
{
  "text": "vLLM shipped version 0.30.0, built from 762 commits by 315 contributors, 104 of them first-timers.",
  "source": { "name": "vLLM", "url": "https://x.com/vllm_project/status/2102593516740411733" },
  "tag": "research",
  "published_at": "2026-09-23T10:18:53+00:00"
}
```

- **`text`** — the fact, 10 to 40 words, one or two sentences. This is all the
  rail shows. Attribute a claim to whoever makes it, as in a story: "Cursor
  says", not the claim bare.
- **`why`** — *not required yet.* For now a snippet is the one line only.
  When the daily newsletter launches, each snippet will also carry one sentence,
  8 to 30 words, on why a reader should care; the archive page already shows it
  where it exists.
- **`source`** — the name and the link. A snippet has no page of its own, so
  the rail links straight to this. Link the primary post or announcement, not a
  repost of it.
- **`tag`** — a section slug from `config/paper.yaml`, optional.
- **`published_at`** — when the news happened, which is the source's
  timestamp, not when you filed it. That is what makes the rail's "3h" true.

The banned lists in `05-forbidden.md` apply. The per-1,000-word rates do not:
at 25 words a single adverb reads as 40 per thousand.

## Filing

Write new snippets to `data/snippets/<today>.new.json` as `{"snippets": [...]}`,
then check and file them:

```bash
python -m pipeline.stylecheck --snippets data/snippets/<today>.new.json
python -m pipeline.snippets add data/snippets/<today>.new.json
```

`add` never rewrites a snippet already filed, and skips any whose source link
has been carried in the last seven days. On the hourly job, the workflow runs
both commands itself; writing the side file is enough.
