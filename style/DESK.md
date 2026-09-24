# The desk card

Everything a cycle needs, on one page. The full style guide (`01`–`11`) is
the reference behind it; open a file there only when the checker flags
something you do not understand, or for a chart or image. The checker
enforces every measurable rule, so write, run it, and fix what it names.

## What runs

Interesting stuff, fresh. Lead with: model releases; things people can try
today; open-source repos and community projects taking off; AI hardware and
robots; the fun and strange. Policy, funding, earnings and partnerships run
only when they are big. Never conference promos or sponsored content.

A story is about something from the last **6 hours**, a snippet the last
**12**, by the source's own timestamp.

## Story or snippet

- **Story:** a release, launch or result people will talk about, with enough
  in the source for four paragraphs. Two independent sources, or one public
  artifact you opened (model card, repo, release notes), attributed.
- **Snippet:** everything else that is fresh and worth knowing. One sentence.
  If it needs a caveat to be fair, it is a story or nothing.
- **Nothing:** anything flagged `similar_to` unless it is plainly a new
  development; anything you cannot open and check.

## Sourcing

- Every claim traces to a source you opened this cycle. Nothing from memory.
- A company's claim about its own product is attributed in the prose ("Meta
  says"), never stated as fact.
- Say what is not confirmed. Keep hedges (`could`, `may`, `according to`).
- Never cite HuggingNews or Techmeme; cite the outlet or post they point at.
  TestingCatalog may be cited as unconfirmed.

## The story, in shape

- **Headline:** 8–13 words. Subject, active verb, object. Present tense for
  past events, numerals, no leading article, no colon, no question.
  `Nvidia ships Blackwell Ultra to cloud partners`
- **Standfirst:** 18–32 words, at most two sentences, no semicolon.
- **Body:** 4–6 paragraphs of 35–75 words. Sentences under 22 words on
  average, none over 38. First paragraph is the news; the second says who
  says so and how they know; the last says what is not known.
- **Banned:** hype words, AI tells ("delve", "landscape"),
  editorial verbs ("unveiled", "slammed"), intensifiers, rule-of-three lists,
  semicolons in body copy. The checker lists them when you trip one.
- A lead-worthy release gets `"promote": true`. At most three a day.

## The snippet, in shape

One sentence, 10–40 words, saying what happened and who says so, with the
source's name and a link to the thing itself. `published_at` is the source's
timestamp. For a find, name the traction and who measured it.

```json
{"text": "Alibaba released Qwen-Image-2.1, a 7B open-weights image model, which is the second most trending model on Hugging Face.",
 "source": {"name": "Qwen", "url": "https://huggingface.co/Qwen/Qwen-Image-2.1"},
 "published_at": "2026-09-23T10:18:53+00:00"}
```
