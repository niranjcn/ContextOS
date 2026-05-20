"""
ContextOS Browser History Connector.

Parses Chrome and Firefox browser history from their local SQLite databases
and ingests visited page titles/URLs as documents.
"""

import logging
import platform
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import settings
from core.ingestion.base import BaseConnector

logger = logging.getLogger(__name__)

MAX_ENTRIES = 200


class BrowserHistoryConnector(BaseConnector):
    """Parses Chrome/Firefox history SQLite databases for ingestion."""

    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        super().__init__(name="browser_history")
        self._max_entries = max_entries

    def validate_config(self) -> bool:
        if not settings.ENABLE_BROWSER_HISTORY:
            self._logger.info("Browser history connector disabled.")
            return False
        return True

    def fetch(self) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        chrome_docs = self._fetch_chrome()
        firefox_docs = self._fetch_firefox()
        documents.extend(chrome_docs)
        documents.extend(firefox_docs)
        self._logger.info("Fetched %d browser history entries.", len(documents))
        return documents

    def _get_chrome_history_path(self) -> Optional[Path]:
        """Get the Chrome history database path for the current OS."""
        system = platform.system()
        home = Path.home()
        if system == "Windows":
            path = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "History"
        elif system == "Darwin":
            path = home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "History"
        else:
            path = home / ".config" / "google-chrome" / "Default" / "History"
        return path if path.exists() else None

    def _get_firefox_history_path(self) -> Optional[Path]:
        """Get the Firefox history database path for the current OS."""
        system = platform.system()
        home = Path.home()
        if system == "Windows":
            profiles_dir = home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
        elif system == "Darwin":
            profiles_dir = home / "Library" / "Application Support" / "Firefox" / "Profiles"
        else:
            profiles_dir = home / ".mozilla" / "firefox"

        if not profiles_dir.exists():
            return None
        for profile in profiles_dir.iterdir():
            places = profile / "places.sqlite"
            if places.exists():
                return places
        return None

    def _fetch_chrome(self) -> list[dict[str, Any]]:
        """Fetch entries from Chrome's History database."""
        db_path = self._get_chrome_history_path()
        if not db_path:
            self._logger.debug("Chrome history not found.")
            return []

        # Copy DB to avoid lock issues
        tmp_dir = Path(tempfile.mkdtemp())
        tmp_db = tmp_dir / "History"
        try:
            shutil.copy2(str(db_path), str(tmp_db))
            conn = sqlite3.connect(str(tmp_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT url, title, visit_count, last_visit_time "
                "FROM urls ORDER BY last_visit_time DESC LIMIT ?",
                (self._max_entries,),
            )
            docs = []
            for row in cursor.fetchall():
                title = row["title"] or row["url"]
                url = row["url"]
                content = f"Visited: {title}\nURL: {url}\nVisit count: {row['visit_count']}"
                import hashlib
                doc_id = hashlib.sha256(url.encode()).hexdigest()[:16]
                docs.append({
                    "id": f"chrome_{doc_id}",
                    "source": "browser_history",
                    "content": content,
                    "metadata": {"browser": "chrome", "url": url, "title": title},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            conn.close()
            return docs
        except Exception as exc:
            self._logger.error("Chrome history read failed: %s", exc)
            return []
        finally:
            shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def _fetch_firefox(self) -> list[dict[str, Any]]:
        """Fetch entries from Firefox's places.sqlite database."""
        db_path = self._get_firefox_history_path()
        if not db_path:
            self._logger.debug("Firefox history not found.")
            return []

        tmp_dir = Path(tempfile.mkdtemp())
        tmp_db = tmp_dir / "places.sqlite"
        try:
            shutil.copy2(str(db_path), str(tmp_db))
            conn = sqlite3.connect(str(tmp_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT url, title, visit_count, last_visit_date "
                "FROM moz_places WHERE title IS NOT NULL "
                "ORDER BY last_visit_date DESC LIMIT ?",
                (self._max_entries,),
            )
            docs = []
            for row in cursor.fetchall():
                title = row["title"] or row["url"]
                url = row["url"]
                content = f"Visited: {title}\nURL: {url}\nVisit count: {row['visit_count']}"
                import hashlib
                doc_id = hashlib.sha256(url.encode()).hexdigest()[:16]
                docs.append({
                    "id": f"firefox_{doc_id}",
                    "source": "browser_history",
                    "content": content,
                    "metadata": {"browser": "firefox", "url": url, "title": title},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            conn.close()
            return docs
        except Exception as exc:
            self._logger.error("Firefox history read failed: %s", exc)
            return []
        finally:
            shutil.rmtree(str(tmp_dir), ignore_errors=True)
