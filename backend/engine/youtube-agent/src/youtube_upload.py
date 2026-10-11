"""
Uploads a finished video to YouTube via the Data API v3.

Deliberately uploads as PRIVATE by default (see config.yaml
`upload.default_privacy`) so nothing goes public without you flipping it
yourself in Studio or re-running with an explicit override. This is a
guardrail, not busywork — treat changing the default to "public" as a
decision you make consciously, not a config default.
"""

from pathlib import Path

import google.auth.transport.requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json"
CLIENT_SECRET_PATH = Path(__file__).resolve().parent.parent / "client_secret.json"


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    category_id: str,
    privacy_status: str,
    tags: list[str] | None = None,
    credentials: Credentials | None = None,
) -> str:
    # Web requests always pass the credential for the authenticated owner.
    # The local token-file flow is retained only for the standalone CLI tool.
    creds = credentials or _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,  # "private" / "unlisted" / "public"
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube_upload] {int(status.progress() * 100)}% uploaded")

    video_id = response["id"]
    print(f"[youtube_upload] Done. Video ID: {video_id} (privacy={privacy_status})")
    return video_id
