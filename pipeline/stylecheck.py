"""Check written copy against the house style in style/.

Prose rules that live only in a document get ignored by the third story of the
day. These are the mechanically checkable ones, with thresholds taken from the
measured targets in style/01-voice.md.

Usage:
    python -m pipeline.stylecheck data/editions/2026-09-18.json
    python -m pipeline.stylecheck --text "A headline to check"
    python -m pipeline.stylecheck data/editions/2026-09-18.json --strict

Exit status is non-zero when any error-level finding is present, so this can
gate publication.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── thresholds (see style/01-voice.md) ───────────────────────────────────────

HEADLINE_WORDS = (6, 14)
STANDFIRST_WORDS = (18, 32)
PARAGRAPH_WORDS = (35, 75)
MAX_SENTENCE_WORDS = 38
MAX_MEAN_SENTENCE_WORDS = 22.0
MAX_ADVERB_RATE = 14.0        # per 1,000 words
MAX_PASSIVE_RATE = 8.0
MIN_HEDGE_RATE = 3.0          # hedging is load-bearing; too little is a fault

HYPE = r"""unprecedented|revolutionary|game.?chang\w+|groundbreaking|landmark|
seismic|historic|monumental|transformative|disruptive|cutting.?edge|
state.?of.?the.?art|next.?generation|breakthrough"""

INTENSIFIERS = r"""very|extremely|incredibly|remarkably|highly|significantly|
substantially|dramatically|massively"""

EDITORIAL_VERBS = r"""slammed|blasted|touted|boasted|admitted|revealed|unveiled|
shattered|dominated|crushed"""

VAGUE = r"""the landscape|the space(?!\s*shuttle)|the ecosystem|the arena|
offerings|solutions provider|leverage(?:s|d)?\s|robust|seamless"""

AI_TELLS = r"""in a move that|underscores the|it'?s worth noting|
as the industry continues|marks a significant milestone|signals a broader shift|
raises important questions|delve into|dive deep into|a testament to|
remains to be seen|only time will tell|^meanwhile,|^furthermore,|^moreover,|
^additionally,|continues to evolve|in today'?s|it is important to note"""

HEDGES = (r"\b(could|may|might|appears?|seems?|expected to|likely|according to|"
          r"reportedly|apparently|potentially|claims?|claimed|suggests?|estimated|"
          r"describes? (?:it |the \w+ )?as|characteris(?:ed|ation)|its own)\b")
ADVERBS = r"\b\w{4,}ly\b"
PASSIVE = r"\b(was|were|been|being|is|are)\s+\w+ed\b"
ATTRIBUTION = (r"\b(said|says|according to|told|confirmed|declined to comment|"
               r"reported|reporting|describes?|described|wrote|writes|cited|"
               r"citing|stated|put the \w+ at|pointed to)\b")


def clean(pattern: str) -> re.Pattern:
    return re.compile(re.sub(r"\s*\n\s*", "", pattern), re.IGNORECASE | re.MULTILINE)


RX = {
    "hype": clean(HYPE), "intensifier": clean(INTENSIFIERS),
    "editorial_verb": clean(EDITORIAL_VERBS), "vague": clean(VAGUE),
    "ai_tell": clean(AI_TELLS),
}


# ── helpers ──────────────────────────────────────────────────────────────────

def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z'\-]+", text)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def rate(pattern: str | re.Pattern, text: str) -> float:
    """Matches per 1,000 words."""
    total = len(words(text)) or 1
    rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, re.I)
    return len(rx.findall(text)) / total * 1000


@dataclass
class Report:
    label: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


def flag_banned(text: str, report: Report, where: str) -> None:
    for name, rx in RX.items():
        for hit in {m.group(0).strip().lower() for m in rx.finditer(text)}:
            report.error(f"{where}: banned {name.replace('_', ' ')} — \"{hit}\"")


# ── the checks ───────────────────────────────────────────────────────────────

def check_headline(headline: str, report: Report) -> None:
    n = len(words(headline))
    low, high = HEADLINE_WORDS
    if n < low:
        report.error(f"headline: {n} words, under {low}")
    elif n > high:
        report.error(f"headline: {n} words, over {high}")

    if ":" in headline:
        report.error("headline: contains a colon (observed in 2% of real headlines)")
    if "?" in headline:
        report.error("headline: is a question")
    if "!" in headline:
        report.error("headline: contains an exclamation mark")
    if len(headline) > 80:
        report.warn(f"headline: {len(headline)} characters, over 80")
    if re.match(r"^(The|A|An)\s", headline):
        report.warn("headline: opens with an article; headlinese usually drops it")
    if not re.search(r"\b[a-z]{2,}\b", headline):
        report.warn("headline: no lowercase word, check it is a sentence not a label")

    flag_banned(headline, report, "headline")


def check_standfirst(standfirst: str, report: Report) -> None:
    if not standfirst.strip():
        report.warn("standfirst: missing")
        return
    n = len(words(standfirst))
    low, high = STANDFIRST_WORDS
    if n < low:
        report.warn(f"standfirst: {n} words, under {low}")
    elif n > high:
        report.error(f"standfirst: {n} words, over {high}")
    if len(sentences(standfirst)) > 2:
        report.error("standfirst: more than two sentences")
    if ";" in standfirst:
        report.error("standfirst: semicolon (absent from the standfirst corpus)")
    flag_banned(standfirst, report, "standfirst")


def check_body(body: list[str], report: Report) -> None:
    if not body:
        report.error("body: empty")
        return
    if len(body) > 4:
        report.warn(f"body: {len(body)} paragraphs, house length is 2-3")

    joined = " ".join(body)

    for i, para in enumerate(body, 1):
        n = len(words(para))
        low, high = PARAGRAPH_WORDS
        if n > high:
            report.error(f"paragraph {i}: {n} words, over {high}")
        elif n < low:
            report.warn(f"paragraph {i}: {n} words, under {low}")

        for sentence in sentences(para):
            sn = len(words(sentence))
            if sn > MAX_SENTENCE_WORDS:
                report.error(f"paragraph {i}: {sn}-word sentence, over {MAX_SENTENCE_WORDS}")

        if ";" in para:
            # Not an error: body prose in the archive carries semicolons at
            # 1.7/1k. Rare enough to flag, common enough not to block.
            report.warn(f"paragraph {i}: semicolon (rare in news body copy)")

        flag_banned(para, report, f"paragraph {i}")

    all_sentences = sentences(joined)
    if all_sentences:
        mean = sum(len(words(s)) for s in all_sentences) / len(all_sentences)
        if mean > MAX_MEAN_SENTENCE_WORDS:
            report.error(f"body: mean sentence {mean:.1f} words, over {MAX_MEAN_SENTENCE_WORDS}")

    adverbs = rate(ADVERBS, joined)
    if adverbs > MAX_ADVERB_RATE:
        report.warn(f"body: -ly adverbs {adverbs:.1f}/1k, over {MAX_ADVERB_RATE}")

    passive = rate(PASSIVE, joined)
    if passive > MAX_PASSIVE_RATE:
        report.warn(f"body: passive {passive:.1f}/1k, over {MAX_PASSIVE_RATE}")

    # The counterintuitive one: too FEW hedges means claims are being stated
    # with more confidence than the sourcing supports.
    hedges = rate(HEDGES, joined)
    if hedges < MIN_HEDGE_RATE:
        report.warn(
            f"body: hedges {hedges:.1f}/1k, under {MIN_HEDGE_RATE} — "
            "check that vendor claims are not stated as fact"
        )

    if not re.search(ATTRIBUTION, joined, re.I):
        report.error("body: no attribution anywhere (no 'said', 'according to', ...)")

    # A tricolon is a rhetorical reflex rather than reporting.
    for hit in re.findall(r"\b\w+, \w+,? and \w+\b", joined):
        if len(words(hit)) <= 5:
            report.warn(f"body: rule-of-three construction — \"{hit}\"")


def check_story(story: dict, index: int) -> Report:
    headline = story.get("headline", "")
    label = f"[{index}] {headline[:58] or '(no headline)'}"
    report = Report(label)
    check_headline(headline, report)
    check_standfirst(story.get("standfirst", ""), report)
    check_body(story.get("body", []) or [], report)
    if not story.get("sources"):
        report.error("sources: none listed")
    return report


# ── entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Check copy against house style.")
    parser.add_argument("edition", nargs="?", type=Path, help="edition JSON to check")
    parser.add_argument("--text", help="check a single headline or passage instead")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    reports: list[Report] = []

    if args.text:
        report = Report("--text")
        if len(sentences(args.text)) == 1 and len(words(args.text)) <= 16:
            check_headline(args.text, report)
        else:
            check_body([args.text], report)
        reports.append(report)
    elif args.edition:
        edition = json.loads(args.edition.read_text(encoding="utf-8"))
        stories = edition.get("stories", [])
        if not stories:
            print("No stories in edition.")
            sys.exit(1)
        reports = [check_story(s, i) for i, s in enumerate(stories, 1)]
    else:
        parser.error("give an edition file or --text")

    errors = warnings = 0
    for report in reports:
        errors += len(report.errors)
        warnings += len(report.warnings)
        if report.errors or report.warnings:
            print(f"\n{report.label}")
            for msg in report.errors:
                print(f"  ERROR  {msg}")
            for msg in report.warnings:
                print(f"  warn   {msg}")
        else:
            print(f"\n{report.label}\n  clean")

    checked = len(reports)
    print(f"\n{'─' * 58}")
    print(f"{checked} checked · {errors} errors · {warnings} warnings")

    if errors or (args.strict and warnings):
        print("FAILED house style. Rewrite before publishing.")
        sys.exit(1)
    print("Passes house style.")


if __name__ == "__main__":
    main()
