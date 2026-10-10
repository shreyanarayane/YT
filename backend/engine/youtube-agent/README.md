# YouTube Auto-Creator Agent

A semi-automatic pipeline that researches topics, writes a script, generates a
narrated short video, lets **you approve it**, uploads it to YouTube, and then
reads back real performance to pick smarter topics next time.

Cost: $0 required. Everything below uses free tiers / free tools. One optional
upgrade (LLM scriptwriting) costs pennies per video if you choose to enable it.

## What it actually does (read this first)

- It does **not** guarantee income. YouTube monetization (ad revenue) only
  kicks in after you pass the YouTube Partner Program thresholds — currently
  1,000 subscribers + either 4,000 public watch hours in 12 months, or 10M
  Shorts views in 90 days. Nothing here can skip that.
- It is **semi-automatic by your choice**: the agent builds a complete video
  and *stops*. You watch it and run one command to actually publish. This is
  also the safer choice for the channel itself — YouTube's spam/"inauthentic
  content" policies specifically target fully-unattended AI upload bots.
- "Decent topics" is enforced by `src/content_filter.py` — a keyword/category
  blocklist (no medical/financial-advice claims, no hate/violence/adult
  content, no copyrighted material, no misleading titles). Tune it to your
  values; it's intentionally conservative by default.
- The feedback loop only has *your channel's own* data to learn from, so it
  needs several videos and a couple of weeks of watch-time data before its
  topic-ranking becomes meaningfully better than a coin flip.

## Pipeline stages

```
src/topic_research.py     -> pulls trending queries (Google Trends, free)
src/content_filter.py     -> drops anything not "decent"/brand-safe
src/script_writer.py      -> turns a topic into a ~45-60s narration script
src/tts.py                -> free TTS narration (edge-tts, no API key)
src/video_builder.py      -> stock B-roll (Pexels free tier) + captions + audio
src/youtube_upload.py     -> uploads as PRIVATE draft for your review
src/analytics_feedback.py -> pulls views/watch-time/subs gained, updates scores
src/orchestrator.py       -> runs the whole thing end to end
```

## One-time setup

1. `pip install -r requirements.txt`
2. Get a **free** Pexels API key: https://www.pexels.com/api/ (for stock video clips)
3. Create a YouTube Data API v3 OAuth client (free, Google Cloud Console →
   enable "YouTube Data API v3" + "YouTube Analytics API" → OAuth client ID,
   type "Desktop app") → download as `client_secret.json` into the project root.
4. Copy `config.example.yaml` → `config.yaml` and fill in your niche, channel
   name, and the Pexels key.
5. (Optional, not free but ~$0.01–0.05/script) Set `ANTHROPIC_API_KEY` as an
   env var to get much better scripts via Claude instead of the built-in
   template writer. Pipeline works without it.

## Running it

```bash
# 1. Research + filter + write a script + build the video, then STOP for you to check
python src/orchestrator.py --stage build

# -> review output/<video_id>/video.mp4 yourself

# 2. When happy, upload as a private draft on your channel
python src/orchestrator.py --stage upload --video-id <video_id>

# 3. A few days later, pull analytics and feed the scores back
python src/orchestrator.py --stage learn
```

Run stage 3 on a schedule (cron / Task Scheduler / GitHub Actions) daily or
weekly — that's what actually makes topic selection improve over time.

## Realistic next steps once this works

- Once you're comfortable with quality, you can change `--stage upload` to
  publish as public/scheduled instead of private, but keep a human glance at
  each video first — it protects the channel and your name is on it.
- Track your true costs (Pexels stays free under its limits; TTS is free;
  the only variable cost is optional LLM scripting) against watch-time growth
  before assuming this is net-positive time-wise.
