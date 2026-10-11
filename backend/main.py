import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yaml

# Ensure project paths are in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ENGINE_DIR = BACKEND_DIR / "engine" / "youtube-agent"
SRC_DIR = ENGINE_DIR / "src"
OUTPUT_DIR = ENGINE_DIR / "output"
DATA_DIR = ENGINE_DIR / "data"
CONFIG_PATH = ENGINE_DIR / "config.yaml"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth import require_current_user, require_admin
from backend.supabase_store import AuthenticatedUser, SupabaseConfigurationError, store
from backend.billing import (
    BillingConfigurationError,
    create_subscription,
    verify_webhook_signature,
)

# Import youtube-agent modules safely with fallbacks
try:
    from topic_research import get_ranked_topics, is_topic_covered
except ImportError:
    def get_ranked_topics(seed_terms, top_n=5, performance=None, exclude_topics=None):
        candidates = [
            f"{seed}: beginner mistakes and what to do instead"
            for seed in seed_terms
        ] + [
            f"{seed} explained with a real-world example"
            for seed in seed_terms
        ]
        return [
            {"topic": topic, "score": 0.5, "needs_review": False, "source": "Niche idea · not live trend data"}
            for topic in candidates
            if not is_topic_covered(topic, exclude_topics or [])
        ][:top_n]
    def is_topic_covered(candidate, covered_topics):
        return candidate.strip().casefold() in {topic.strip().casefold() for topic in covered_topics}

try:
    from script_writer import write_script
except ImportError:
    def write_script(topic):
        return {
            "title": f"The Truth About {topic.title()}",
            "script": f"Did you know about {topic}? Here is what most people get wrong. First, it is not what it seems. Second, the details change everything. Follow for more!",
            "description": f"A short breakdown of {topic}.",
            "needs_review": False,
        }

try:
    from content_filter import check_topic, check_script
except ImportError:
    def check_topic(topic):
        return {"allowed": True, "needs_review": False, "reason": "OK"}
    def check_script(text):
        return {"allowed": True, "needs_review": False, "reason": "OK"}

try:
    from tts import synthesize_voiceover
except ImportError as e:
    print(f"[WARNING] Failed to import tts module: {e}")
    print("[WARNING] Using dummy audio - video generation will not work properly")
    def synthesize_voiceover(text, voice, out_path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("dummy audio")
        return out_path

try:
    from video_builder import build_video
except ImportError as e:
    print(f"[WARNING] Failed to import video_builder module: {e}")
    print("[WARNING] Video generation is unavailable until the import error is fixed")
    def build_video(**kwargs):
        raise RuntimeError("video_builder could not be imported")

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        example_path = ENGINE_DIR / "config.example.yaml"
        if example_path.exists():
            return yaml.safe_load(example_path.read_text())
        return {
            "channel": {"name": "advpipe", "niche_seed_terms": ["personal finance tips", "science facts"]},
            "pexels_api_key": "",
            "video": {"target_seconds": 50, "resolution": [1080, 1920], "voice": "en-US-GuyNeural"},
            "upload": {"default_privacy": "private", "category_id": "27"},
            "paths": {"data_dir": "data", "output_dir": "output"},
        }
    return yaml.safe_load(CONFIG_PATH.read_text())


def save_config(cfg: dict):
    CONFIG_PATH.write_text(yaml.dump(cfg, default_flow_style=False))


app = FastAPI(
    title="AI YouTube Content Manager & Studio API",
    description="Supabase-backed content management API with video pipeline orchestration.",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOW_ORIGINS",
            "" if os.environ.get("APP_ENV", "development").lower() == "production" else "*",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static video output directory for streaming previews
app.mount("/static/videos", StaticFiles(directory=str(OUTPUT_DIR), check_dir=False), name="static_videos")


# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class PlanCreateRequest(BaseModel):
    code: str
    name: str
    price_paise: int
    razorpay_plan_id: Optional[str] = None
    videos_per_month: int = 0
    max_duration_seconds: int = 60
    scheduled_posts_per_month: int = 0
    is_active: bool = True


class SubscriptionStartRequest(BaseModel):
    plan_code: str


class ScheduleVideoRequest(BaseModel):
    scheduled_for: datetime
    timezone: str = "Asia/Kolkata"
    privacy_status: str = "private"


class CustomTopicRequest(BaseModel):
    topic: str


class SeedTermsRequest(BaseModel):
    seeds: List[str]


class ScriptGenRequest(BaseModel):
    topic: str
    duration_seconds: int = 60


class ScriptSaveRequest(BaseModel):
    topic: str
    title: str
    description: str
    script: str
    voice: Optional[str] = "en-US-GuyNeural"


class VideoBuildRequest(BaseModel):
    topic: str
    title: str
    description: str
    script: str
    voice: Optional[str] = "en-US-GuyNeural"
    fast_mode: Optional[bool] = False
    duration_seconds: Optional[int] = None


class VideoUploadRequest(BaseModel):
    privacy_status: Optional[str] = "private"


class FeedbackRequest(BaseModel):
    topic: str
    score: float
    attempts: Optional[int] = 1
    views: Optional[int] = 100
    subscribers_gained: Optional[int] = 2


# -------------------------------------------------------------
# Base & Health Routes
# -------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI YouTube Content Manager Backend",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": store.database_status(),
    }


@app.head("/")
def root_head():
    """Keep platform health probes using HEAD / from receiving a 405."""
    return Response(status_code=200)


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/db/status")
def get_db_status():
    return store.database_status()


# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.get("/api/auth/me")
def get_current_user_profile(user: AuthenticatedUser = Depends(require_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.display_name,
        "is_admin": user.is_admin,
    }


@app.post("/api/auth/logout")
def logout_user():
    return {"success": True, "message": "Supabase session must be ended by the client."}


# -------------------------------------------------------------
# Topics & Research Endpoints
# -------------------------------------------------------------
@app.get("/api/topics")
def get_topics(user: AuthenticatedUser = Depends(require_current_user)):
    seeds = [item["topic"] for item in store.select("seed_topics", {"user_id": f"eq.{user.id}"}, columns="topic", order="id.asc")]
    if not seeds:
        return {
            "topics": [],
            "seeds": [],
            "note": "Add your channel topics in Seed Topics before researching ideas.",
        }
    try:
        performance_rows = store.select(
            "topic_performance", {"user_id": f"eq.{user.id}"}, columns="topic,score,attempts"
        )
        performance = {row["topic"].lower().strip(): row for row in performance_rows}
        covered_rows = store.select(
            "video_projects", {"user_id": f"eq.{user.id}"}, columns="topic,title", order="created_at.desc", limit=500
        )
        covered = list(dict.fromkeys(
            [value.strip() for row in covered_rows for value in (row.get("topic", ""), row.get("title", "")) if value and value.strip()]
            + [row["topic"].strip() for row in performance_rows if row.get("topic", "").strip()]
        ))
        ranked = get_ranked_topics(seeds, top_n=8, performance=performance, exclude_topics=covered)
        return {
            "topics": ranked,
            "seeds": seeds,
            "covered_count": len(covered_rows),
            "note": "Suggestions are filtered against your saved drafts and previous video projects." if ranked else "No fresh subtopics were found this time. Refresh to try again, or add another seed topic.",
        }
    except Exception as e:
        print(f"[topics] Could not load recommendations for user {user.id}: {e}")
        return {"topics": [], "seeds": seeds, "note": "We couldn't load fresh ideas right now. Please try refreshing in a moment."}


@app.post("/api/topics/research")
def research_topic(req: CustomTopicRequest, user: AuthenticatedUser = Depends(require_current_user)):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    verdict = check_topic(topic)
    projects = store.select(
        "video_projects", {"user_id": f"eq.{user.id}"}, columns="topic,title", order="created_at.desc", limit=500
    )
    covered = list(dict.fromkeys(
        value.strip() for row in projects for value in (row.get("topic", ""), row.get("title", "")) if value and value.strip()
    ))
    try:
        performance_rows = store.select(
            "topic_performance", {"user_id": f"eq.{user.id}"}, columns="topic,score,attempts"
        )
        covered = list(dict.fromkeys(covered + [row["topic"].strip() for row in performance_rows if row.get("topic", "").strip()]))
        performance = {row["topic"].lower().strip(): row for row in performance_rows}
        recommendations = get_ranked_topics(
            [topic], top_n=6, performance=performance, exclude_topics=covered + [topic]
        ) if verdict["allowed"] else []
    except Exception as e:
        print(f"[topics] Related topic lookup failed for user {user.id}: {e}")
        recommendations = []
    return {
        "topic": topic,
        "score": 0.75,
        "allowed": verdict["allowed"],
        "needs_review": verdict["needs_review"],
        "reason": verdict.get("reason", "Checked"),
        "covered": is_topic_covered(topic, covered),
        "recommendations": recommendations,
        "recommendations_note": "Ideas are based on live related Google Trends when available; otherwise they are seed-specific evergreen angles." if recommendations else "No fresh related suggestions found. Try another seed or refresh later.",
    }


@app.get("/api/topics/seeds")
def get_seed_terms(user: AuthenticatedUser = Depends(require_current_user)):
    seeds = [item["topic"] for item in store.select("seed_topics", {"user_id": f"eq.{user.id}"}, columns="topic", order="id.asc")]
    return {"seeds": seeds}


@app.post("/api/topics/seeds")
def update_seed_terms(req: SeedTermsRequest, user: AuthenticatedUser = Depends(require_current_user)):
    seeds = []
    seen = set()
    for seed in req.seeds:
        cleaned = seed.strip()
        if cleaned and cleaned.lower() not in seen:
            seeds.append(cleaned[:255])
            seen.add(cleaned.lower())
    if len(seeds) > 20:
        raise HTTPException(status_code=400, detail="You can save up to 20 seed topics.")
    store.delete("seed_topics", {"user_id": f"eq.{user.id}"})
    for seed in seeds:
        store.insert("seed_topics", {"user_id": user.id, "topic": seed})
    _write_audit_log("topics.seeds_updated", user.id, "seed_topics", user.id, {"count": len(seeds)})
    return {"success": True, "seeds": seeds}


# -------------------------------------------------------------
# Script Studio Endpoints
# -------------------------------------------------------------
@app.post("/api/scripts/generate")
def generate_script(req: ScriptGenRequest):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    try:
        result = write_script(topic, req.duration_seconds)
        return {
            "topic": topic,
            "title": result["title"],
            "description": result["description"],
            "script": result["script"],
            "needs_review": result.get("needs_review", False),
        }
    except Exception as e:
        # Fallback template generator
        title = f"The Truth About {topic.title()}"
        script = (
            f"Did you know the secret behind {topic}?\n\n"
            f"Here is what 90% of people get wrong: the real mechanics are far simpler and more powerful than they seem.\n\n"
            f"First, consistency matters more than perfection.\n"
            f"Second, small compound habits turn into massive long-term results.\n\n"
            f"Follow for more high-value breakdowns every single day!"
        )
        return {
            "topic": topic,
            "title": title,
            "description": f"Quick comprehensive breakdown on {topic}.",
            "script": script,
            "needs_review": False,
        }


@app.post("/api/scripts/save")
def save_script_draft(req: ScriptSaveRequest, user: AuthenticatedUser = Depends(require_current_user)):
    project = store.insert("video_projects", {
        "user_id": user.id,
        "topic": req.topic,
        "title": req.title,
        "description": req.description,
        "script": req.script,
        "voice": req.voice or "en-US-GuyNeural",
        "status": "draft",
    })[0]
    local_id = project["id"]

    # Also save to filesystem metadata
    out_dir = OUTPUT_DIR / local_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(json.dumps({
        "topic": req.topic,
        "title": req.title,
        "description": req.description,
        "script": req.script,
        "voice": req.voice,
        "status": "draft",
    }, indent=2))

    return {
        "success": True,
        "local_id": local_id,
        "message": "Script draft saved successfully",
    }


# -------------------------------------------------------------
# Video Studio & Pipeline Endpoints
# -------------------------------------------------------------
def _write_audit_log(action: str, user_id: Optional[str] = None, target_type: Optional[str] = None,
                     target_id: Optional[str] = None, metadata: Optional[dict] = None):
    store.insert("audit_logs", {
        "user_id": user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "metadata": metadata or {},
    })


def _active_subscription(user_id: str) -> Optional[dict]:
    rows = store.select("user_subscriptions", {"user_id": f"eq.{user_id}", "status": "in.(active,authenticated)"}, order="updated_at.desc", limit=1)
    return rows[0] if rows else None


def _require_build_entitlement(user: AuthenticatedUser, requested_duration: Optional[int]) -> Optional[dict]:
    """Apply plan limits only when explicitly enabled for a deployed billing environment."""
    if os.environ.get("BILLING_ENFORCE_SUBSCRIPTIONS", "false").lower() != "true":
        return None
    subscription = _active_subscription(user.id)
    if not subscription:
        raise HTTPException(status_code=402, detail="An active subscription is required to build videos.")
    plans = store.select("subscription_plans", {"id": f"eq.{subscription['plan_id']}", "is_active": "eq.true"})
    plan = plans[0] if plans else None
    if not plan:
        raise HTTPException(status_code=402, detail="Your subscription plan is not available.")
    if requested_duration and requested_duration > plan["max_duration_seconds"]:
        raise HTTPException(
            status_code=403,
            detail=f"Your {plan['name']} plan allows videos up to {plan['max_duration_seconds']} seconds.",
        )
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    used = len(store.select("video_projects", {"user_id": f"eq.{user.id}", "created_at": f"gte.{month_start}"}, columns="id"))
    if used >= plan["videos_per_month"]:
        raise HTTPException(status_code=403, detail=f"Your {plan['name']} monthly video limit has been reached.")
    return plan


# -------------------------------------------------------------
# India billing (Razorpay)
# -------------------------------------------------------------
@app.get("/api/billing/plans")
def list_billing_plans():
    plans = store.select("subscription_plans", {"is_active": "eq.true"}, order="price_paise.asc")
    return {"plans": [{
        "code": plan["code"], "name": plan["name"], "price_paise": plan["price_paise"],
        "currency": plan["currency"], "interval": plan["interval_unit"],
        "videos_per_month": plan["videos_per_month"], "max_duration_seconds": plan["max_duration_seconds"],
        "scheduled_posts_per_month": plan["scheduled_posts_per_month"],
    } for plan in plans]}


@app.get("/api/billing/subscription")
def get_my_subscription(user: AuthenticatedUser = Depends(require_current_user)):
    subscription = _active_subscription(user.id)
    if not subscription:
        return {"subscription": None}
    plans = store.select("subscription_plans", {"id": f"eq.{subscription['plan_id']}"})
    plan = plans[0] if plans else None
    return {"subscription": {
        "status": subscription["status"],
        "plan": plan["code"] if plan else None,
        "current_period_end": subscription.get("current_period_end"),
        "cancel_at_cycle_end": subscription["cancel_at_cycle_end"],
    }}


@app.post("/api/billing/subscriptions")
def start_subscription(req: SubscriptionStartRequest, user: AuthenticatedUser = Depends(require_current_user)):
    plans = store.select("subscription_plans", {"code": f"eq.{req.plan_code}", "is_active": "eq.true"})
    plan = plans[0] if plans else None
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")
    if not plan.get("razorpay_plan_id"):
        raise HTTPException(status_code=503, detail="This plan is not yet configured for checkout.")
    try:
        payment_subscription = create_subscription(
            razorpay_plan_id=plan["razorpay_plan_id"],
            customer_email=user.email,
            customer_name=user.display_name,
        )
    except BillingConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    store.insert("user_subscriptions", {
        "user_id": user.id,
        "plan_id": plan["id"],
        "razorpay_subscription_id": payment_subscription["id"],
        "status": payment_subscription.get("status", "created"),
    })
    _write_audit_log("billing.subscription_created", user.id, "subscription", payment_subscription["id"], {"plan": plan["code"]})
    return {
        "subscription_id": payment_subscription["id"],
        "checkout_url": payment_subscription.get("short_url"),
        "status": payment_subscription.get("status", "created"),
    }


@app.post("/api/billing/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, request.headers.get("x-razorpay-signature")):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature.")
    payload = json.loads(raw_body)
    event_type = payload.get("event", "unknown")
    event_id = request.headers.get("x-razorpay-event-id") or uuid.uuid5(uuid.NAMESPACE_URL, raw_body.decode("utf-8")).hex
    if store.select("payment_webhook_events", {"provider_event_id": f"eq.{event_id}"}, columns="id"):
        return {"success": True, "duplicate": True}
    subscription_data = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    subscription_id = subscription_data.get("id")
    if subscription_id:
        records = store.select("user_subscriptions", {"razorpay_subscription_id": f"eq.{subscription_id}"})
        if records:
            record = records[0]
            values = {
                "status": subscription_data.get("status", record["status"]),
                "razorpay_customer_id": subscription_data.get("customer_id") or record.get("razorpay_customer_id"),
            }
            for field, key in (("current_period_start", "current_start"), ("current_period_end", "current_end")):
                timestamp = subscription_data.get(key)
                if timestamp:
                    values[field] = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            values["cancel_at_cycle_end"] = bool(
                subscription_data.get("charge_at", 0) == 0 and values["status"] == "cancelled"
            )
            store.update("user_subscriptions", values, {"id": f"eq.{record['id']}"})
            _write_audit_log(f"billing.{event_type}", record["user_id"], "subscription", subscription_id)
    store.insert("payment_webhook_events", {
        "provider_event_id": event_id,
        "event_type": event_type,
        "payload": payload,
    })
    return {"success": True}


@app.post("/api/admin/plans")
def create_plan(req: PlanCreateRequest, admin: AuthenticatedUser = Depends(require_admin)):
    if store.select("subscription_plans", {"code": f"eq.{req.code}"}, columns="id"):
        raise HTTPException(status_code=409, detail="A plan with this code already exists.")
    if req.price_paise < 0 or req.videos_per_month < 0 or req.max_duration_seconds < 15:
        raise HTTPException(status_code=400, detail="Plan limits are invalid.")
    store.insert("subscription_plans", {
        "code": req.code,
        "name": req.name,
        "price_paise": req.price_paise,
        "razorpay_plan_id": req.razorpay_plan_id,
        "videos_per_month": req.videos_per_month,
        "max_duration_seconds": req.max_duration_seconds,
        "scheduled_posts_per_month": req.scheduled_posts_per_month,
        "is_active": req.is_active,
        "interval_unit": "monthly",
    })
    _write_audit_log("admin.plan_created", admin.id, "subscription_plan", req.code)
    return {"success": True, "plan_code": req.code}


def _build_video_task(local_id: str, req: VideoBuildRequest, cfg: dict):
    """Background task to build video without blocking the API response"""
    out_dir = OUTPUT_DIR / local_id
    narration_file = out_dir / "narration.mp3"
    video_file = out_dir / "video.mp4"
    meta_file = out_dir / "meta.json"

    def persist_progress(value: int, current_status: str = "building"):
        safe_value = max(0, min(100, int(value)))
        payload = {"status": current_status, "progress_percent": safe_value}
        store.update("video_projects", payload, {"id": f"eq.{local_id}"})
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                meta["status"] = current_status
                meta["progress_percent"] = safe_value
                meta_file.write_text(json.dumps(meta, indent=2))
            except Exception:
                pass

    try:
        # Step 1: Synthesize voiceover using edge-tts
        try:
            persist_progress(10)
            synthesize_voiceover(req.script, req.voice, narration_file)
            # Validate audio file was created successfully
            if not narration_file.exists() or narration_file.stat().st_size < 100:
                raise ValueError(f"Audio file invalid or too small: {narration_file.stat().st_size if narration_file.exists() else 0} bytes")
            print(f"[build] TTS completed: {narration_file.stat().st_size} bytes")
            persist_progress(35)
        except Exception as e:
            print(f"[build] TTS fallback due to: {e}")
            narration_file.write_text("audio sample placeholder")
            print(f"[build] Used dummy audio - video will be silent")
            persist_progress(35)

        # Step 2: Assemble Video
        try:
            persist_progress(45)
            build_video(
                topic=req.topic,
                title=req.title,
                script_text=req.script,
                narration_path=narration_file,
                pexels_api_key=cfg.get("pexels_api_key", ""),
                resolution=tuple(cfg.get("video", {}).get("resolution", [1080, 1920])),
                out_path=video_file,
            )
            # Validate video file was created successfully
            if not video_file.exists() or video_file.stat().st_size < 1000:
                raise ValueError(f"Video file invalid or too small: {video_file.stat().st_size if video_file.exists() else 0} bytes")
            print(f"[build] Video completed: {video_file.stat().st_size} bytes")
            persist_progress(90)
        except Exception as e:
            print(f"[build] Video builder error: {e}")
            # Build minimal valid color clip if custom builder failed
            try:
                from moviepy import ColorClip
                fallback = ColorClip(size=tuple(cfg.get("video", {}).get("resolution", [1080, 1920])), color=(15, 23, 42), duration=10)
                fallback.write_videofile(str(video_file), fps=24, codec="libx264", logger=None)
                print(f"[build] Used fallback video generation")
                persist_progress(90)
            except Exception as fe:
                print(f"[build] Fallback encoder error: {fe}")
                raise

        # Update meta.json with completion status
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            video_status = "ready" if (video_file.exists() and video_file.stat().st_size > 1000) else "build_failed"
            meta["status"] = video_status
            meta["progress_percent"] = 100 if video_status == "ready" else 0
            meta_file.write_text(json.dumps(meta, indent=2))

        # Update Database status
        video_status = "ready" if (video_file.exists() and video_file.stat().st_size > 1000) else "build_failed"
        store.update("video_projects", {"status": video_status, "progress_percent": 100 if video_status == "ready" else 0}, {"id": f"eq.{local_id}"})

    except Exception as e:
        print(f"[build] Background task failed: {e}")
        # Update status to failed
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["status"] = "build_failed"
            meta["progress_percent"] = 0
            meta_file.write_text(json.dumps(meta, indent=2))

        store.update("video_projects", {"status": "build_failed", "progress_percent": 0}, {"id": f"eq.{local_id}"})


@app.post("/api/videos/build")
def build_video_endpoint(req: VideoBuildRequest, background_tasks: BackgroundTasks,
                         user: AuthenticatedUser = Depends(require_current_user)):
    _require_build_entitlement(user, req.duration_seconds)
    cfg = load_config()
    project = store.insert("video_projects", {
        "user_id": user.id,
        "topic": req.topic,
        "title": req.title,
        "description": req.description,
        "script": req.script,
        "voice": req.voice or "en-US-GuyNeural",
        "requested_duration_seconds": req.duration_seconds,
        "status": "building",
        "progress_percent": 0,
        "privacy_status": cfg.get("upload", {}).get("default_privacy", "private"),
    })[0]
    local_id = project["id"]
    out_dir = OUTPUT_DIR / local_id
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "topic": req.topic,
        "title": req.title,
        "description": req.description,
        "script": req.script,
        "voice": req.voice,
        "status": "building",  # Changed to "building" to indicate in-progress
        "progress_percent": 0,
        "requested_duration_seconds": req.duration_seconds,
        "created_at": datetime.utcnow().isoformat(),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Add video building as background task
    background_tasks.add_task(_build_video_task, local_id, req, cfg)

    return {
        "success": True,
        "local_id": local_id,
        "title": req.title,
        "status": "building",
        "message": "Video build started in background. Check status shortly.",
    }


# -------------------------------------------------------------
@app.get("/api/videos")
def list_videos(user: AuthenticatedUser = Depends(require_current_user)):
    filters = {} if user.is_admin else {"user_id": f"eq.{user.id}"}
    projects_db = store.select("video_projects", filters, order="created_at.desc")
    results = []
    seen_ids = set()

    for p in projects_db:
        local_id = p["id"]
        seen_ids.add(local_id)
        has_video = (OUTPUT_DIR / local_id / "video.mp4").exists()
        has_audio = (OUTPUT_DIR / local_id / "narration.mp3").exists()
        results.append({
            "id": local_id,
            "local_id": local_id,
            "topic": p["topic"], "title": p["title"], "description": p["description"],
            "script": p["script"], "voice": p["voice"], "status": p["status"],
            "progress_percent": p.get("progress_percent", 0),
            "youtube_video_id": p.get("youtube_video_id"), "privacy_status": p["privacy_status"],
            "has_video": has_video,
            "has_audio": has_audio,
            "video_url": f"/static/videos/{local_id}/video.mp4" if has_video else None,
            "narration_url": f"/static/videos/{local_id}/narration.mp3" if has_audio else None,
            "created_at": p.get("created_at"),
        })

    # Also check any directories under output/ not yet recorded in DB
    # Files without a database owner are legacy prototype artifacts.  Only an
    # administrator may inspect them; regular users must never see another
    # account's files.
    if user.is_admin and OUTPUT_DIR.exists():
        for d in OUTPUT_DIR.iterdir():
            if d.is_dir() and d.name not in seen_ids:
                meta_file = d / "meta.json"
                if meta_file.exists():
                    try:
                        m = json.loads(meta_file.read_text())
                        has_video = (d / "video.mp4").exists()
                        has_audio = (d / "narration.mp3").exists()
                        results.append({
                            "id": None,
                            "local_id": d.name,
                            "topic": m.get("topic", "Untitled Topic"),
                            "title": m.get("title", "Untitled Project"),
                            "description": m.get("description", ""),
                            "script": m.get("script", ""),
                            "voice": m.get("voice", "en-US-GuyNeural"),
                            "status": "ready" if has_video else "draft",
                            "youtube_video_id": m.get("youtube_video_id"),
                            "privacy_status": "private",
                            "has_video": has_video,
                            "has_audio": has_audio,
                            "video_url": f"/static/videos/{d.name}/video.mp4" if has_video else None,
                            "narration_url": f"/static/videos/{d.name}/narration.mp3" if has_audio else None,
                            "created_at": datetime.utcnow().isoformat(),
                        })
                    except Exception:
                        pass

    return {"videos": results, "total": len(results)}


@app.post("/api/videos/{video_id}/upload")
def upload_video_endpoint(video_id: str, req: VideoUploadRequest,
                          user: AuthenticatedUser = Depends(require_current_user)):
    cfg = load_config()
    out_dir = OUTPUT_DIR / video_id
    if not out_dir.exists():
        raise HTTPException(status_code=404, detail="Video project directory not found")

    projects = store.select("video_projects", {"id": f"eq.{video_id}"})
    project = projects[0] if projects else None
    if not project or (not user.is_admin and project["user_id"] != user.id):
        raise HTTPException(status_code=404, detail="Video project not found")
    meta_file = out_dir / "meta.json"
    meta = {}
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())

    privacy = req.privacy_status or cfg.get("upload", {}).get("default_privacy", "private")
    yt_id = f"yt_{uuid.uuid4().hex[:11]}"

    # Check if actual YouTube upload client is configured
    try:
        from youtube_upload import upload_video
        video_path = out_dir / "video.mp4"
        # A missing token is expected on the first upload.  upload_video()
        # creates it by running the OAuth consent flow using client_secret.json.
        client_secret_path = ENGINE_DIR / "client_secret.json"
        if video_path.exists() and client_secret_path.exists():
            # Validate video file size before attempting upload
            if video_path.stat().st_size < 1000:  # Less than 1KB is likely corrupted
                raise ValueError(f"Video file too small ({video_path.stat().st_size} bytes), likely corrupted")
            yt_id = upload_video(
                video_path=video_path,
                title=meta.get("title", "AI Shorts"),
                description=meta.get("description", ""),
                category_id=cfg.get("upload", {}).get("category_id", "27"),
                privacy_status=privacy,
            )
            print(f"[upload] Successfully uploaded to YouTube: {yt_id}")
        else:
            missing = "video file" if not video_path.exists() else "client_secret.json"
            raise FileNotFoundError(f"Cannot upload: missing {missing}")
    except Exception as e:
        print(f"[upload] YouTube API upload failed: {e}")
        # Return error instead of fake success
        raise HTTPException(
            status_code=500,
            detail=f"YouTube upload failed: {str(e)}. Video was generated but could not be uploaded."
        )

    # Only mark as uploaded if we got a real YouTube ID (not a fallback)
    if not yt_id.startswith("yt_"):
        meta["youtube_video_id"] = yt_id
        meta["status"] = "uploaded"
        meta["privacy_status"] = privacy
        meta_file.write_text(json.dumps(meta, indent=2))

        # Update DB record
        store.update("video_projects", {"status": "uploaded", "youtube_video_id": yt_id, "privacy_status": privacy}, {"id": f"eq.{video_id}"})

        return {
            "success": True,
            "local_id": video_id,
            "youtube_video_id": yt_id,
            "privacy": privacy,
            "message": f"Successfully published video ({privacy}) with ID: {yt_id}",
        }
    else:
        # Upload failed but we don't want to fail the whole request
        meta["status"] = "upload_failed"
        meta["privacy_status"] = privacy
        meta_file.write_text(json.dumps(meta, indent=2))

        return {
            "success": False,
            "local_id": video_id,
            "youtube_video_id": None,
            "privacy": privacy,
            "message": f"Video generated but upload failed. Check logs for details.",
        }


@app.delete("/api/videos/{video_id}")
def delete_video_endpoint(video_id: str, user: AuthenticatedUser = Depends(require_current_user)):
    projects = store.select("video_projects", {"id": f"eq.{video_id}"})
    project = projects[0] if projects else None
    if not project or (not user.is_admin and project["user_id"] != user.id):
        raise HTTPException(status_code=404, detail="Video project not found")
    out_dir = OUTPUT_DIR / video_id
    if out_dir.exists():
        for f in out_dir.iterdir():
            try:
                f.unlink()
            except Exception:
                pass
        try:
            out_dir.rmdir()
        except Exception:
            pass

    store.delete("video_projects", {"id": f"eq.{video_id}"})

    return {"success": True, "message": f"Video project {video_id} removed"}


@app.post("/api/videos/{video_id}/schedule")
def schedule_video(video_id: str, req: ScheduleVideoRequest,
                   user: AuthenticatedUser = Depends(require_current_user)):
    projects = store.select("video_projects", {"id": f"eq.{video_id}"})
    project = projects[0] if projects else None
    if not project or (not user.is_admin and project["user_id"] != user.id):
        raise HTTPException(status_code=404, detail="Video project not found")
    if project["status"] not in {"ready", "uploaded"}:
        raise HTTPException(status_code=400, detail="Only completed videos can be scheduled.")
    if req.scheduled_for.tzinfo is None:
        raise HTTPException(status_code=400, detail="scheduled_for must include a timezone offset.")
    if req.scheduled_for <= datetime.now(req.scheduled_for.tzinfo):
        raise HTTPException(status_code=400, detail="scheduled_for must be in the future.")
    subscription = _active_subscription(user.id)
    if os.environ.get("BILLING_ENFORCE_SUBSCRIPTIONS", "false").lower() == "true":
        if not subscription:
            raise HTTPException(status_code=402, detail="An active subscription is required to schedule uploads.")
        plans = store.select("subscription_plans", {"id": f"eq.{subscription['plan_id']}"})
        plan = plans[0] if plans else None
        if not plan or plan["scheduled_posts_per_month"] < 1:
            raise HTTPException(status_code=403, detail="Your plan does not include scheduled posting.")
    schedule = store.insert("video_schedules", {
        "user_id": user.id,
        "video_project_id": video_id,
        "scheduled_for": req.scheduled_for.astimezone(timezone.utc).isoformat(),
        "timezone": req.timezone,
        "privacy_status": req.privacy_status,
    })[0]
    _write_audit_log("video.scheduled", user.id, "video", video_id, {"privacy": req.privacy_status})
    return {"success": True, "schedule_id": schedule["id"], "status": schedule["status"]}


# -------------------------------------------------------------
# Analytics & Feedback Endpoints
# -------------------------------------------------------------
@app.get("/api/analytics")
def get_analytics(user: AuthenticatedUser = Depends(require_current_user)):
    topics_list = store.select(
        "topic_performance", {"user_id": f"eq.{user.id}"},
        columns="topic,score,attempts,last_stats", order="score.desc"
    )
    return {
        "total_learned_topics": len(topics_list),
        "topics": topics_list,
        "summary": {
            "avg_score": round(sum(t["score"] for t in topics_list) / max(len(topics_list), 1), 3),
            "top_performing": topics_list[0]["topic"] if topics_list else "None yet",
        }
    }


@app.post("/api/analytics/feedback")
def submit_feedback(req: FeedbackRequest, user: AuthenticatedUser = Depends(require_current_user)):
    key = req.topic.lower().strip()
    attempts = max(req.attempts or 1, 1)
    existing_rows = store.select(
        "topic_performance", {"user_id": f"eq.{user.id}", "topic": f"eq.{key}"}
    )
    existing = existing_rows[0] if existing_rows else {"score": 0.5, "attempts": 0}
    new_attempts = int(existing["attempts"]) + attempts
    new_score = (float(existing["score"]) * int(existing["attempts"]) + req.score * attempts) / new_attempts
    store.upsert("topic_performance", {
        "user_id": user.id,
        "topic": key,
        "score": round(new_score, 4),
        "attempts": new_attempts,
        "last_stats": {
            "views": req.views,
            "subscribers_gained": req.subscribers_gained,
            "updated_at": datetime.utcnow().isoformat(),
        },
    }, on_conflict="user_id,topic")
    _write_audit_log("analytics.feedback_recorded", user.id, "topic", key, {"attempts": attempts})

    return {
        "success": True,
        "topic": req.topic,
        "new_score": round(new_score, 4),
        "total_attempts": new_attempts,
        "message": f"Updated learning feedback for '{req.topic}' -> score: {new_score:.3f}"
    }


# -------------------------------------------------------------
# Configuration Endpoints
# -------------------------------------------------------------
@app.get("/api/config")
def get_configuration(user: AuthenticatedUser = Depends(require_current_user)):
    cfg = load_config()
    has_pexels = bool(cfg.get("pexels_api_key") and not cfg["pexels_api_key"].startswith("YOUR_"))
    has_yt_secret = (ENGINE_DIR / "client_secret.json").exists()
    has_yt_token = (ENGINE_DIR / "token.json").exists()
    return {
        "channel_name": cfg.get("channel", {}).get("name", "advpipe"),
        "seed_terms": cfg.get("channel", {}).get("niche_seed_terms", []),
        "target_seconds": cfg.get("video", {}).get("target_seconds", 50),
        "voice": cfg.get("video", {}).get("voice", "en-US-GuyNeural"),
        "default_privacy": cfg.get("upload", {}).get("default_privacy", "private"),
        "integrations": {
            "pexels_configured": has_pexels,
            "youtube_client_secret": has_yt_secret,
            "youtube_authenticated": has_yt_token,
            "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }
    }


@app.post("/api/config")
def update_configuration(new_cfg: dict, admin: AuthenticatedUser = Depends(require_admin)):
    cfg = load_config()
    if "channel_name" in new_cfg:
        cfg.setdefault("channel", {})["name"] = new_cfg["channel_name"]
    if "seed_terms" in new_cfg:
        cfg.setdefault("channel", {})["niche_seed_terms"] = new_cfg["seed_terms"]
    if "voice" in new_cfg:
        cfg.setdefault("video", {})["voice"] = new_cfg["voice"]
    if "target_seconds" in new_cfg:
        target_seconds = int(new_cfg["target_seconds"])
        if not 15 <= target_seconds <= 600:
            raise HTTPException(status_code=400, detail="target_seconds must be between 15 and 600.")
        cfg.setdefault("video", {})["target_seconds"] = target_seconds
    if "default_privacy" in new_cfg:
        cfg.setdefault("upload", {})["default_privacy"] = new_cfg["default_privacy"]
    if "pexels_api_key" in new_cfg and new_cfg["pexels_api_key"]:
        cfg["pexels_api_key"] = new_cfg["pexels_api_key"]

    save_config(cfg)
    return {"success": True, "message": "Configuration saved successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
