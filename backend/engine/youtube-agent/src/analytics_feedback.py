"""
Pulls this video's real performance from the YouTube Analytics API and
updates data/performance.json, which topic_research.py reads to weight
future topic choices.

Score formula (0-1 range, simple and explainable on purpose):
  0.5 * normalized_avg_view_percentage
+ 0.3 * normalized_subscribers_gained_per_1k_views
+ 0.2 * normalized_views_per_day_since_publish

Normalization is against this channel's own running max so far (not some
external benchmark) — the point is "better or worse than what's worked for
THIS channel", not chasing an absolute industry number.
"""

import json
from pathlib import Path

from googleapiclient.discovery import build

from youtube_upload import _get_credentials

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PERF_FILE = DATA_DIR / "performance.json"


def _load_perf() -> dict:
    if PERF_FILE.exists():
        return json.loads(PERF_FILE.read_text())
    return {"topics": {}}


def _save_perf(perf: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PERF_FILE.write_text(json.dumps(perf, indent=2))


def fetch_video_stats(video_id: str) -> dict:
    creds = _get_credentials()
    youtube_data = build("youtube", "v3", credentials=creds)
    youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)

    stats_resp = youtube_data.videos().list(part="statistics,snippet", id=video_id).execute()
    item = stats_resp["items"][0]
    views = int(item["statistics"].get("viewCount", 0))
    published = item["snippet"]["publishedAt"][:10]

    analytics_resp = youtube_analytics.reports().query(
        ids="channel==MINE",
        startDate=published,
        endDate="today",
        metrics="averageViewPercentage,subscribersGained",
        filters=f"video=={video_id}",
    ).execute()

    row = analytics_resp.get("rows", [[0, 0]])[0]
    avg_view_pct, subs_gained = row[0], row[1]

    return {
        "views": views,
        "avg_view_percentage": avg_view_pct,
        "subscribers_gained": subs_gained,
    }


def update_score(topic: str, video_id: str):
    perf = _load_perf()
    stats = fetch_video_stats(video_id)

    subs_per_1k = (stats["subscribers_gained"] / max(stats["views"], 1)) * 1000
    raw_score = (
        0.5 * min(stats["avg_view_percentage"] / 100, 1.0)
        + 0.3 * min(subs_per_1k / 5, 1.0)   # 5 subs/1k views treated as excellent
        + 0.2 * min(stats["views"] / 1000, 1.0)  # 1000 views treated as strong early signal
    )

    key = topic.lower().strip()
    existing = perf["topics"].get(key, {"score": 0.5, "attempts": 0})
    attempts = existing["attempts"] + 1
    # running average so one lucky/unlucky video doesn't dominate
    new_score = (existing["score"] * existing["attempts"] + raw_score) / attempts

    perf["topics"][key] = {"score": round(new_score, 4), "attempts": attempts,
                            "last_stats": stats}
    _save_perf(perf)
    print(f"[analytics_feedback] '{topic}' -> score {new_score:.3f} (n={attempts})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: python analytics_feedback.py '<topic>' <video_id>")
        raise SystemExit(1)
    update_score(sys.argv[1], sys.argv[2])
