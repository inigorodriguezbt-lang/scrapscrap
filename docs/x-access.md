# Reading X: options, costs, and what I recommend

All prices below were checked against vendor pages, not recalled. Rates change;
re-verify before you spend.

## Why this document exists

X gates timeline reads behind a logged-in session. Unauthenticated reads return
a login wall with no post content, the official API returns 401 without a key,
and Nitter is dead. Tested in this repo — see the session log. So reading X
costs either credentials or money.

## What the official API now costs

There is **no meaningful free tier**. New developers get pay-per-use only:

| | Rate |
|---|---|
| Post read | **$0.005** each |
| User profile read | $0.010 each |
| Monthly read cap | 2M posts |

Legacy Basic ($200/mo) and Pro ($5,000/mo) are closed to new signups and
existing subscribers were migrated to pay-per-use. Enterprise starts around
$42,000/month. At $5 per thousand posts, the official API is priced for
products, not for a newspaper's research.

## Third-party providers

| Provider | Per 1,000 | Notes |
|---|---|---|
| GetXAPI | $0.05 | Cheapest claimed rate; **unverified by me** |
| **Xquik** | **$0.15** | Apify actor + direct platform, **hosted MCP server** |
| twitterapi.io | $0.15 | Comparable, no MCP |
| SocialData | $0.20 | |
| Apify (kaitoeasyapi) | $0.25 | |
| Official X API | $5.00 | 33× Xquik |

## What the design decision costs

The ingestion design matters far more than the provider choice.

| Design | Volume/day | Xquik | Official API |
|---|---|---|---|
| **A** — monitor 248 accounts, 12×/day | 178,560 | $804/mo | $26,784/mo |
| **B** — targeted search per lead + sweeps | 6,000 | **$27/mo** | $900/mo |
| **C** — leads only, no sweeps | 1,500 | **$6.75/mo** | $225/mo |

Moving from a standing source list to per-lead search cuts cost roughly
**30×**. That is the single biggest lever, and it is free to pull.

## Xquik specifically

**Verified:** $0.00015 per delivered tweet on Apify, no start or query fee,
filters and deduplication applied *before* billing. 100% run success across
4,096 users, 1,197 monthly active, 4.55/5. Accepts X advanced search operators
(`from:`, `since:`, `until:`, `filter:media`), tweet IDs in batches, lists, and
date ranges. Direct platform is pay-as-you-go from $10; $10 buys roughly 66,666
tweets, which is about six weeks at Design C.

**The reason to pick it over a cheaper rate:** it publishes a hosted MCP server
at `https://xquik.com/mcp`. That lets Claude Code query X directly as a tool —
no scraper, no `accounts.db`, no CI secret juggling, no code to maintain when X
changes its internals. For this project that is worth more than the $0.10 per
thousand it costs over the cheapest option.

```bash
claude mcp add --transport http xquik https://xquik.com/mcp \
  --header "x-api-key: $XQUIK_API_KEY"
```

## What you should weigh before buying

**Terms of service.** Xquik states plainly that it is not affiliated with X
Corp. Scraping X is against X's terms, and X has pursued scrapers in court. The
exposure sits with you as the buyer, not with the provider. Only you can decide
whether that is acceptable for this project; it is a real consideration, not a
formality.

**Provider concentration.** 1,197 monthly active users is a small business. If
it degrades or shuts down, anything hard-wired to it breaks. `pipeline/xsearch.py`
therefore talks to a provider interface, not to Xquik directly, so switching is
a config change.

**The cheaper option is unverified.** GetXAPI claims $0.05/1,000 — a third of
Xquik. I have not tested it and it has no MCP server. If cost dominates, trial
it; if integration dominates, Xquik wins.

## Recommendation

Start with the **$10 Xquik pay-as-you-go credit** on Design C. It is roughly six
weeks of real use for the price of a sandwich, and the MCP server means the
integration is one command rather than a scraper to maintain.

Keep feeds as the base wire regardless. They are free, they do not breach
anyone's terms, and two outlets independently covering an event is stronger
corroboration than two accounts posting about it. **X is best used to chase a
specific lead, not as the paper's standing source of record.**
