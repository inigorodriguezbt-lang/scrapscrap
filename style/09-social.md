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

## The house template

Every post the paper sends uses one shape, three blocks separated by blank
lines:

```
<headline, exactly as it runs in the paper>

<standfirst, exactly as it runs in the paper>

<link to the story>
```

```
Alibaba's Qwen releases a 7B image model with open weights

Qwen-Image-2.1 generates and edits in one model, takes up to ten reference
images and outputs transparent layers, and ComfyUI and vLLM supported it
within the hour.

https://theaipost.net/story/qwen-image-21/
```

Three reasons it is this and not something else.

**Nothing is rewritten for the post.** The headline and the standfirst have
already passed the checks in `02-headlines.md` and `01-voice.md`. Rewriting
either one for social is how a paper ends up with a post that promises more
than the story delivers.

**The standfirst is already the right second block.** The sampled papers that
use two blocks put the fact in the first and the thing that complicates it in
the second. That is the standfirst's job on the page — it exists to add what
the headline had to leave out — so it needs no adaptation.

**The link stands alone at the end.** It is the last line, on its own, so the
preview card attaches to it and the reader's eye lands on it last.

Where this sits against the sample: it is the Times/Post/Economist "sell"
shape, which ran to a median of 223 characters. The paper uses it for every
story rather than for the lead alone, because every story here has a
standfirst written to that standard.

### The fallback

A story with no standfirst gets the headline and the link, one line each —
the Reuters/FT/Guardian "wire" shape. The same applies if the assembled post
somehow exceeds the platform's 280 characters: it falls back rather than being
cut mid-sentence. Both cases are rare, and `pipeline/social.py` handles them
without asking.

## Rules

- **The link, always.** No exceptions, including threads and quote posts.
- **No hashtag, no emoji**, in any position.
- Under 280 characters including the URL, which the template stays inside so
  long as the headline and standfirst are within their own limits.
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
