# 06 · Worked examples

Every example is original to this repository and built on invented facts. Read
them as demonstrations of the rewrite, not as reporting.

---

## Example 1 — A model release

### Draft (machine-typical)

> **Revolutionary New AI Model: A Game-Changer for the Industry**
>
> In a move that could reshape the artificial intelligence landscape, a leading
> AI company has unveiled its groundbreaking new model, which promises to
> deliver unprecedented performance across a wide range of tasks.
>
> The announcement marks a significant milestone for the company and underscores
> the increasingly competitive nature of the AI space. Industry observers have
> noted that the release signals a broader shift toward more capable systems.
>
> As the industry continues to evolve, it remains to be seen how competitors
> will respond. Only time will tell.

**What is wrong:** No company is named. No model is named. No number appears. No
source is cited. Every sentence is compatible with any product release in any
year. Nine banned constructions, a colon headline, and a closing paragraph that
says nothing.

### Rewrite

> **Meridian puts Atlas-3 reasoning model in the API today**
>
> Atlas-3 ships with a 400,000-token context window and, according to one
> reporter, undercuts the company's previous frontier tier on price.
>
> Meridian released Atlas-3 on Tuesday and made it available in its API the same
> day. The company gives the context window as 400,000 tokens and has not
> announced a waitlist or staged rollout.
>
> Reporting from The Ledger adds a detail Meridian did not state: the model is
> priced below the company's previous frontier tier. A separate assessment from
> the researcher Nina Okafor pointed to the evaluation results rather than the
> context window as the more consequential change.
>
> The claims sit in different registers. Availability and context length come
> from Meridian. The pricing position is a reporter's characterisation, and the
> benchmark reading is one researcher's interpretation of results Meridian
> published.

**What changed:** Subject and active verb in the headline, 10 words. A specific
number in the standfirst. Every claim traced to whoever makes it. The final
paragraph does real work — it tells the reader which facts are solid and which
are one party's account.

---

## Example 2 — Attribution laundering

### Draft

> The new accelerator delivers 3.1 times the training throughput of its
> predecessor, making it the fastest chip available for large-scale workloads.

Two vendor claims stated as the paper's own findings. The superlative is
unverifiable — the writer has not tested every chip available.

### Rewrite

> Corvid Systems put the gain at 3.1 times its previous generation on training
> throughput, measured on internal benchmarks it has not published. The company
> described the part as the fastest available for large-scale workloads. No
> independent comparison has been published.

Same information, and now the reader knows exactly how much to trust it.

---

## Example 3 — Ledes that could have been written yesterday

| Broken lede | Diagnosis | Rewrite |
|---|---|---|
| The AI hardware market saw significant developments this week. | No event, no actor, no number. | Corvid began shipping its Kestrel accelerator to cloud partners on Monday. |
| Regulators are increasingly focused on AI training data. | A trend, not news. | The Dutch data authority opened a formal inquiry into three training datasets on Thursday. |
| A major funding round highlights investor appetite for AI startups. | The news is the round; the paper is editorialising instead of reporting it. | Halden AI raised $600 million at a $14 billion valuation, three people briefed on the terms said. |

---

## Example 4 — Handling a conflict

### Draft

> While the company claims shipments have begun, some partners have suggested
> otherwise, creating uncertainty around the timeline.

Vague on both sides. `Some partners` is unattributed, `creating uncertainty` is
the writer's editorial.

### Rewrite

> The accounts differ on timing. Corvid said shipments began Monday. Two cloud
> partners said on Thursday that they had not received units, and a third
> declined to comment.

The disagreement is now specific, sourced, and countable — and the refusal to
comment is reported rather than hidden.

---

## Example 5 — The cuttable third paragraph

### Keep it

> Sampling and shipping describe different stages. Corvid is describing hardware
> reaching partners now. Its competitor is describing parts going out for
> evaluation next quarter.

Resolves an ambiguity the reader would otherwise carry away.

### Cut it

> The competition between the two firms is expected to intensify as demand for
> AI accelerators continues to grow, and the coming months will be critical for
> both companies.

Prediction, no source, true of everything. Delete.

---

## The four-question check

Before a story ships:

1. **Could this lede have been written yesterday?** If yes, there is no news in it.
2. **Who would have to be right for each sentence to be true?** If the answer is
   the company selling the thing, add the source clause.
3. **Does the last paragraph survive deletion?** If yes, delete it.
4. **Does any sentence tell the reader how to feel?** Cut the instruction; keep
   the fact that prompted it.
