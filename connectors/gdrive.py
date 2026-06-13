"""
ContextOS Google Drive Connector.

Connects to Google Drive via OAuth2 to fetch and ingest documents.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.config import settings
from core.ingestion.base import BaseConnector

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
MAX_RESULTS = 50


class GDriveConnector(BaseConnector):
    """Google Drive connector for fetching and ingesting documents."""

    def __init__(self, max_results: int = MAX_RESULTS) -> None:
        super().__init__(name="gdrive")
        self._max_results = max_results
        self._service = None

    def validate_config(self) -> bool:
        if not settings.ENABLE_GDRIVE:
            self._logger.info("GDrive connector disabled.")
            return False
        if not settings.GOOGLE_CLIENT_SECRETS_FILE.exists():
            self._logger.error("Google credentials not found.")
            return False
        return True

    def _authenticate(self) -> bool:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            token_file = settings.GOOGLE_TOKEN_FILE
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), DRIVE_SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(settings.GOOGLE_CLIENT_SECRETS_FILE), DRIVE_SCOPES)
                    creds = flow.run_local_server(port=0)
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(creds.to_json())
            self._service = build("drive", "v3", credentials=creds)
            return True
        except Exception as exc:
            self._logger.error("GDrive auth failed: %s", exc)
            return False

    def fetch(self) -> list[dict[str, Any]]:
        if not self._authenticate():
            return []
        documents: list[dict[str, Any]] = []
        try:
            results = (
                self._service.files()
                .list(
                    pageSize=self._max_results,
                    q="trashed=false",
                    fields="files(id, name, mimeType, modifiedTime)",
                )
                .execute()
            )
            for f in results.get("files", []):
                content = self._download(f)
                if content:
                    documents.append(
                        {
                            "id": f"gdrive_{f['id']}",
                            "source": "gdrive",
                            "content": content,
                            "metadata": {"filename": f.get("name", ""), "drive_id": f["id"]},
                            "created_at": f.get("modifiedTime", datetime.now(timezone.utc).isoformat()),
                        }
                    )
        except Exception as exc:
            self._logger.error("Drive fetch failed: %s", exc)
        return documents

    def _download(self, file_info: dict[str, Any]) -> Optional[str]:
        try:
            mime = file_info.get("mimeType", "")
            fid = file_info["id"]
            if mime == "application/vnd.google-apps.document":
                data = self._service.files().export(fileId=fid, mimeType="text/plain").execute()
            else:
                data = self._service.files().get_media(fileId=fid).execute()
            return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        except Exception as exc:
            self._logger.error("Download failed for %s: %s", file_info.get("name"), exc)
            return None
