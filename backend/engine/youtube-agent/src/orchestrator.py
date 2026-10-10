"""
Command-line entry point for the whole pipeline.

  python orchestrator.py --stage build                    # research -> script -> video, then STOP
  python orchestrator.py --stage upload --video-id <id>    # publish the reviewed build
  python orchestrator.py --stage learn --video-id <yt_id> --topic "<topic>"

The 'build' stage never uploads anything by itself — you always have a
chance to open the mp4 and look at it first. That's a deliberate seam, not
a missing feature.
"""

import argparse
import json
import uuid
from pathlib import Path

import yaml

from topic_research import get_ranked_topics
from script_writer import write_script
from tts import synthesize_voiceover
from video_builder import build_video
from youtube_upload import upload_video
from analytics_feedback import update_score

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError("Copy config.example.yaml to config.yaml and fill it in first.")
    return yaml.safe_load(cfg_path.read_text())


def stage_build(cfg: dict):
    ranked = get_ranked_topics(cfg["channel"]["niche_seed_terms"])
    if not ranked:
        print("No candidate topics passed the content filter. Widen your seed terms.")
        return
    top = ranked[0]
    print(f"Chosen topic: {top['topic']}  (score={top['score']:.2f})")
    if top["needs_review"]:
        print("NOTE: flagged for manual review by content_filter — double check before uploading.")

    script_data = write_script(top["topic"])
    print(f"Title: {script_data['title']}")

    video_id_local = uuid.uuid4().hex[:8]
    out_dir = ROOT / cfg["paths"]["output_dir"] / video_id_local
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "meta.json").write_text(json.dumps({
        "topic": top["topic"],
        "title": script_data["title"],
        "description": script_data["description"],
        "script": script_data["script"],
    }, indent=2))

    narration_path = synthesize_voiceover(
        script_data["script"], cfg["video"]["voice"], out_dir / "narration.mp3"
    )

    video_path = build_video(
        topic=top["topic"],
        title=script_data["title"],
        script_text=script_data["script"],
        narration_path=narration_path,
        pexels_api_key=cfg["pexels_api_key"],
        resolution=tuple(cfg["video"]["resolution"]),
        out_path=out_dir / "video.mp4",
    )

    print(f"\nBuilt: {video_path}")
    print(f"Local build id: {video_id_local}")
    print("Watch it, then run:")
    print(f"  python src/orchestrator.py --stage upload --video-id {video_id_local}")


def stage_upload(cfg: dict, local_video_id: str):
    out_dir = ROOT / cfg["paths"]["output_dir"] / local_video_id
    meta = json.loads((out_dir / "meta.json").read_text())

    yt_id = upload_video(
        video_path=out_dir / "video.mp4",
        title=meta["title"],
        description=meta["description"],
        category_id=cfg["upload"]["category_id"],
        privacy_status=cfg["upload"]["default_privacy"],
    )

    meta["youtube_video_id"] = yt_id
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Uploaded as {cfg['upload']['default_privacy']}. Remember to review/publish in Studio.")
    print(f"Once it has some views, run:")
    print(f"  python src/orchestrator.py --stage learn --video-id {local_video_id}")


def stage_learn(cfg: dict, local_video_id: str):
    out_dir = ROOT / cfg["paths"]["output_dir"] / local_video_id
    meta = json.loads((out_dir / "meta.json").read_text())
    if "youtube_video_id" not in meta:
        print("This build hasn't been uploaded yet.")
        return
    update_score(meta["topic"], meta["youtube_video_id"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["build", "upload", "learn"])
    parser.add_argument("--video-id", help="local build id (the 8-char folder name under output/)")
    args = parser.parse_args()

    cfg = load_config()

    if args.stage == "build":
        stage_build(cfg)
    elif args.stage == "upload":
        if not args.video_id:
            raise SystemExit("--video-id required for upload stage")
        stage_upload(cfg, args.video_id)
    elif args.stage == "learn":
        if not args.video_id:
            raise SystemExit("--video-id required for learn stage")
        stage_learn(cfg, args.video_id)
