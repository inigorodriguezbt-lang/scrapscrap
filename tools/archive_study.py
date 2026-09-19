"""Measure news prose against the public-domain newspaper record.

Source: Chronicling America (Library of Congress) -- digitised US newspapers,
public domain. The API returns whole-page OCR, which mixes news columns with
advertising, classifieds, mastheads and stock tables, so the hard part is not
fetching but separating news prose from everything else on the page.

Nothing from the archive is stored in the repository. Pages are cached under
.cache/ (gitignored) and only aggregate statistics are written out.

Usage:
    python tools/archive_study.py --pages 120 --out style/evidence.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SEARCH = "https://www.loc.gov/collections/chronicling-america/"
UA = "LatentTimes-StyleStudy/1.0 (newspaper register research)"
CACHE = Path(".cache/archive")


def fetch(url: str, timeout: int = 15) -> str:
    key = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".json")
    if key.exists():
        return key.read_text(encoding="utf-8")
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", errors="replace")
    CACHE.mkdir(parents=True, exist_ok=True)
    key.write_text(body, encoding="utf-8")
    return body


# ── harvesting ───────────────────────────────────────────────────────────────

def search_pages(query: str, count: int, start_year: int, end_year: int) -> list[str]:
    """Return resource URLs for pages matching a query in a date range."""
    params = {
        "q": query, "fo": "json", "c": min(count, 100),
        "start_date": f"{start_year}-01-01", "end_date": f"{end_year}-12-31",
    }
    data = json.loads(fetch(SEARCH + "?" + urlencode(params)))
    return [r["id"] for r in data.get("results", []) if r.get("id")]


def page_text(resource_url: str) -> str | None:
    """Pull the OCR full text behind a resource URL."""
    url = resource_url.replace("http://", "https://")
    sep = "&" if "?" in url else "?"
    try:
        meta = json.loads(fetch(f"{url}{sep}fo=json"))
    except Exception:
        return None
    service = meta.get("fulltext_service")
    if not service:
        return None
    try:
        payload = json.loads(fetch(service))
    except Exception:
        return None
    for value in payload.values():
        if isinstance(value, dict) and "full_text" in value:
            return value["full_text"]
    return None


# ── separating news prose from the rest of the page ──────────────────────────

# OCR of this era is noisy and the page is mostly not news. A sentence must
# clear every one of these to be counted.
FUNCTION_WORDS = set("""the of and to in a that for on with as was were is are at by
from he she they it his her their this had has have been will would said not but
an or which who when after before over under about into than them him""".split())

AD_MARKERS = re.compile(
    r"\b(for sale|apply|phone|tel\.|per cent off|bargain|cash only|inquire|"
    r"wanted|rooms? to let|see our|call at|prices?|sale|\$\d+\.\d\d)\b", re.I)


def clean_sentences(raw: str) -> list[str]:
    """Extract sentences that plausibly come from a news column."""
    text = raw.replace("­", "")
    # OCR breaks columns into short lines; rejoin, but keep paragraph breaks.
    text = re.sub(r"-\n(\w)", r"\1", text)          # de-hyphenate line breaks
    text = re.sub(r"\n{2,}", " ¶ ", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s+", " ", text)

    out = []
    for chunk in text.split("¶"):
        for sentence in re.split(r"(?<=[.!?])\s+", chunk):
            s = sentence.strip()
            words = s.split()
            n = len(words)
            if not (8 <= n <= 60):
                continue
            if not s[0].isupper() or not s.endswith((".", "!", "?")):
                continue
            alpha = sum(c.isalpha() or c.isspace() for c in s) / len(s)
            if alpha < 0.88:                      # digits/punctuation soup
                continue
            caps = sum(1 for w in words if w.isupper() and len(w) > 2) / n
            if caps > 0.18:                       # headlines, mastheads, ads
                continue
            lower = {w.strip(".,;:!?'\"").lower() for w in words}
            if len(lower & FUNCTION_WORDS) < 3:   # not running prose
                continue
            if AD_MARKERS.search(s):
                continue
            # OCR garbage: implausible words with no vowels
            bad = sum(1 for w in words if len(w) > 3 and not re.search(r"[aeiouyAEIOUY]", w))
            if bad / n > 0.12:
                continue
            out.append(s)
    return out


# ── measurement ──────────────────────────────────────────────────────────────

PATTERNS = {
    "attribution_said": r"\b(said|says|stated|told|according to)\b",
    "hedges": r"\b(could|may|might|appears?|seems?|expected to|likely|reportedly|alleged\w*)\b",
    "adverbs_ly": r"\b\w{4,}ly\b",
    "intensifiers": r"\b(very|extremely|highly|exceedingly|remarkably)\b",
    "hype": r"\b(unprecedented|revolutionary|sensational|magnificent|epoch.?making|historic)\b",
    "passive": r"\b(was|were|been|being)\s+\w+ed\b",
    "semicolon": r";",
    "em_dash": r"—",
}


def measure(sentences: list[str]) -> dict:
    body = " ".join(sentences)
    words = re.findall(r"[A-Za-z'\-]+", body)
    total = len(words) or 1
    lengths = [len(re.findall(r"[A-Za-z'\-]+", s)) for s in sentences]

    stats = {
        "sentences": len(sentences),
        "words": total,
        "mean_sentence_words": round(st.mean(lengths), 1) if lengths else 0,
        "median_sentence_words": round(st.median(lengths), 1) if lengths else 0,
        "p90_sentence_words": round(st.quantiles(lengths, n=10)[-1], 1) if len(lengths) > 10 else 0,
        "mean_word_chars": round(st.mean([len(w) for w in words]), 2),
        "long_word_share": round(sum(1 for w in words if len(w) > 6) / total, 3),
        "type_token_ratio": round(len(set(w.lower() for w in words)) / total, 3),
    }
    for name, pattern in PATTERNS.items():
        stats[f"{name}_per_1k"] = round(
            len(re.findall(pattern, body, re.I)) / total * 1000, 2)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure the public-domain news record.")
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--out", type=Path, default=Path("style/evidence.json"))
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()

    # Query terms MUST be neutral. An earlier version searched for "said
    # yesterday", "the committee said" and similar, then measured attribution
    # rate on the pages those searches returned -- selecting the corpus by the
    # variable being measured, which inflated `said` sevenfold (21.27 vs 3.08
    # per thousand). Use content words that are not attribution or hedge
    # markers, and keep it that way.
    QUERIES = ["city council", "monday morning", "school board",
               "railroad", "harvest", "county fair"]
    ERAS = [(1900, 1919), (1920, 1939), (1940, 1963)]

    per_era: dict[str, list[str]] = {}
    pages_seen = 0
    per_query = max(4, args.pages // (len(QUERIES) * len(ERAS)))

    for lo, hi in ERAS:
        era = f"{lo}-{hi}"
        sentences: list[str] = []
        for query in QUERIES:
            try:
                urls = search_pages(query, per_query, lo, hi)
            except Exception as exc:
                print(f"  ! search {era} {query!r}: {exc}", file=sys.stderr)
                continue
            for url in urls[:per_query]:
                time.sleep(args.delay)
                raw = page_text(url)
                pages_seen += 1
                if raw:
                    sentences.extend(clean_sentences(raw))
            print(f"  · {era} {query!r}: {len(sentences)} clean sentences so far")
        per_era[era] = sentences
        # Checkpoint: a run cut short still leaves usable statistics rather
        # than nothing, since results were previously only written at the end.
        if sentences:
            partial = {
                "source": "Chronicling America (Library of Congress), public domain",
                "pages_fetched": pages_seen,
                "complete": False,
                "overall": measure([x for v in per_era.values() for x in v]),
                "by_era": {e: measure(v) for e, v in per_era.items() if v},
            }
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(partial, indent=2), encoding="utf-8")
            print(f"  [checkpoint] {era}: {len(sentences)} sentences written")

    all_sentences = [s for v in per_era.values() for s in v]
    if not all_sentences:
        sys.exit("No usable sentences recovered.")

    result = {
        "source": "Chronicling America (Library of Congress), public domain",
        "pages_fetched": pages_seen,
        "complete": True,
        "note": "Whole-page OCR filtered to news-like prose; see clean_sentences().",
        "overall": measure(all_sentences),
        "by_era": {era: measure(s) for era, s in per_era.items() if s},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    o = result["overall"]
    print(f"\n{pages_seen} pages → {o['sentences']} news sentences, {o['words']} words")
    print(f"  mean sentence: {o['mean_sentence_words']} words (median {o['median_sentence_words']})")
    for k in ("attribution_said_per_1k", "hedges_per_1k", "adverbs_ly_per_1k",
              "intensifiers_per_1k", "hype_per_1k", "passive_per_1k", "semicolon_per_1k"):
        print(f"  {k:<28} {o[k]}")
    print(f"\n→ {args.out}")


if __name__ == "__main__":
    main()
