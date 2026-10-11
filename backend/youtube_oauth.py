"""Per-user YouTube OAuth helpers with encrypted refresh-token storage."""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from backend.supabase_store import store

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
OAUTH_STATE_TTL_SECONDS = 10 * 60


def _client_config() -> dict[str, Any]:
    raw = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=503, detail="GOOGLE_CLIENT_SECRET_JSON is not valid JSON.") from exc
    else:
        path = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE")
        if not path:
            from pathlib import Path
            path = str(Path(__file__).resolve().parent / "engine" / "youtube-agent" / "client_secret.json")
        try:
            parsed = json.loads(open(path, encoding="utf-8").read())
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="YouTube is not configured. Set GOOGLE_CLIENT_SECRET_JSON (recommended) or GOOGLE_CLIENT_SECRETS_FILE on the backend.",
            ) from exc

    section = parsed.get("web") or parsed.get("installed")
    if not section or not section.get("client_id") or not section.get("client_secret"):
        raise HTTPException(status_code=503, detail="Google OAuth client config must contain client_id and client_secret.")
    return {"web": section}


def _redirect_uri() -> str:
    value = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
    if not value:
        base = os.environ.get("PUBLIC_API_URL") or os.environ.get("RENDER_EXTERNAL_URL")
        if base:
            value = f"{base.rstrip('/')}/api/youtube/callback"
    if not value:
        raise HTTPException(status_code=503, detail="Set GOOGLE_OAUTH_REDIRECT_URI to the backend /api/youtube/callback URL.")
    return value


def _fernet() -> Fernet:
    key = os.environ.get("YOUTUBE_TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Set YOUTUBE_TOKEN_ENCRYPTION_KEY on the backend before connecting YouTube.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(status_code=503, detail="YOUTUBE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def _state_secret() -> bytes:
    value = os.environ.get("YOUTUBE_OAUTH_STATE_SECRET", "")
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="Set YOUTUBE_OAUTH_STATE_SECRET to a random value of at least 32 characters.")
    return value.encode("utf-8")


def _encode_state(user_id: str) -> str:
    payload = {"sub": user_id, "nonce": uuid.uuid4().hex, "iat": int(time.time())}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_state_secret(), body.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{body}.{sig}"


def _decode_state(state: str) -> str:
    try:
        body, signature = state.split(".", 1)
        expected = hmac.new(_state_secret(), body.encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, actual):
            raise ValueError("bad signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        issued = int(payload["iat"])
        if not payload.get("sub") or int(time.time()) - issued > OAUTH_STATE_TTL_SECONDS or issued > int(time.time()) + 30:
            raise ValueError("expired state")
        return str(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="The YouTube authorization state is invalid or expired. Please reconnect.") from exc


def create_authorization_url(user_id: str) -> str:
    _fernet()  # Fail before redirecting if at-rest token encryption is not configured.
    redirect_uri = _redirect_uri()
    flow = Flow.from_client_config(_client_config(), scopes=YOUTUBE_SCOPES, redirect_uri=redirect_uri)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=_encode_state(user_id),
    )
    return authorization_url


def _credentials_from_refresh_token(refresh_token: str) -> Credentials:
    client = _client_config()["web"]
    token_uri = client.get("token_uri", "https://oauth2.googleapis.com/token")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client["client_id"],
        client_secret=client["client_secret"],
        scopes=YOUTUBE_SCOPES,
    )
    creds.refresh(Request())
    return creds


def complete_authorization(code: str, state: str) -> tuple[str, dict[str, str]]:
    user_id = _decode_state(state)
    redirect_uri = _redirect_uri()
    flow = Flow.from_client_config(_client_config(), scopes=YOUTUBE_SCOPES, redirect_uri=redirect_uri, state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials
    refresh_token = creds.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Google did not return a refresh token. Disconnect the app from your Google account and reconnect with consent.")

    refreshed_creds = _credentials_from_refresh_token(refresh_token)
    youtube = build("youtube", "v3", credentials=refreshed_creds, cache_discovery=False)
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    channel = (response.get("items") or [{}])[0]
    snippet = channel.get("snippet") or {}
    metadata = {"channel_id": str(channel.get("id") or ""), "channel_title": str(snippet.get("title") or "YouTube channel")}
    encrypted = _fernet().encrypt(refresh_token.encode("utf-8")).decode("ascii")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    store.upsert("youtube_connections", {
        "user_id": user_id,
        "encrypted_refresh_token": encrypted,
        **metadata,
        "connected_at": now,
        "updated_at": now,
    }, on_conflict="user_id")
    return user_id, metadata


def get_connection_status(user_id: str) -> dict[str, Any]:
    rows = store.select("youtube_connections", {"user_id": f"eq.{user_id}"}, columns="channel_id,channel_title,connected_at")
    if not rows:
        return {"connected": False, "channel_id": None, "channel_title": None, "connected_at": None}
    row = rows[0]
    return {"connected": True, **row}


def get_user_credentials(user_id: str) -> Credentials:
    rows = store.select("youtube_connections", {"user_id": f"eq.{user_id}"}, columns="encrypted_refresh_token")
    if not rows:
        raise HTTPException(status_code=409, detail="Connect your YouTube account in Settings before uploading.")
    try:
        refresh_token = _fernet().decrypt(rows[0]["encrypted_refresh_token"].encode("ascii")).decode("utf-8")
    except (InvalidToken, KeyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Stored YouTube authorization could not be decrypted. Check the backend encryption key.") from exc
    try:
        return _credentials_from_refresh_token(refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="YouTube authorization expired or was revoked. Reconnect your account in Settings.") from exc


def disconnect_user(user_id: str) -> None:
    rows = store.select("youtube_connections", {"user_id": f"eq.{user_id}"}, columns="encrypted_refresh_token")
    if rows:
        try:
            refresh_token = _fernet().decrypt(rows[0]["encrypted_refresh_token"].encode("ascii")).decode("utf-8")
            import requests
            requests.post("https://oauth2.googleapis.com/revoke", data={"token": refresh_token}, timeout=10)
        except Exception as exc:
            print(f"[youtube] Token revocation request failed for user {user_id}: {exc}")
    store.delete("youtube_connections", {"user_id": f"eq.{user_id}"})


def frontend_callback_url(outcome: str) -> str:
    origin = os.environ.get("FRONTEND_URL") or os.environ.get("VERCEL_URL")
    if not origin:
        raise HTTPException(status_code=503, detail="Set FRONTEND_URL to your frontend origin for YouTube OAuth callbacks.")
    if origin.startswith("www.") or ("://" not in origin and not origin.startswith("localhost")):
        origin = f"https://{origin}"
    elif "localhost" in origin and "://" not in origin:
        origin = f"http://{origin}"
    return f"{origin.rstrip('/')}/?{urlencode({'youtube': outcome})}"
