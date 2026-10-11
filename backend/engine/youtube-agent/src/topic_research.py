"""
Finds candidate video topics.

Two signal sources, combined:
1. Google Trends (via pytrends, free, no key) for what's currently rising
   around your niche seed terms.
2. This channel's own historical performance scores — previously successful
    topics get a boost when the exact candidate has a recorded score.

Previously covered topics are excluded, and clearly labeled evergreen angles
keep discovery useful when Google Trends is unavailable or exhausted.
"""

import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

from pytrends.request import TrendReq

from content_filter import check_topic

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PERF_FILE = DATA_DIR / "performance.json"


def _load_performance() -> dict:
    if PERF_FILE.exists():
        return json.loads(PERF_FILE.read_text())
    return {"topics": {}}  # topic_key -> {"score": float, "attempts": int}


def _trending_candidates(seed_terms: list[str], per_seed: int = 8) -> list[tuple[str, str]]:
    try:
        pytrends = TrendReq(hl="en-US", tz=0, timeout=(3, 3))
    except Exception:
        pytrends = None
    candidates: list[tuple[str, str]] = []
    for seed in seed_terms:
        if pytrends:
            try:
                pytrends.build_payload([seed], timeframe="now 7-d")
                related = pytrends.related_queries().get(seed, {})
                rising = related.get("rising")
                seed_candidates = []
                if rising is not None:
                    seed_candidates.extend((str(topic), "Google Trends · rising") for topic in rising["query"].head(per_seed).tolist())
                if not seed_candidates:
                    top = related.get("top")
                    if top is not None:
                        seed_candidates.extend((str(topic), "Google Trends · related") for topic in top["query"].head(per_seed).tolist())
                seed_key = _normalize_topic(seed)
                candidates.extend((topic, source) for topic, source in seed_candidates if _normalize_topic(topic) != seed_key)
            except Exception as e:
                print(f"[topic_research] trends lookup failed for '{seed}': {e}")
    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for topic, source in candidates:
        key = _normalize_topic(topic)
        if key and key not in seen:
            seen.add(key)
            unique.append((topic.strip(), source))
    return unique


def _normalize_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", topic.lower())).strip()


def _is_covered(candidate: str, covered_topics: list[str]) -> bool:
    candidate_key = _normalize_topic(candidate)
    candidate_words = set(candidate_key.split())
    for covered in covered_topics:
        covered_key = _normalize_topic(covered)
        if not candidate_key or not covered_key:
            continue
        if candidate_key == covered_key or SequenceMatcher(None, candidate_key, covered_key).ratio() >= 0.88:
            return True
        covered_words = set(covered_key.split())
        overlap = len(candidate_words & covered_words) / max(1, len(candidate_words | covered_words))
        if len(candidate_words) > 1 and len(covered_words) > 1 and overlap >= 0.8:
            return True
    return False


def _fallback_candidates(seed_terms: list[str]) -> list[tuple[str, str]]:
    """Relevant, clearly non-trending ideas when Google Trends is unavailable."""
    ideas = []
    for seed in seed_terms:
        ideas.extend([
            (f"What changed recently in {seed}", "Niche idea · not live trend data"),
            (f"{seed}: beginner mistakes and what to do instead", "Niche idea · not live trend data"),
            (f"{seed} explained with a real-world example", "Niche idea · not live trend data"),
            (f"{seed} vs. the alternatives: which fits different needs?", "Niche idea · not live trend data"),
            (f"The most common myths about {seed}", "Niche idea · not live trend data"),
        ])
    return ideas


def _score_candidate(topic: str, perf: dict) -> float:
    key = topic.lower().strip()
    hist = perf["topics"].get(key)
    if hist and hist["attempts"] > 0:
        return hist["score"]
    return 0.5


def get_ranked_topics(
    seed_terms: list[str],
    top_n: int = 5,
    performance: dict | None = None,
    exclude_topics: list[str] | None = None,
) -> list[dict]:
    # Web requests provide user-scoped Supabase performance.  Retaining the
    # local file only preserves compatibility with the standalone CLI tool.
    perf = {"topics": performance} if performance is not None else _load_performance()
    raw_candidates = _trending_candidates(seed_terms)
    # Always keep a relevant fallback pool: live queries may be exhausted by
    # coverage filtering or Google Trends may return too few usable results.
    raw_candidates.extend(_fallback_candidates(seed_terms))

    scored = []
    for topic, source in raw_candidates:
        if is_topic_covered(topic, exclude_topics or []):
            continue
        verdict = check_topic(topic)
        if not verdict["allowed"]:
            continue
        scored.append({
            "topic": topic,
            "score": _score_candidate(topic, perf),
            "needs_review": verdict["needs_review"],
            "source": source,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def is_topic_covered(candidate: str, covered_topics: list[str]) -> bool:
    return _is_covered(candidate, covered_topics)


if __name__ == "__main__":
    import yaml
    cfg = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config.yaml"))
    ranked = get_ranked_topics(cfg["channel"]["niche_seed_terms"])
    for r in ranked:
        print(f"{r['score']:.2f}  {r['topic']}" + ("  [review]" if r["needs_review"] else ""))
