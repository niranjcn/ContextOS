"""
ContextOS Configuration Module.

Loads all configuration values from environment variables (via .env file)
and provides typed attributes for every config key. Includes helper methods
for path management and validation.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_FILE)


class ConfigurationError(Exception):
    """Raised when a required configuration value is missing or invalid."""


class Settings:
    """
    Central configuration for ContextOS.

    Loads all values from environment variables and provides typed attributes.
    Uses the .env file in the project root if present, with environment
    variable overrides taking precedence.
    """

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # ---- Paths ----
        self.CONTEXTOS_DATA_DIR: Path = self._resolve_path(
            os.getenv("CONTEXTOS_DATA_DIR", "~/.contextos/data")
        )
        self.CONTEXTOS_DB_DIR: Path = self._resolve_path(
            os.getenv("CONTEXTOS_DB_DIR", "~/.contextos/db")
        )
        self.CONTEXTOS_LOG_DIR: Path = self._resolve_path(
            os.getenv("CONTEXTOS_LOG_DIR", "~/.contextos/logs")
        )

        # ---- Encryption ----
        self.CONTEXTOS_ENCRYPTION_KEY: Optional[str] = os.getenv(
            "CONTEXTOS_ENCRYPTION_KEY"
        )

        # ---- LLM Settings ----
        self.OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.OLLAMA_FALLBACK_MODEL: str = os.getenv("OLLAMA_FALLBACK_MODEL", "mistral")
        self.OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))

        # ---- Embedding Settings ----
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        # ---- API Settings ----
        self.API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
        self.API_PORT: int = int(os.getenv("API_PORT", "8000"))
        self.API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"

        # ---- Google OAuth ----
        self.GOOGLE_CLIENT_SECRETS_FILE: Path = self._resolve_path(
            os.getenv(
                "GOOGLE_CLIENT_SECRETS_FILE",
                "~/.contextos/google_credentials.json",
            )
        )
        self.GOOGLE_TOKEN_FILE: Path = self._resolve_path(
            os.getenv("GOOGLE_TOKEN_FILE", "~/.contextos/google_token.json")
        )

        # ---- Feature Flags ----
        self.ENABLE_GMAIL: bool = (
            os.getenv("ENABLE_GMAIL", "false").lower() == "true"
        )
        self.ENABLE_GDRIVE: bool = (
            os.getenv("ENABLE_GDRIVE", "false").lower() == "true"
        )
        self.ENABLE_BROWSER_HISTORY: bool = (
            os.getenv("ENABLE_BROWSER_HISTORY", "false").lower() == "true"
        )
        self.ENABLE_WHISPER: bool = (
            os.getenv("ENABLE_WHISPER", "false").lower() == "true"
        )
        self.ENABLE_ENCRYPTION: bool = (
            os.getenv("ENABLE_ENCRYPTION", "true").lower() == "true"
        )

        # Validate critical settings
        self._validate()

        logger.info("ContextOS settings loaded successfully.")

    def _resolve_path(self, path_str: str) -> Path:
        """
        Resolve a path string, expanding ~ to the user's home directory.

        Args:
            path_str: A path string, possibly starting with ~.

        Returns:
            A resolved, absolute Path object.
        """
        return Path(path_str).expanduser().resolve()

    def _validate(self) -> None:
        """
        Validate critical configuration values.

        Raises:
            ConfigurationError: If encryption is enabled but no key is provided,
                or if the key is set to the placeholder value.
        """
        if self.ENABLE_ENCRYPTION:
            if not self.CONTEXTOS_ENCRYPTION_KEY:
                raise ConfigurationError(
                    "CONTEXTOS_ENCRYPTION_KEY must be set when encryption is enabled. "
                    "Generate one with: python -c "
                    '"from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())"'
                )
            if self.CONTEXTOS_ENCRYPTION_KEY == "your-generated-key-here":
                raise ConfigurationError(
                    "CONTEXTOS_ENCRYPTION_KEY is still set to the placeholder value. "
                    "Please generate a real key."
                )

    def get_db_path(self, name: str) -> Path:
        """
        Get a database path, creating the directory if it doesn't exist.

        Args:
            name: The name of the database subdirectory (e.g., 'graph', 'vector').

        Returns:
            A Path to the database directory, guaranteed to exist.
        """
        db_path = self.CONTEXTOS_DB_DIR / name
        db_path.mkdir(parents=True, exist_ok=True)
        return db_path

    def get_data_path(self, name: str) -> Path:
        """
        Get a data path, creating the directory if it doesn't exist.

        Args:
            name: The name of the data subdirectory.

        Returns:
            A Path to the data directory, guaranteed to exist.
        """
        data_path = self.CONTEXTOS_DATA_DIR / name
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    def get_log_path(self) -> Path:
        """
        Get the log directory path, creating it if it doesn't exist.

        Returns:
            A Path to the log directory, guaranteed to exist.
        """
        self.CONTEXTOS_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return self.CONTEXTOS_LOG_DIR

    def __repr__(self) -> str:
        """Return a string representation of current settings (redacting secrets)."""
        return (
            f"Settings("
            f"data_dir={self.CONTEXTOS_DATA_DIR}, "
            f"db_dir={self.CONTEXTOS_DB_DIR}, "
            f"ollama_host={self.OLLAMA_HOST}, "
            f"ollama_model={self.OLLAMA_MODEL}, "
            f"encryption={'enabled' if self.ENABLE_ENCRYPTION else 'disabled'}"
            f")"
        )


def _create_settings() -> Settings:
    """
    Create a Settings instance, falling back to safe defaults if .env is missing.

    Returns:
        A configured Settings instance.
    """
    try:
        return Settings()
    except ConfigurationError as exc:
        logger.warning(
            "Configuration issue: %s. "
            "Some features may be unavailable until configured.",
            exc,
        )
        # Re-create with encryption disabled for development convenience
        os.environ["ENABLE_ENCRYPTION"] = "false"
        return Settings()


# Singleton settings instance — import this throughout the project
settings = _create_settings()
