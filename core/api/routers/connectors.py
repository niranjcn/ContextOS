import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config_store import (
    CONNECTOR_GUIDES,
    CONNECTOR_META,
    delete_connector_config,
    get_all_connectors,
    get_connector_config,
    save_credential_file,
    set_connector_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConfigureRequest(BaseModel):
    enabled: bool | None = Field(default=None, description="Enable or disable the connector")
    credentials_json: str | None = Field(
        default=None,
        description="JSON content of the OAuth credentials file",
    )
    settings: dict | None = Field(
        default=None,
        description="Additional settings (paths, config values)",
    )


class ConnectorStatus(BaseModel):
    id: str
    name: str
    icon: str
    description: str
    enabled: bool
    configured: bool
    needs_credentials: bool
    credential_type: str | None
    settings: dict


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]


class ConnectorGuideStep(BaseModel):
    step: int
    title: str
    description: str
    link: str | None = None


class ConnectorGuideResponse(BaseModel):
    connector: str
    steps: list[ConnectorGuideStep]


class SyncResponse(BaseModel):
    connector: str
    status: str
    message: str


@router.get("", response_model=ConnectorListResponse)
async def list_connectors():
    connectors = get_all_connectors()
    return ConnectorListResponse(connectors=[ConnectorStatus(**c) for c in connectors])


@router.get("/{name}", response_model=ConnectorStatus)
async def get_connector(name: str):
    if name not in CONNECTOR_META:
        raise HTTPException(404, detail=f"Connector '{name}' not found")
    meta = CONNECTOR_META[name]
    cfg = get_connector_config(name)
    is_configured = bool(cfg.get("configured", False))
    if meta["needs_credentials"]:
        is_configured = bool(cfg.get("credentials_file"))
    return ConnectorStatus(
        id=name,
        name=meta["name"],
        icon=meta["icon"],
        description=meta["description"],
        enabled=bool(cfg.get("enabled", False)),
        configured=is_configured,
        needs_credentials=meta["needs_credentials"],
        credential_type=meta["credential_type"],
        settings={k: v for k, v in cfg.items() if k not in ("enabled", "configured")},
    )


@router.get("/{name}/guide", response_model=ConnectorGuideResponse)
async def get_connector_guide(name: str):
    if name not in CONNECTOR_GUIDES:
        raise HTTPException(404, detail=f"No guide available for '{name}'")
    return ConnectorGuideResponse(
        connector=name,
        steps=[ConnectorGuideStep(**s) for s in CONNECTOR_GUIDES[name]],
    )


@router.post("/{name}/configure")
async def configure_connector(name: str, body: ConfigureRequest):
    if name not in CONNECTOR_META:
        raise HTTPException(404, detail=f"Connector '{name}' not found")

    updates = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.credentials_json:
        path = save_credential_file(name, body.credentials_json)
        updates["credentials_file"] = path
        updates["configured"] = True
    if body.settings:
        updates["settings"] = body.settings

    if updates:
        set_connector_config(name, updates)

    cfg = get_connector_config(name)
    return {
        "status": "ok",
        "connector": name,
        "enabled": cfg.get("enabled", False),
        "configured": cfg.get("configured", False) or bool(cfg.get("credentials_file")),
    }


@router.post("/{name}/sync", response_model=SyncResponse)
async def sync_connector(name: str):
    if name not in CONNECTOR_META:
        raise HTTPException(404, detail=f"Connector '{name}' not found")

    if name == "local_files":
        try:
            from connectors.local_files import LocalFileConnector

            connector = LocalFileConnector()
            count = connector.sync()
            return SyncResponse(
                connector=name,
                status="completed",
                message=f"Ingested {count} files from watched directories.",
            )
        except Exception as exc:
            raise HTTPException(500, detail=f"Sync failed: {exc}")

    cfg = get_connector_config(name)
    if not cfg.get("enabled", False):
        return SyncResponse(
            connector=name,
            status="skipped",
            message="Connector is not enabled. Enable it first in the settings.",
        )

    try:
        if name == "gmail":
            from connectors.gmail import GmailConnector

            creds_file = cfg.get("credentials_file")
            if not creds_file:
                return SyncResponse(
                    connector=name,
                    status="error",
                    message="No credentials configured. Follow the setup guide first.",
                )
            connector = GmailConnector(credentials_path=creds_file)
            count = connector.sync()
            return SyncResponse(
                connector=name,
                status="completed",
                message=f"Synced {count} emails from Gmail.",
            )

        elif name == "gdrive":
            from connectors.gdrive import GDriveConnector

            creds_file = cfg.get("credentials_file")
            if not creds_file:
                return SyncResponse(
                    connector=name,
                    status="error",
                    message="No credentials configured. Follow the setup guide first.",
                )
            connector = GDriveConnector(credentials_path=creds_file)
            count = connector.sync()
            return SyncResponse(
                connector=name,
                status="completed",
                message=f"Synced {count} files from Google Drive.",
            )

        elif name == "browser_history":
            from connectors.browser_history import BrowserHistoryConnector

            settings = cfg.get("settings", {})
            path = settings.get("history_path") if settings else None
            connector = BrowserHistoryConnector(history_path=path)
            count = connector.sync()
            return SyncResponse(
                connector=name,
                status="completed",
                message=f"Synced {count} history entries.",
            )

        else:
            return SyncResponse(
                connector=name,
                status="error",
                message=f"Sync not implemented for '{name}'.",
            )

    except ImportError as exc:
        raise HTTPException(500, detail=f"Connector module not found: {exc}")
    except Exception as exc:
        raise HTTPException(500, detail=f"Sync failed: {exc}")


@router.delete("/{name}/configure")
async def remove_connector_config(name: str):
    if name not in CONNECTOR_META:
        raise HTTPException(404, detail=f"Connector '{name}' not found")
    delete_connector_config(name)
    return {"status": "ok", "connector": name, "message": "Configuration removed."}
