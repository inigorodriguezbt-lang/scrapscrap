# House Style

How this paper writes. Six documents, each answering one question.

| File | Question it answers |
|---|---|
| `01-voice.md` | What does the paper sound like, in numbers? |
| `02-headlines.md` | How is a headline built? |
| `03-structure.md` | How is a story built? |
| `04-attribution.md` | How do we say how much we know? |
| `05-forbidden.md` | What never appears in the paper? |
| `06-examples.md` | What does the difference look like on the page? |

## How this was derived

The quantitative targets come from measuring 214 headlines and 213 standfirsts
across six sections of a major daily's syndication feeds (world, business,
technology, science, politics, front page). The craft rules come from published
journalism-school and newsroom guidance on news style.

Nothing here is copied from another paper. These are measured properties of
professional news register — sentence lengths, hedge rates, headline grammar —
expressed as rules this paper follows. Style and method carry no copyright; the
prose examples in `06-examples.md` are original to this repository.

## How it is enforced

Prose guidance that lives only in a document gets ignored by the third story of
the day. The measurable rules are therefore also machine-checked:

```bash
python -m pipeline.stylecheck data/editions/2026-09-18.json
```

`/write-edition` runs this before an edition ships. A story that fails does not
get published; it gets rewritten.

Not everything here is checkable. A linter can catch a banned adverb and a
40-word sentence. It cannot catch a lede that buries the news, or an attribution
that launders a vendor claim into fact. Those are in the documents because a
writer has to hold them.
