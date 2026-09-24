# 11 · The beat: interesting stuff

The paper covers all of machine intelligence, but it is not a trade gazette.
The test for every story, snippet and lead is simple:

> **Would someone who loves this field stop scrolling for it?**

If it is something they can download, try, run, watch, star or argue about,
the answer is usually yes. If it is a consultation closing, a think-tank report
or a funding round for a company nobody has heard of, the answer is usually no.

## Fresh or nothing

The paper publishes every two hours. **A story is about something that
happened in the last twelve hours; a snippet, the last twenty-four.** Measure from the
source's own timestamp (the post, the release, the commit), not from when an
aggregator noticed it. A model that has been trending for three days is not
news today, however many likes it has; if the paper missed it, it missed it.

The one exception is a genuinely new development on an older thing: a result
someone just published, a price that just changed. Then the development is
the story and its timestamp is the one that counts.

### The week after a launch

Community reaction is the second exception, and it exists because the first
rule would otherwise make item 3 under *What we want* unwritable. Nobody builds anything
worth reading about in the six hours after a model ships. The demos, the
head-to-heads and the stunts arrive over the following two or three days, so
measuring them from the launch kills the story before it is ready.

**For what people are doing with a model released in the last seven days, the
clock runs on the reaction, not on the release.** The test is whether the
reaction is still moving: quote traction you have read today, and say when you
read it. Four conditions, all of them:

- the model shipped within the last week,
- the posts you are reporting are from the last 48 hours,
- the traction is current, and you name the number and where it came from,
- no story already published covers the same posts.

That last one is not a formality. This material clusters, so the same demo
reaches the desk three cycles running under three different accounts. Read
the last two editions before writing, and let the merge step's repeat
detection stand when it fires. A second story about the same overnight build
is worse than no story.

Everything else on this beat keeps the six-hour rule.

Every find carries `age_hours`. Start from the top of the list.

## What we want, in order

1. **Model releases.** New frontier models, new open weights, new image,
   video, voice and music models, a big model arriving somewhere new (an API,
   a phone, a laptop). Name the size, the licence, where to get it, and what
   the maker claims it beats.
2. **Things you can try today.** A new app, feature, demo, playground or
   Hugging Face Space. Say where it is and what it does.
3. **What people are doing with a model that just shipped.** The launch is
   item 1; this is the week that follows, and it is usually the better read.
   The demo someone built overnight, the head-to-head somebody ran on their
   own machine, the stunt, the thing the model was not meant to do. Weight
   these as heavily as the release itself: a release is a press cycle, but
   what people build with it is evidence. Name the maker, give the traction,
   and keep every capability claim attached to whoever is making it.
4. **Open-source projects and repos taking off.** A new repo with real
   traction, a tool the community is passing around, a Show HN that people
   are actually using. Traction is the news: say how much (stars, likes,
   downloads, points) and who measured it.
5. **New tech with AI in it.** Robots, humanoids, chips, AI hardware, a new
   technique that changes what is possible, a striking research result with
   code or a demo.
6. **Fun and strange.** A model beating a game, an agent doing something
   unexpected, a jailbreak, a leaderboard upset, a community stunt. Still
   reported, sourced and attributed; fun is not an excuse for sloppy.

## What we run less of

Still in scope, never the default. Run these when they are big, not because
they are there:

- Policy consultations, hearings, bills in committee, ministerial speeches.
- Think-tank reports, surveys and polls.
- Funding rounds, valuations and hires, unless the company is one readers know
  or the number is remarkable.
- Earnings, share prices, trade figures, tariffs.
- Partnerships and "programmes" with no product in them.
- Conference promotions and anything sponsored. Never.

A big policy story (a ban, a court ruling that changes what people can use, a
military incident) is still a big story. The point is the default, not a ban.

## Where to find it

The wire (`python -m pipeline.wire`) is newsrooms and company blogs, and it
skews dull on its own. So each cycle also reads **finds**:

```bash
python -m pipeline.discover        # → data/finds/<today>.json
```

Finds are **tips** from fast newsrooms (HuggingNews, Techmeme,
TestingCatalog), trending models, Spaces and daily papers on Hugging Face, AI
stories on the Hacker News front page, and AI launches on Show HN.

**A tip is a lead, never a source.** Never cite HuggingNews or Techmeme, and
never reuse their wording. (TestingCatalog is different: it reports its own
findings from app strings and live tests, so cite it by name, as a
`commentary`-tier source whose findings are unconfirmed until the company
ships.) A HuggingNews tip lists the X
posts it credits (`credits`): open those, and report from them and from the
primary pages they point at. A Techmeme tip's `url` is the outlet that has the
story: cite that outlet, by name.

Every find has a `signal` (how much traction, measured where) and a link to
the thing itself.

The X sweep adds two discovery queries on top of the account lists, and they
are there to feed items 3 and 4 above:

- posts linking to GitHub or Hugging Face that already have traction, which
  are the repos and models taking off;
- posts in which somebody says they built, made or tested something with a
  model — the launch week's demos and head-to-heads. This query is worded
  around what people say ("I built", "one prompt", "same prompt") rather than
  around model names, which go stale in a fortnight.

The account sweep will bring you the launch. It will not bring you the week
after it, and the week after it is usually the better paper. `sweep_share` in
`config/discover.yaml` sets the split; the discovery queries hold 30 of the
100 posts.

**A find is a pointer, not a source.** Open the link. Report from the model
card, the repo README, the Space, the release notes. The trending number is
the traction; the artifact is the story.

## The single-source rule for public artifacts

The paper's standing rule is two independent sources (`04-attribution.md`).
There is one exception, and it is what makes this beat possible:

**A public artifact can carry a story on its own.** When a lab publishes a
model card, a repo, release notes or a demo, the artifact is itself the
record. You can open it and check it. So a story may rest on one primary
source when:

- the thing is public and you have read it (the card, the README, the page),
- every claim about what it does or beats is attributed to its maker in the
  prose ("Alibaba says", "according to the model card"), and
- the story says plainly that no one else has tested it yet, when that is so.

The brief marks these clusters `"single_source": true`. What the artifact
says about itself is the maker's claim, never the paper's.

## Snippet or story?

- **Story:** a frontier or major open model, something readers will be using
  tomorrow, a repo or demo with exceptional traction, a result that changes
  what people think is possible.
- **Snippet:** a trending model or Space worth knowing about, a version bump,
  a new repo getting attention, a notable paper with code. Most finds end up
  here, and that is the rail doing its job.

## The lead

The lead should be the most interesting thing of the day, not the first thing
filed. When a new story is plainly bigger than the current lead (a new
frontier model, a major open-weights release, the thing everyone in the field
is talking about), mark it `"promote": true` in the side file. The merge step
moves it to the lead and the old lead to the top of the front. That happens at
most three times a day, so use it for the day's real headline, not for every
good story.
