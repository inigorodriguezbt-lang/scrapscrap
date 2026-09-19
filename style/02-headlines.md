# 02 · Headlines

A headline states what happened. It is not a label, a tease, or a summary of
the topic — it is a sentence with a subject and an active verb.

## The form

**Subject — active verb — object.** Everything else is optional.

```
Nvidia ships Blackwell Ultra to cloud partners
Regulators open inquiry into three AI training datasets
Mistral raises $600 million at a $14 billion valuation
```

## Headlinese: the grammar that differs from prose

News headlines use a compressed grammar. It is a real dialect with real rules,
and getting it wrong is the clearest tell of writing that is not newswriting.

| Rule | Write | Not |
|---|---|---|
| Drop articles | `Regulator opens inquiry` | `The regulator opens an inquiry` |
| Present tense for past events | `Nvidia ships` | `Nvidia shipped` |
| Infinitive for the future | `Meta to open Ohio datacenter` | `Meta will open` |
| Drop the auxiliary in passives | `Three datasets pulled` | `Three datasets were pulled` |
| Comma replaces `and` | `Nvidia ships chips, AMD answers` | `Nvidia ships chips and AMD answers` |
| Numerals always | `4 labs`, `$600 million` | `four labs` |

Only 12% of observed headlines open with `The`, `A`, or `An`. Dropping the
article is the norm, not a stylistic choice.

## Length

Target **8–13 words**, hard ceiling **14**. Observed median is 11; the 90th
percentile is 14. A 17-word headline is not a headline, it is a standfirst that
got promoted.

Under 6 words is usually too thin to carry a claim, unless the news is enormous
and the subject is famous.

## Punctuation

| Mark | Observed | Rule |
|---|---|---|
| Comma | 26% | fine — joins two clauses or sets off attribution |
| Question mark | 10% | **banned here.** Ours is a news paper, not a features desk. A question headline means the reporting did not land |
| Colon | 2% | **banned.** `Topic: what happened` is the single most common artificial-headline pattern |
| Em dash | rare | avoid |
| Exclamation | 0% | never |

The colon ban deserves emphasis. At 2% it is effectively absent from real
headlines, yet it is the default shape of machine-written ones, because it
lets the writer avoid committing to a verb. Commit to the verb.

## Attribution in a headline

When the claim is contested or belongs to one party, say whose it is:

```
Nvidia says Blackwell Ultra triples inference throughput
```

Not `Blackwell Ultra triples inference throughput` — that adopts a vendor's
benchmark as the paper's own finding. The three-word `Nvidia says` prefix is
the difference between reporting and repeating.

## Failure modes

| Broken | Why | Fixed |
|---|---|---|
| `AI Chips: A New Era Begins` | label, colon, no verb, no news | `Nvidia ships Blackwell Ultra to cloud partners` |
| `Is This the End of Training Scale?` | question, no reporting | `Three labs report diminishing returns above 10^26 FLOPs` |
| `Company Announces Major Update` | no subject, no specifics | `Mistral adds 400k context to Large 3` |
| `In a Move That Could Reshape AI…` | editorialising, no event | `Meta licenses Reuters archive for model training` |
| `Revolutionary Model Shatters Benchmarks` | hype, vague, unattributed | `Qwen 4 tops three reasoning benchmarks, Alibaba says` |
