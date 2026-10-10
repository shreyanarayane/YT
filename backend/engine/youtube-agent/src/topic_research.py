"""
Finds candidate video topics.

Two signal sources, combined:
1. Google Trends (via pytrends, free, no key) for what's currently rising
   around your niche seed terms.
2. This channel's own historical performance scores (data/performance.json,
   written by analytics_feedback.py) — topics/categories that did well
   before get a boost; ones that flopped get suppressed.

This is the piece that makes the loop "optimize for revenue over attempts":
early runs are mostly Trends-driven (cold start), later runs increasingly
weight your own history.
"""

import json
import os
import random
from pathlib import Path

from pytrends.request import TrendReq

from content_filter import check_topic

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PERF_FILE = DATA_DIR / "performance.json"


def _load_performance() -> dict:
    if PERF_FILE.exists():
        return json.loads(PERF_FILE.read_text())
    return {"topics": {}}  # topic_key -> {"score": float, "attempts": int}


def _trending_candidates(seed_terms: list[str], per_seed: int = 5) -> list[str]:
    try:
        pytrends = TrendReq(hl="en-US", tz=0, timeout=(3, 3))
    except Exception:
        pytrends = None
    candidates = []
    for seed in seed_terms:
        if pytrends:
            try:
                pytrends.build_payload([seed], timeframe="now 7-d")
                related = pytrends.related_queries().get(seed, {})
                rising = related.get("rising")
                if rising is not None:
                    candidates.extend(rising["query"].head(per_seed).tolist())
            except Exception as e:
                print(f"[topic_research] trends lookup failed for '{seed}': {e}")
        candidates.append(seed)  # always keep the raw seed as a fallback
    return list(dict.fromkeys(candidates))  # dedupe, keep order


def _score_candidate(topic: str, perf: dict) -> float:
    key = topic.lower().strip()
    hist = perf["topics"].get(key)
    if hist and hist["attempts"] > 0:
        return hist["score"]
    # Cold start: mild random exploration so untested topics still get a shot
    return 0.5 + random.uniform(-0.1, 0.1)


def get_ranked_topics(seed_terms: list[str], top_n: int = 5, performance: dict | None = None) -> list[dict]:
    # Web requests provide user-scoped Supabase performance.  Retaining the
    # local file only preserves compatibility with the standalone CLI tool.
    perf = {"topics": performance} if performance is not None else _load_performance()
    raw_candidates = _trending_candidates(seed_terms)

    scored = []
    for topic in raw_candidates:
        verdict = check_topic(topic)
        if not verdict["allowed"]:
            continue
        scored.append({
            "topic": topic,
            "score": _score_candidate(topic, perf),
            "needs_review": verdict["needs_review"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


if __name__ == "__main__":
    import yaml
    cfg = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config.yaml"))
    ranked = get_ranked_topics(cfg["channel"]["niche_seed_terms"])
    for r in ranked:
        print(f"{r['score']:.2f}  {r['topic']}" + ("  [review]" if r["needs_review"] else ""))
