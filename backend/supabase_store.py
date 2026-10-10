"""Server-only gateway for Supabase Auth and PostgREST.

All application writes go through this module. The service-role key is never
sent to Flutter; Flutter uses only the project URL and publishable key.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class SupabaseConfigurationError(RuntimeError):
    pass


def _base_url() -> str:
    value = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not value:
        raise SupabaseConfigurationError("SUPABASE_URL is required.")
    return value


def _service_key() -> str:
    value = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not value:
        raise SupabaseConfigurationError("SUPABASE_SERVICE_ROLE_KEY is required on the server.")
    return value


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    display_name: str
    is_admin: bool


class SupabaseStore:
    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        key = _service_key()
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(self, method: str, path: str, *, payload: Any = None,
                 params: dict[str, str] | None = None, prefer: str | None = None) -> Any:
        response = requests.request(
            method,
            f"{_base_url()}{path}",
            headers=self._headers(prefer=prefer),
            json=payload,
            params=params,
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(f"Supabase request failed ({response.status_code}): {response.text[:500]}")
        if not response.content:
            return None
        return response.json()

    def current_user(self, access_token: str) -> AuthenticatedUser:
        response = requests.get(
            f"{_base_url()}/auth/v1/user",
            headers={"apikey": _service_key(), "Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if response.status_code in (401, 403):
            raise PermissionError("Invalid or expired Supabase session.")
        if not response.ok:
            raise RuntimeError(f"Supabase Auth validation failed: {response.text[:500]}")
        identity = response.json()
        user_id = identity["id"]
        email = identity.get("email") or ""
        metadata = identity.get("user_metadata") or {}
        display_name = str(metadata.get("full_name") or metadata.get("name") or email.split("@")[0] or "Creator")
        profiles = self.select("profiles", {"id": f"eq.{user_id}"}, columns="id,display_name,role")
        if profiles:
            profile = profiles[0]
        else:
            created = self.upsert("profiles", {"id": user_id, "display_name": display_name}, on_conflict="id")
            profile = created[0]
        return AuthenticatedUser(
            id=user_id,
            email=email,
            display_name=profile.get("display_name") or display_name,
            is_admin=profile.get("role") == "admin",
        )

    def select(self, table: str, filters: dict[str, str] | None = None, *, columns: str = "*",
               order: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        params = {"select": columns, **(filters or {})}
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        return self._request("GET", f"/rest/v1/{table}", params=params)

    def insert(self, table: str, row: dict[str, Any]) -> list[dict[str, Any]]:
        return self._request("POST", f"/rest/v1/{table}", payload=row, prefer="return=representation")

    def upsert(self, table: str, row: dict[str, Any], *, on_conflict: str) -> list[dict[str, Any]]:
        return self._request(
            "POST", f"/rest/v1/{table}", payload=row,
            params={"on_conflict": on_conflict},
            prefer="resolution=merge-duplicates,return=representation",
        )

    def update(self, table: str, values: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        return self._request("PATCH", f"/rest/v1/{table}", payload=values, params=filters, prefer="return=representation")

    def delete(self, table: str, filters: dict[str, str]) -> None:
        self._request("DELETE", f"/rest/v1/{table}", params=filters)

    def database_status(self) -> dict[str, Any]:
        """Check that the server can reach the configured Supabase database."""
        try:
            self.select("video_projects", columns="id", limit=1)
        except Exception:
            return {
                "connected": False,
                "dialect": "Supabase Postgres",
                "url": "Supabase",
                "stats": {},
                "message": "Supabase database is unavailable or not configured.",
            }
        return {
            "connected": True,
            "dialect": "Supabase Postgres",
            "url": "Supabase",
            "stats": {},
            "message": "Supabase Postgres is operational.",
        }


store = SupabaseStore()
