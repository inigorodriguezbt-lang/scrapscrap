"""Generate a synthetic raw feed so the pipeline can be tested without an X pool.

Contains two genuine multi-source events, one single-source post that must NOT
become a story, and unrelated chatter.
"""
import json, sys
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import RAW_DIR, utcnow

now = utcnow()
def ago(h): return (now - timedelta(hours=h)).isoformat()

POSTS = [
    # EVENT A: a model release, carried by four independent accounts + a shared link.
    ("OpenAI", "primary", 1.6, "Introducing Orion-2, our new frontier reasoning model. Available today in the API with a 400k context window.", 0.5, 9000, 2100, ["https://openai.com/blog/orion-2?utm_source=twitter"]),
    ("karpathy", "commentary", 1.5, "Orion-2 numbers on the reasoning benchmarks are genuinely surprising. The 400k context is the headline but the eval jump is the story.", 0.4, 6200, 900, ["https://openai.com/blog/orion-2"]),
    ("steph_palazzolo", "press", 1.3, "OpenAI has released Orion-2, a reasoning model with a 400k context window, priced below the previous frontier tier.", 0.3, 1800, 420, []),
    ("_akhaliq", "commentary", 1.2, "Orion-2 is out. Frontier reasoning model, 400k context, API available today.", 0.2, 900, 300, ["https://openai.com/blog/orion-2"]),

    # EVENT B: a chips story, carried by three independent accounts.
    ("nvidia", "primary", 1.3, "Blackwell Ultra is now shipping to cloud partners. 2.4x inference throughput over the prior generation on large MoE workloads.", 3.0, 5400, 1500, ["https://nvidia.com/blackwell-ultra"]),
    ("AIatAMD", "primary", 1.1, "Our response to Blackwell Ultra shipping: MI400 sampling begins next quarter with competitive HBM bandwidth.", 2.4, 1200, 260, []),
    ("emilychangtv", "press", 1.0, "Nvidia says Blackwell Ultra is shipping to cloud partners now, claiming 2.4x inference throughput. AMD counters with MI400 sampling.", 2.0, 800, 190, ["https://nvidia.com/blackwell-ultra"]),

    # Single-source post: real-sounding, but nobody corroborates it. Must be dropped.
    ("ylecun", "commentary", 1.3, "A lone thought about energy based models and why autoregressive sampling is a dead end for planning.", 5.0, 4000, 700, []),

    # Unrelated chatter that must not merge into either event.
    ("huggingface", "primary", 1.4, "The community has now uploaded over two million datasets to the Hub. Thank you all.", 8.0, 3000, 600, []),
    ("rowancheung", "commentary", 0.9, "Five AI tools I used this week to save time on video editing.", 9.0, 400, 60, []),
]

RAW_DIR.mkdir(parents=True, exist_ok=True)
out = RAW_DIR / "posts-fixture.jsonl"
with out.open("w", encoding="utf-8") as fh:
    for i, (handle, tier, weight, text, hours, likes, reposts, links) in enumerate(POSTS):
        fh.write(json.dumps({
            "id": str(1000 + i), "handle": handle, "author": handle,
            "weight": weight, "tier": tier, "text": text,
            "created_at": ago(hours), "url": f"https://x.com/{handle}/status/{1000+i}",
            "links": links, "likes": likes, "reposts": reposts, "replies": 0,
            "is_repost": False, "is_reply": False,
        }) + "\n")
print(f"wrote {len(POSTS)} posts -> {out}")
