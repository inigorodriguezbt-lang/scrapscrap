"""Discover which X accounts a reference publication actually cites.

HuggingNews does not publish its source list, but it credits the accounts behind
every story on the story page. Crawling its public sitemap and tallying those
credits recovers the working list empirically -- and, unlike a hand-written
list, it is ranked by how often each account actually breaks news.

Only handles are collected. No article text is stored.

Usage:
    python -m pipeline.discover_sources --days 30
    python -m pipeline.discover_sources --days 30 --max-stories 600 --out sources.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

SITE = "https://huggingnews.com"
UA = "LatentTimes-SourceDiscovery/1.0 (+source list research; contact via repo)"

# x.com paths that are not accounts.
NOT_HANDLES = {
    "intent", "i", "search", "hashtag", "home", "share", "compose", "messages",
    "explore", "notifications", "settings", "login", "signup", "privacy", "tos",
    "about", "download", "status",
}

HANDLE_RE = re.compile(r"(?:x|twitter)\.com/([A-Za-z0-9_]{2,15})(?![A-Za-z0-9_])")
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")


CACHE = Path(".cache/discovery")


def fetch(url: str, timeout: int = 25, cache: bool = True) -> str:
    """Fetch a URL, caching story pages so retuning costs the site nothing."""
    key = CACHE / (re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".html")
    if cache and key.exists():
        return key.read_text(encoding="utf-8")

    request = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")

    if cache:
        CACHE.mkdir(parents=True, exist_ok=True)
        key.write_text(body, encoding="utf-8")
    return body


def story_urls(days: int, max_stories: int) -> list[str]:
    """Walk the sitemap index, newest day first, until we have enough stories."""
    index = fetch(f"{SITE}/sitemap.xml", cache=False)
    day_maps = [u for u in LOC_RE.findall(index) if "/stories-" in u]
    day_maps.sort(reverse=True)

    urls: list[str] = []
    for day_map in day_maps[:days]:
        try:
            urls.extend(LOC_RE.findall(fetch(day_map, cache=False)))
        except Exception as exc:
            print(f"  ! {day_map}: {exc}", file=sys.stderr)
        print(f"  · {day_map.rsplit('/', 1)[-1]}: {len(urls)} stories so far")
        if len(urls) >= max_stories:
            break
        time.sleep(0.2)

    return urls[:max_stories]


SECTION_RE = re.compile(r"huggingnews\.com/([a-z-]+)/")


def handles_in(url: str) -> tuple[set[str], str, bool]:
    """Return the handles credited on a story page, plus the story's section."""
    match = SECTION_RE.match(url.replace("https://", ""))
    section = match.group(1) if match else "unknown"
    try:
        html = fetch(url)
    except Exception:
        return set(), section, False
    found = {
        handle for handle in HANDLE_RE.findall(html)
        if handle.lower() not in NOT_HANDLES
    }
    return found, section, True


def crawl(urls: list[str], workers: int, delay: float):
    """Tally handles across story pages, keeping track of which beat cited them.

    An account credited mostly on AI stories belongs in an AI paper; one credited
    mostly on markets stories does not, however often it appears.
    """
    tally: Counter[str] = Counter()
    by_beat: dict[str, Counter] = {}
    ok = 0

    def task(url: str):
        time.sleep(delay)
        return handles_in(url)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (found, section, success) in enumerate(pool.map(task, urls), 1):
            if success:
                ok += 1
                tally.update(found)
                for handle in found:
                    by_beat.setdefault(handle, Counter())[section] += 1
            if i % 50 == 0:
                print(f"  · {i}/{len(urls)} stories · {len(tally)} accounts found")

    return tally, by_beat, ok


# Accounts that speak for a lab, company, or project rather than about one.
# Frequency cannot tell these apart, so the distinction is declared here.
PRIMARY_HINTS = re.compile(
    r"^(openai|anthropicai|googledeepmind|googleai|google|meta|aiatmeta|nvidia|"
    r"nvidiaai|aiatamd|amd|intel|microsoft|msftresearch|huggingface|mistralai|"
    r"deepseek_ai|alibaba_qwen|qwen|cohere|stabilityai|runwayml|midjourney|"
    r"perplexity_ai|xai|grok|apple|awscloud|ibm|salesforce|databricks|"
    r"scale_ai|weights_biases|langchainai|llama_index|ollama|vllm_project|"
    r"pytorch|tensorflow|kaggle|arxiv|allen_ai|eleutherai|epochairesearch|"
    r"reuters|business|cnbc|bloomberg|ft|wsj|techmeme|theinformation|"
    r"googleresearch|googlecloud|azure|openaidevs|anthropic|adept_ai|"
    r"figure_robot|waymo|tesla|spacex|boston_dynamics|lambdaapi|together_ai|"
    r"groqinc|cerebrassystems|graphcoreai|sambanovaai|modular|replicate|"
    r"fireworksai_hq|baseten|modal_labs|nous_research|primeintellect|"
    r"moonshotai|zhipuai|minimax__ai|stepfun_ai|baaibeijing|inclusionai)$",
    re.IGNORECASE,
)


# The sections of the reference site that are actually our beat.
ON_BEAT = {"ai", "tech", "cybersecurity"}

# Below this many citations, an account's beat ratio is sampling noise.
BEAT_EVIDENCE_MIN = 5


def beat_share(beats: Counter) -> float:
    total = sum(beats.values()) or 1
    return sum(count for section, count in beats.items() if section in ON_BEAT) / total


def to_yaml(tally: Counter, by_beat: dict, stories_seen: int, min_mentions: int,
            min_beat_share: float) -> str:
    top = tally.most_common()
    peak = top[0][1] if top else 1

    lines = [
        "# Source list discovered from HuggingNews story credits.",
        f"# Crawled {stories_seen} story pages; {len(tally)} distinct accounts seen.",
        f"# Kept accounts credited at least {min_mentions}x. Regenerate with:",
        "#   python -m pipeline.discover_sources --days 30",
        "sources:",
    ]
    kept = 0
    rejected = []
    for handle, count in top:
        if count < min_mentions:
            continue
        share = beat_share(by_beat.get(handle, Counter()))
        # One or two citations cannot establish a beat; judge only when there
        # is enough evidence to judge on.
        if count >= BEAT_EVIDENCE_MIN and share < min_beat_share:
            rejected.append((handle, count, share))
            continue
        kept += 1
        # Weight tracks how often an account actually appears in a story,
        # compressed so the tail stays meaningful rather than vanishing.
        weight = round(0.8 + 0.9 * (count / peak) ** 0.5, 2)
        tier = "primary" if PRIMARY_HINTS.match(handle) else "commentary"
        lines.append(
            f"  - {{ handle: {handle}, weight: {weight}, tier: {tier} }}"
            f"  # cited {count}x, {share:.0%} on-beat"
        )
    lines.insert(4, f"# {kept} accounts kept; {len(rejected)} dropped as off-beat.")
    if rejected:
        lines.append("")
        lines.append("# Dropped -- credited mostly on markets/politics stories:")
        for handle, count, share in rejected[:40]:
            lines.append(f"#   @{handle} ({count}x, {share:.0%} on-beat)")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover a source list from story credits.")
    parser.add_argument("--days", type=int, default=30, help="day sitemaps to walk")
    parser.add_argument("--max-stories", type=int, default=600)
    parser.add_argument("--workers", type=int, default=4, help="keep this small; be polite")
    parser.add_argument("--delay", type=float, default=0.25, help="seconds before each request")
    parser.add_argument("--min-mentions", type=int, default=2)
    parser.add_argument("--min-beat-share", type=float, default=0.6,
                        help="fraction of an account's citations that must be on-beat")
    parser.add_argument("--out", type=Path, default=Path("config/discovered_sources.yaml"))
    args = parser.parse_args()

    print(f"Collecting story URLs from up to {args.days} days…")
    urls = story_urls(args.days, args.max_stories)
    print(f"\nCrawling {len(urls)} story pages with {args.workers} workers…")

    tally, by_beat, ok = crawl(urls, args.workers, args.delay)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        to_yaml(tally, by_beat, ok, args.min_mentions, args.min_beat_share),
        encoding="utf-8",
    )

    kept = sum(
        1 for h, c in tally.items()
        if c >= args.min_mentions and beat_share(by_beat.get(h, Counter())) >= args.min_beat_share
    )
    print(f"\n{ok} pages read · {len(tally)} accounts seen · {kept} kept → {args.out}")
    for handle, count in tally.most_common(15):
        print(f"  {count:4d}  @{handle}")


if __name__ == "__main__":
    main()
