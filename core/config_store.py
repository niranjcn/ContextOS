import json
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

CONNECTOR_GUIDES: dict[str, list[dict]] = {
    "gmail": [
        {
            "step": 1,
            "title": "Go to Google Cloud Console",
            "description": (
                "Open the Google Cloud Console in your browser. "
                "Sign in with the Google account that owns the Gmail you want to index."
            ),
            "link": "https://console.cloud.google.com/",
        },
        {
            "step": 2,
            "title": "Create a new project (or select existing)",
            "description": (
                "At the top of the page, click the project dropdown and click "
                "'New Project'. Give it a name like 'ContextOS' and click 'Create'."
            ),
            "link": "https://console.cloud.google.com/projectcreate",
        },
        {
            "step": 3,
            "title": "Enable the Gmail API",
            "description": (
                "In the left sidebar, go to 'APIs & Services' > 'Library'. "
                "Search for 'Gmail API', click on it, and click 'Enable'."
            ),
            "link": "https://console.cloud.google.com/apis/library/gmail.googleapis.com",
        },
        {
            "step": 4,
            "title": "Configure OAuth consent screen",
            "description": (
                "Go to 'APIs & Services' > 'OAuth consent screen'. "
                "Select 'External' user type and click 'Create'. "
                "Fill in the App name ('ContextOS'), your email, and "
                "developer contact info. Click 'Save and Continue'. "
                "Skip scopes and test users for now."
            ),
            "link": "https://console.cloud.google.com/apis/credentials/consent",
        },
        {
            "step": 5,
            "title": "Create OAuth 2.0 credentials",
            "description": (
                "Go to 'APIs & Services' > 'Credentials'. "
                "Click '+ Create Credentials' > 'OAuth client ID'. "
                "Select 'Desktop app' as the application type. "
                "Give it a name like 'ContextOS Desktop' and click 'Create'."
            ),
            "link": "https://console.cloud.google.com/apis/credentials",
        },
        {
            "step": 6,
            "title": "Download the credentials file",
            "description": (
                "After creation, a popup will show your client ID and secret. "
                "Click 'Download JSON' to download the credentials file. "
                "Upload it below using the 'Choose File' button."
            ),
        },
    ],
    "gdrive": [
        {
            "step": 1,
            "title": "Go to Google Cloud Console",
            "description": (
                "Open the Google Cloud Console in your browser. "
                "Sign in with the Google account that owns the Drive you want to index."
            ),
            "link": "https://console.cloud.google.com/",
        },
        {
            "step": 2,
            "title": "Select your project",
            "description": (
                "If you already created a project for the Gmail connector, "
                "select the same project. Otherwise, create a new project."
            ),
            "link": "https://console.cloud.google.com/projectcreate",
        },
        {
            "step": 3,
            "title": "Enable the Google Drive API",
            "description": (
                "Go to 'APIs & Services' > 'Library'. " "Search for 'Google Drive API', click on it, and click 'Enable'."
            ),
            "link": "https://console.cloud.google.com/apis/library/drive.googleapis.com",
        },
        {
            "step": 4,
            "title": "Use the same OAuth credentials",
            "description": (
                "If you already created OAuth credentials for Gmail, "
                "you can reuse the same credentials file — it supports both APIs. "
                "If not, follow steps 4-6 from the Gmail setup guide above."
            ),
        },
        {
            "step": 5,
            "title": "Upload your credentials",
            "description": (
                "Upload the same or a new credentials JSON file below. "
                "The connector will use it to authenticate with Google Drive."
            ),
        },
    ],
    "browser_history": [
        {
            "step": 1,
            "title": "Locate your browser history file",
            "description": (
                "Chrome stores history at: "
                "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\History\\n"
                "Firefox stores history at: "
                "%APPDATA%\\Mozilla\\Firefox\\Profiles\\*.default\\places.sqlite\\n"
                "Edge stores history at: "
                "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\History"
            ),
        },
        {
            "step": 2,
            "title": "Configure the path below",
            "description": (
                "Enter the full path to your browser's history file "
                "in the field below. The connector will read from this file "
                "and index the URLs and page titles into your knowledge base."
            ),
        },
        {
            "step": 3,
            "title": "Enable and sync",
            "description": (
                "Toggle the switch to enable the connector and click 'Sync Now' " "to start indexing your browsing history."
            ),
        },
    ],
    "local_files": [
        {
            "step": 1,
            "title": "Add directories to watch",
            "description": (
                "Enter the full paths to directories you want ContextOS "
                "to monitor for new files. Separate multiple paths with commas. "
                "Supported formats: PDF, DOCX, TXT, MD."
            ),
        },
        {
            "step": 2,
            "title": "Enable and sync",
            "description": (
                "Toggle the switch to enable the connector. "
                "Click 'Sync Now' to scan the directories and index all files. "
                "New files added later will be picked up automatically."
            ),
        },
    ],
}


CONNECTOR_META: dict[str, dict] = {
    "gmail": {
        "id": "gmail",
        "name": "Gmail",
        "icon": "📧",
        "description": "Import emails from Gmail. Requires Google API credentials.",
        "needs_credentials": True,
        "credential_type": "google_oauth",
    },
    "gdrive": {
        "id": "gdrive",
        "name": "Google Drive",
        "icon": "📁",
        "description": "Import documents from Google Drive. " "Requires Google API credentials.",
        "needs_credentials": True,
        "credential_type": "google_oauth",
    },
    "browser_history": {
        "id": "browser_history",
        "name": "Browser History",
        "icon": "🌐",
        "description": "Import your Chrome, Firefox, or Edge browsing history.",
        "needs_credentials": False,
        "credential_type": None,
    },
    "local_files": {
        "id": "local_files",
        "name": "Local Files",
        "icon": "💻",
        "description": "Watch directories for new PDF, DOCX, TXT, and MD files.",
        "needs_credentials": False,
        "credential_type": None,
    },
}


def _config_path() -> Path:
    return settings.CONTEXTOS_DATA_DIR / "connectors_config.json"


def _secrets_dir() -> Path:
    p = Path("secrets")
    p.mkdir(exist_ok=True)
    return p


def load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read connector config: %s", exc)
    return {}


def save_config(config: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, default=str))


def get_connector_config(name: str) -> dict:
    return load_config().get(name, {})


def set_connector_config(name: str, values: dict) -> dict:
    config = load_config()
    existing = config.get(name, {})
    existing.update(values)
    config[name] = existing
    save_config(config)
    return existing


def delete_connector_config(name: str) -> None:
    config = load_config()
    config.pop(name, None)
    save_config(config)


def save_credential_file(name: str, content: str) -> str:
    secrets = _secrets_dir()
    filename = f"{name}_credentials.json"
    path = secrets / filename
    path.write_text(content)
    set_connector_config(name, {"credentials_file": str(path)})
    return str(path)


def is_connector_enabled(name: str) -> bool:
    cfg = get_connector_config(name)
    return cfg.get("enabled", False)


def get_all_connectors() -> list[dict]:
    config = load_config()
    results = []
    for cid, meta in CONNECTOR_META.items():
        cfg = config.get(cid, {})
        is_configured = bool(cfg.get("configured", False))
        if meta["needs_credentials"]:
            is_configured = bool(cfg.get("credentials_file"))
        is_enabled = bool(cfg.get("enabled", False))
        results.append(
            {
                **meta,
                "enabled": is_enabled,
                "configured": is_configured,
                "settings": {k: v for k, v in cfg.items() if k not in ("enabled", "configured")},
            }
        )
    return results
