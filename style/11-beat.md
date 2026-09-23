# 11 · The beat: interesting stuff

The paper covers all of machine intelligence, but it is not a trade gazette.
The test for every story, snippet and lead is simple:

> **Would someone who loves this field stop scrolling for it?**

If it is something they can download, try, run, watch, star or argue about,
the answer is usually yes. If it is a consultation closing, a think-tank report
or a funding round for a company nobody has heard of, the answer is usually no.

## What we want, in order

1. **Model releases.** New frontier models, new open weights, new image,
   video, voice and music models, a big model arriving somewhere new (an API,
   a phone, a laptop). Name the size, the licence, where to get it, and what
   the maker claims it beats.
2. **Things you can try today.** A new app, feature, demo, playground or
   Hugging Face Space. Say where it is and what it does.
3. **Open-source projects and repos taking off.** A new repo with real
   traction, a tool the community is passing around, a Show HN that people
   are actually using. Traction is the news: say how much (stars, likes,
   downloads, points) and who measured it.
4. **New tech with AI in it.** Robots, humanoids, chips, AI hardware, a new
   technique that changes what is possible, a striking research result with
   code or a demo.
5. **Fun and strange.** A model beating a game, an agent doing something
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

Finds are trending models, Spaces and daily papers on Hugging Face, AI stories
on the Hacker News front page, and AI launches on Show HN. Each has a `signal`
(how much traction, measured where) and a link to the artifact itself. The X
sweep adds posts linking to GitHub and Hugging Face that already have traction.

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
