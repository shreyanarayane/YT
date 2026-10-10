"""
Keeps the topic pipeline inside a conservative, brand-safe, non-misleading
lane. This is a first line of defense, not a substitute for you eyeballing
the final script and video before upload.

Design choice: this filter runs on every candidate topic BEFORE any script
gets written, and again on the generated script/title before the video is
built. Fail closed — if unsure, reject.
"""

import re

# Hard blocklist: topics/scripts containing these are rejected outright.
BLOCKED_TERMS = [
    # violence / hate / adult
    "kill", "suicide", "self-harm", "gore", "terroris", "hate speech",
    "nsfw", "nude", "sex tape", "explicit",
    # medical/financial advice framed as fact (liability + misinformation risk)
    "cure cancer", "cures cancer", "guaranteed cure", "guaranteed return",
    "guaranteed profit", "get rich quick", "risk-free investment",
    "doubles your money", "miracle cure",
    # engagement-bait / policy-risk patterns
    "fake giveaway", "clickbait shock", "you won't believe",
    "leaked private", "hacked account", "doxx",
    # misinformation flags
    "flat earth", "faked moon landing", "vaccines cause autism",
]

# Soft flags: not auto-rejected, but logged for your manual review.
REVIEW_TERMS = [
    "diet", "weight loss", "investment", "stock tip", "crypto",
    "political", "election", "religion", "controversial",
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def check_topic(topic: str) -> dict:
    """
    Returns {"allowed": bool, "reason": str, "needs_review": bool}
    """
    norm = _normalize(topic)

    for term in BLOCKED_TERMS:
        if term in norm:
            return {
                "allowed": False,
                "reason": f"matched blocked term: '{term}'",
                "needs_review": False,
            }

    flagged = [t for t in REVIEW_TERMS if t in norm]
    if flagged:
        return {
            "allowed": True,
            "reason": f"passed, but flagged for manual review: {flagged}",
            "needs_review": True,
        }

    return {"allowed": True, "reason": "passed", "needs_review": False}


def check_script(script_text: str) -> dict:
    """Same rules, applied to the full generated script/title before build."""
    return check_topic(script_text)


if __name__ == "__main__":
    tests = [
        "5 productivity hacks that actually work",
        "this crypto guarantees 10x returns risk-free",
        "history's strangest unsolved mysteries",
    ]
    for t in tests:
        print(t, "->", check_topic(t))
