# 09 · The paper's X account

Measured from 72 posts across six newspapers — the Times, the Post, Reuters,
the FT, the Economist and the Guardian — sampled the week this was written.

## What every paper does

| Feature | Observed |
|---|---|
| Carries a link to the story | **72 of 72 — 100%** |
| Hashtag | **0%** |
| Emoji | **0%** |
| Median length | 146 characters |

Three findings, and they are not close calls.

**The link is the point.** Not one post in the sample omitted it. A newspaper's
X account exists to move readers to the story; a post without a link is a
newspaper giving away the only thing it sells. **Never post a story without its
URL.**

**No hashtags. No emoji.** Zero out of 72, across six papers with different
audiences and different countries. This is not a stylistic preference, it is
the register. A hashtag on a news post reads as marketing.

**Short.** Median 146 characters, roughly half the limit. The restraint is the
signal: a paper that has the story does not need to work for the click.

## The two house styles

The sample splits cleanly.

### Wire — Reuters, the FT, the Guardian · median 108 characters

The headline, then the link. Nothing else. One line.

```
Corvid ships Kestrel accelerator to cloud partners
https://theaipost.com/story/kestrel
```

No verb changes, no teaser. The headline already did the work, and it was
written to be read cold.

### Sell — the Times, the Post, the Economist · median 223 characters

The story restated for someone scrolling, often in two blocks separated by a
blank line: the fact, then the turn.

```
Figure rented 30 homes in the Bay Area and sent in a humanoid with no
training for any of them.

It finished 56% of the chores.

https://theaipost.com/story/helix25
```

The second block is doing the work — it carries the number, the qualification,
or the thing that complicates the first block. It is not a restatement.

## Which one we use

**Default to wire.** Headline, newline, link. It is honest, it is fast, and it
cannot overpromise, because the headline has already passed the checks in
`02-headlines.md`.

**Use sell for the lead story only**, at most a few times a day. The second
block must add a fact the headline left out — a number, a caveat, a conflict.
If it only rephrases, use wire instead.

## Rules

- **The link, always.** No exceptions, including threads and quote posts.
- **No hashtag, no emoji**, in any position.
- Under 200 characters including the URL. Wire posts should be well under.
- Never a claim the story does not support. The post is the paper speaking, and
  it carries the same attribution rules as the copy — `04-attribution.md`
  applies in full. A vendor's benchmark is attributed here too.
- No question-mark posts, no "you won't believe", no "thread 🧵", no counting
  down, no "this is huge".
- A label suffix is acceptable where a paper needs it — ` | analysis` — but the
  paper has no opinion section yet, so it should not appear.
- If a story is corrected after posting, post the correction. Do not delete
  quietly.

## Breaking

A prefix is legitimate for genuinely breaking news, as the Times uses one. It
must be rare enough to mean something.

```
Breaking: Regulator opens inquiry into three AI training datasets
https://theaipost.com/story/dpa-inquiry
```

Reserve it for a story confirmed in the last hour that the reader would want
interrupting. If everything is breaking, nothing is.

## Nothing posts without review

Every post is drafted alongside the story, held in the queue, and goes out only
after the editor approves it. See `.claude/commands/publish.md`.
