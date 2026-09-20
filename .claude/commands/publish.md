---
description: Review the queued edition and its posts, then publish what the editor approves
---

Nothing in this command may go out without the editor saying so, in this
conversation, for these specific items. Publishing a story to the web and
posting it to X are both public and effectively irreversible.

## 1 — Show what is waiting

Read `data/queue/<date>.json` and the matching `data/editions/<date>.json`.

For each story, show the editor, in plain terms:

- The **headline** and **standfirst**
- The **number of independent sources**, and who they are
- **What could not be confirmed**
- The **drafted post**, exactly as it would appear, with its character count and
  whether it uses the house template or the wire fallback
- Any validation problems

Then verify before asking:

```bash
python -m pipeline.stylecheck data/editions/<date>.json
python -m pipeline.social --edition data/editions/<date>.json --check
```

If either reports an error, say so and **do not offer to publish** until it is
fixed. A story that fails the checks is not ready for the editor's time.

## 2 — Ask

Ask which items to publish. Accept: all of them, a named subset, or none.

**Wait for an answer.** Do not infer approval from enthusiasm about the story,
from an earlier "looks good", or from a reply about something else. Silence is
not consent. If the editor asks for a change, make it, re-run the checks, and
ask again.

A story may be approved for the site but not for X. Treat those as two
separate permissions and ask for both.

## 3 — Publish the site

Only for approved stories.

```bash
python -m pipeline.build
```

Commit and push to `claude/keen-cerf-tu0nb3`. The site is the record; it goes
out first, because a post must never point at a story that is not live yet.

Confirm the story URL resolves before posting anything.

## 4 — Post to X

Only for posts the editor approved for X, and only after the story is live.

Through the Xquik connector, `POST /api/v1/x/tweets`. Write actions need the
paper's X account connected to Xquik — a read API key alone will not post. If
that is not set up, say so plainly and stop; do not improvise another route.

Post the approved text **exactly as approved**. Do not re-edit it on the way
out, not even to fix a comma. What the editor read is what goes out.

One post per story. No threads.

## 5 — Record it

Update the queue file: set each item's `status` to `published`, `skipped` or
`rejected`, and record the post URL for anything that went out. Commit that too,
so the queue is an accurate log of what the paper has said.

## If a post is wrong after it goes out

Tell the editor at once. Post a correction; do not delete quietly. The paper's
standing rule is that a correction is more valuable than a clean timeline.
