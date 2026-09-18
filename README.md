# The Latent Times

A daily paper covering machine intelligence, assembled from public posts on X.

Built in the fashion of [HuggingNews](https://huggingnews.com): watch a curated
set of accounts, wait for several independent sources to converge on the same
event, then write it up. The difference is the newsroom — Claude Code writes the
copy, and the result is laid out as a broadsheet rather than a card feed.

```
scrape ──▶ cluster ──▶ /write-edition ──▶ build ──▶ dist/
 (X)       (events)      (Claude)        (HTML)   (Pages)
```

## The editorial rule

One account posting loudly is not news. The pipeline only declares a story once
**two or more independent accounts** touch the same event inside a 24-hour
window — `editorial.min_independent_sources` in `config/paper.yaml`. That single
setting is what separates this from a firehose, and it is the first thing to
tune if the paper feels too thin or too noisy.

Every story carries its sources on the page. If a claim cannot be traced back to
a post, it does not run.

## Quick start

```bash
pip install -r requirements.txt

# See the whole thing work on synthetic data, no X account needed:
python tests/make_fixture.py
python -m pipeline.cluster --raw data/raw/posts-fixture.jsonl
python -m pipeline.build
python -m http.server -d dist 8000     # → http://localhost:8000
```

That renders the sample edition in `data/editions/`. To write a real one, run
`/write-edition` inside Claude Code after the cluster step.

## Wiring the scraper

Ingestion uses [twscrape](https://github.com/vladkens/twscrape), which needs a
pool of logged-in X accounts. Set it up once:

```bash
twscrape add_accounts accounts.txt username:password:email:email_password
twscrape login_accounts
```

**Use throwaway accounts.** An `auth_token` is a full account session, not a
scoped read-only key, and scraping can get an account suspended. `accounts.db`
is gitignored; never commit it.

The scraper reads whichever accounts are listed under `sources:` in
`config/paper.yaml`, with a `weight` that biases ranking and a `tier` that tells
the writer whether a source is the company itself (`primary`), a reporter
(`press`), or a bystander (`commentary`). That distinction matters — it's how
the copy avoids laundering a vendor claim into fact.

## Where the source list came from

The seed list in `config/paper.yaml` is hand-written. The bulk of the list was
recovered empirically:

```bash
python -m pipeline.discover_sources --days 45
```

HuggingNews does not publish which accounts it monitors, but it credits the
accounts behind every story on the story page. This crawls its public sitemap
(`robots.txt` is `Allow: /`), tallies those credits, and writes
`config/discovered_sources.yaml` ranked by how often each account is actually
cited. Only handles are stored -- no article text. Pages are cached under
`.cache/`, so retuning costs the site nothing.

**This recovers ~236 accounts, not the ~1,200 HuggingNews says it monitors.** A
story page credits only the accounts that contributed to *that* story, so the
crawl sees the active subset -- accounts that actually produced news in the
window -- and never the silent remainder of the pool. The published archive also
only goes back about three weeks. Re-run it periodically and the list grows.

`source_list: merged` in `config/paper.yaml` unions the two. Curated entries win
on conflict: a crawl can count citations, but it cannot tell whether an account
speaks for a lab or merely about one.

## The pipeline

| Stage | Command | Output |
|---|---|---|
| Collect | `python -m pipeline.scrape --hours 24` | `data/raw/posts-*.jsonl` |
| Cluster | `python -m pipeline.cluster` | `data/briefs/<date>.json` |
| Write | `/write-edition` in Claude Code | `data/editions/<date>.json` |
| Render | `python -m pipeline.build` | `dist/` |

### How clustering works

Posts are compared by IDF-weighted token cosine, with two lifts that matter in
practice:

- **A shared outbound link** is near-proof of the same event.
- **A shared rare token** — `orion-2`, `blackwell` — is how news events are
  actually identified. Two rare tokens in common is strong evidence.

Candidates are also scored against each cluster's **centroid**, not just its
closest member. This is what catches a press rewrite: a reporter restating an
announcement in different words often fails a pairwise comparison against any
single post while matching the group's theme clearly.

Ranking weights corroboration far above engagement, deliberately. A story
carried by five accounts outranks one loud post with big numbers.

## Publishing

`.github/workflows/edition.yml` runs the whole loop every two hours and deploys
to GitHub Pages. Two repository secrets:

- `CLAUDE_CODE_OAUTH_TOKEN` — from `claude setup-token`
- `TWSCRAPE_ACCOUNTS_DB` — `base64 -w0 accounts.db`

Enable Pages with source **GitHub Actions**.

## Making it your own paper

Everything editorial lives in `config/paper.yaml`: masthead, tagline, source
list, sections, tracked entities, and the thresholds. Point `sources:` at a
different beat and the rest of the pipeline follows without code changes.

The house style lives in `.claude/commands/write-edition.md` — headline form,
paragraph length, attribution rules, and a banned-vocabulary list. Edit that
file to change how the paper sounds.

The design is in `site/style.css` and `site/templates/`, built from generic
broadsheet conventions — column rules, a folio line, a drop cap on the lead —
using free fonts. Nothing is borrowed from any particular newspaper.

## Caveats worth knowing

- X caps a user timeline at roughly 3,200 posts. Fine for a daily, a hard wall
  for backfill; use dated search queries if you need history.
- twscrape hits undocumented endpoints. Breakage after an X change is routine.
- Clustering thresholds are tuned against the fixture, not against months of
  live data. Expect to adjust `cluster_threshold` once you see real volume.
