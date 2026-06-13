"""
ContextOS Inference Backends.

Defines a pluggable backend abstraction for LLM inference, supporting:
  - Ollama (local, offline-capable)
  - External AI CLI tools (opencode, claude, gemini, etc.) — auto-detected

On startup the system scans for available CLI tools and selects the best
backend automatically. The user can override with INFERENCE_BACKEND=ollama.
"""

import logging
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Known external CLI tools — name → detection & invocation templates
# ---------------------------------------------------------------------------
# Each entry describes how to detect the tool on PATH and how to invoke it.
# {prompt} is replaced with the full prompt text.
KNOWN_CLI_TOOLS: list[dict[str, Any]] = [
    {
        "name": "claude",
        "detect_cmd": "claude",
        "invoke_args": ["-p", "{prompt}"],
        "description": "Anthropic Claude CLI",
    },
    {
        "name": "gemini",
        "detect_cmd": "gemini",
        "invoke_args": ["ask", "{prompt}"],
        "description": "Google Gemini CLI",
    },
    {
        "name": "opencode",
        "detect_cmd": "opencode",
        "invoke_args": ["-p", "{prompt}"],
        "description": "opencode AI coding assistant",
    },
]


@dataclass
class DetectedTool:
    name: str
    command: str
    invoke_args: list[str]
    description: str


def _find_on_path(name: str) -> Optional[str]:
    """Check if a command exists on PATH (cross-platform)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["where", name], capture_output=True, text=True, timeout=5
            )
        else:
            result = subprocess.run(
                ["which", name], capture_output=True, text=True, timeout=5
            )
        if result.returncode == 0:
            candidates = result.stdout.strip().splitlines()
            for path in candidates:
                path = path.strip()
                if not path:
                    continue
                if sys.platform == "win32":
                    ext = os.path.splitext(path)[1].lower()
                    if ext in (".exe", ".cmd", ".bat", ".com"):
                        return path
                    if not ext and os.path.isfile(path):
                        continue
                return path
            return None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def detect_cli_tools() -> list[DetectedTool]:
    """Scan the system for known AI CLI tools and return those found."""
    found: list[DetectedTool] = []
    for tool in KNOWN_CLI_TOOLS:
        cmd_path = _find_on_path(tool["detect_cmd"])
        if cmd_path:
            found.append(
                DetectedTool(
                    name=tool["name"],
                    command=cmd_path,
                    invoke_args=tool["invoke_args"],
                    description=tool["description"],
                )
            )
            logger.info("Detected CLI tool: %s at %s", tool["name"], cmd_path)
    return found


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------


class InferenceBackend(ABC):
    """Abstract base for an LLM inference backend."""

    @abstractmethod
    def generate(self, prompt: str, timeout: int = 180) -> str:
        """Generate a complete response for the given prompt."""

    @abstractmethod
    def generate_stream(
        self, prompt: str
    ) -> Generator[str, None, None]:
        """Yield tokens one-by-one for streaming responses."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if the backend is available and usable."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier for this backend (e.g. 'ollama/llama3.2:1b')."""

    @abstractmethod
    def info(self) -> dict[str, Any]:
        """Return metadata about the backend for the health endpoint."""


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------


class OllamaBackend(InferenceBackend):
    """Inference via a local Ollama server."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        fallback_model: str = "mistral",
        timeout: int = 120,
    ) -> None:
        import ollama

        self._host = host
        self._model = model
        self._fallback = fallback_model
        self._timeout = timeout
        self._client = ollama.Client(host=host)

    def generate(self, prompt: str, timeout: int = 180) -> str:
        model = self._model
        try:
            response = self._client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 2048},
            )
            return response["message"]["content"]
        except Exception as primary_exc:
            logger.warning(
                "Primary model '%s' failed: %s. Trying fallback '%s'...",
                model,
                primary_exc,
                self._fallback,
            )
            response = self._client.chat(
                model=self._fallback,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 2048},
            )
            return response["message"]["content"]

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        model = self._model
        try:
            stream = self._client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"num_predict": 2048},
            )
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        except Exception as primary_exc:
            logger.warning(
                "Primary model '%s' stream failed: %s. Trying fallback...",
                model,
                primary_exc,
            )
            stream = self._client.chat(
                model=self._fallback,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                options={"num_predict": 2048},
            )
            for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content

    def is_ready(self) -> bool:
        try:
            models_response = self._client.list()
            available = [
                m.get("name", m.get("model", ""))
                for m in models_response.get("models", [])
            ]
            def match_model(model_name: str) -> bool:
                prefix = model_name.split(":")[0]
                return any(name.startswith(prefix) or model_name in name for name in available)
            primary_ok = match_model(self._model)
            fallback_ok = match_model(self._fallback)
            if primary_ok or fallback_ok:
                return True
            logger.warning(
                "Ollama running but no suitable models. Available: %s",
                available,
            )
            return False
        except Exception as exc:
            logger.debug("Ollama not reachable: %s", exc)
            return False

    def name(self) -> str:
        return f"ollama/{self._model}"

    def info(self) -> dict[str, Any]:
        available = []
        try:
            models_response = self._client.list()
            available = [
                m.get("name", m.get("model", ""))
                for m in models_response.get("models", [])
            ]
        except Exception:
            pass
        return {
            "type": "ollama",
            "host": self._host,
            "model": self._model,
            "fallback": self._fallback,
            "models_available": available,
        }


# ---------------------------------------------------------------------------
# External CLI backend
# ---------------------------------------------------------------------------


class ExternalCLIBackend(InferenceBackend):
    """Inference by shelling out to a system-installed AI CLI tool."""

    def __init__(self, tool: DetectedTool, timeout: int = 180) -> None:
        self._tool = tool
        self._timeout = timeout
        logger.info(
            "External CLI backend initialized: %s (%s)",
            tool.name,
            tool.command,
        )

    def generate(self, prompt: str, timeout: int = 180) -> str:
        args = [arg.replace("{prompt}", prompt) for arg in self._tool.invoke_args]
        cmd = [self._tool.command] + args
        logger.debug("Invoking: %s", " ".join(cmd[:2]) + " ...")

        effective_timeout = timeout or self._timeout
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                logger.error(
                    "CLI tool '%s' exited with code %d: %s",
                    self._tool.name,
                    result.returncode,
                    stderr,
                )
                raise RuntimeError(
                    f"CLI tool '{self._tool.name}' failed: {stderr or 'unknown error'}"
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"CLI tool '{self._tool.name}' timed out after {effective_timeout}s"
            )

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        args = [arg.replace("{prompt}", prompt) for arg in self._tool.invoke_args]
        cmd = [self._tool.command] + args
        logger.debug("Stream-invoking: %s", " ".join(cmd[:2]) + " ...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                logger.error(
                    "CLI tool '%s' stream exited with code %d: %s",
                    self._tool.name,
                    result.returncode,
                    stderr,
                )
                raise RuntimeError(
                    f"CLI tool '{self._tool.name}' failed: {stderr or 'unknown error'}"
                )
            yield result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"CLI tool '{self._tool.name}' timed out after {self._timeout}s"
            )

    def is_ready(self) -> bool:
        return _find_on_path(self._tool.name) is not None

    def name(self) -> str:
        return f"cli/{self._tool.name}"

    def info(self) -> dict[str, Any]:
        return {
            "type": "external_cli",
            "tool": self._tool.name,
            "command": self._tool.command,
            "description": self._tool.description,
            "available": self.is_ready(),
        }


# ---------------------------------------------------------------------------
# Auto-detection factory
# ---------------------------------------------------------------------------


def auto_select_backend(
    prefer_ollama: bool = False,
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "llama3.2",
    ollama_fallback: str = "mistral",
) -> InferenceBackend:
    """
    Scan for available inference backends and return the best one.

    Priority:
      1. External CLI tools (if any found) — faster, better quality
      2. Ollama (if reachable and has models)
      3. Fallback: Ollama even if not ready (user will see an error)

    Set *prefer_ollama=True* to skip CLI detection and always use Ollama.
    """
    if not prefer_ollama:
        cli_tools = detect_cli_tools()
        if cli_tools:
            logger.info(
                "Auto-selected external CLI backend: %s", cli_tools[0].name
            )
            return ExternalCLIBackend(tool=cli_tools[0])

    ollama_backend = OllamaBackend(
        host=ollama_host,
        model=ollama_model,
        fallback_model=ollama_fallback,
    )
    if ollama_backend.is_ready():
        logger.info("Auto-selected Ollama backend: %s", ollama_model)
    else:
        logger.warning(
            "Ollama not available. Using Ollama backend anyway "
            "(queries will fail until Ollama is started)."
        )
    return ollama_backend
