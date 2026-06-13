"""
ContextOS Gmail Connector.

Connects to Gmail via OAuth2 to fetch and ingest email content.
Requires Google API credentials to be configured.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.config import settings
from core.ingestion.base import BaseConnector

logger = logging.getLogger(__name__)

# Constants
MAX_RESULTS = 50
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailConnector(BaseConnector):
    """
    Gmail API connector for fetching and ingesting emails.

    Uses OAuth2 authentication via Google's API client library.
    Fetches emails from the user's inbox and converts them to
    document dicts for the ingestion pipeline.
    """

    def __init__(self, max_results: int = MAX_RESULTS) -> None:
        """
        Initialize the GmailConnector.

        Args:
            max_results: Maximum number of emails to fetch per sync.
        """
        super().__init__(name="gmail")
        self._max_results = max_results
        self._service = None

    def validate_config(self) -> bool:
        """
        Validate Gmail configuration.

        Checks that Google OAuth credentials file exists and the
        Gmail feature flag is enabled.

        Returns:
            True if configuration is valid.
        """
        if not settings.ENABLE_GMAIL:
            self._logger.info("Gmail connector is disabled via feature flag.")
            return False

        if not settings.GOOGLE_CLIENT_SECRETS_FILE.exists():
            self._logger.error(
                "Google client secrets file not found: %s",
                settings.GOOGLE_CLIENT_SECRETS_FILE,
            )
            return False

        return True

    def _authenticate(self) -> bool:
        """
        Authenticate with Gmail using OAuth2.

        Returns:
            True if authentication succeeded.
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            creds = None
            token_file = settings.GOOGLE_TOKEN_FILE

            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), GMAIL_SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(settings.GOOGLE_CLIENT_SECRETS_FILE), GMAIL_SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save the credentials for future runs
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(creds.to_json())

            self._service = build("gmail", "v1", credentials=creds)
            self._logger.info("Gmail authentication successful.")
            return True

        except ImportError as exc:
            self._logger.error(
                "Google API libraries not installed: %s. "
                "Install with: pip install google-auth google-auth-oauthlib "
                "google-api-python-client",
                exc,
            )
            return False
        except Exception as exc:
            self._logger.error("Gmail authentication failed: %s", exc)
            return False

    def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch emails from Gmail.

        Returns:
            A list of document dicts representing email messages.
        """
        if not self._authenticate():
            return []

        documents: list[dict[str, Any]] = []

        try:
            # List messages
            results = (
                self._service.users().messages().list(userId="me", maxResults=self._max_results, labelIds=["INBOX"]).execute()
            )

            messages = results.get("messages", [])
            self._logger.info("Found %d emails to process.", len(messages))

            for msg_info in messages:
                try:
                    msg = self._service.users().messages().get(userId="me", id=msg_info["id"], format="full").execute()
                    doc = self._parse_message(msg)
                    if doc:
                        documents.append(doc)
                except Exception as exc:
                    self._logger.error("Failed to fetch message %s: %s", msg_info["id"], exc)

        except Exception as exc:
            self._logger.error("Failed to list Gmail messages: %s", exc)

        return documents

    def _parse_message(self, message: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Parse a Gmail API message into a document dict.

        Args:
            message: Raw Gmail API message dict.

        Returns:
            A document dict, or None if parsing fails.
        """
        try:
            headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

            subject = headers.get("subject", "No Subject")
            from_addr = headers.get("from", "Unknown")
            to_addr = headers.get("to", "Unknown")
            date_str = headers.get("date", "")

            # Extract body text
            body = self._extract_body(message.get("payload", {}))

            if not body:
                return None

            content = f"Subject: {subject}\nFrom: {from_addr}\nTo: {to_addr}\n\n{body}"

            return {
                "id": f"gmail_{message['id']}",
                "source": "gmail",
                "content": content,
                "metadata": {
                    "subject": subject,
                    "from": from_addr,
                    "to": to_addr,
                    "gmail_id": message["id"],
                    "thread_id": message.get("threadId", ""),
                    "labels": message.get("labelIds", []),
                },
                "created_at": date_str or datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self._logger.error("Message parsing failed: %s", exc)
            return None

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """
        Recursively extract text body from a Gmail message payload.

        Args:
            payload: The Gmail message payload dict.

        Returns:
            The decoded text body.
        """
        body = ""

        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif payload.get("parts"):
            for part in payload["parts"]:
                part_body = self._extract_body(part)
                if part_body:
                    body = part_body
                    break

        return body
