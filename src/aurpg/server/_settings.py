"""Server configuration — loads from ~/.aurpg/settings.json with env var fallbacks."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

_SETTINGS_FILE: Path = Path.home() / ".aurpg" / "settings.json"

_PACKAGE_DIR: Path = Path(__file__).parent.parent
SYSTEM_PROMPT_PATH: Path = (
    _PACKAGE_DIR / "prompts" / "aurpg_system_prompt_prototype.xml"
)


# ---------------------------------------------------------------------------
# Settings model
# ---------------------------------------------------------------------------


class AppSettings(BaseModel):
    provider: str = "anthropic"
    api_key: str = ""
    model: str = "claude-haiku-4-5-20251001"
    saves_dir: str = str(Path.home() / ".aurpg" / "saves")
    port: int = 8000


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

def _env_defaults() -> dict:
    """Build defaults from environment variables."""
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    anth_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if or_key:
        provider = "openrouter"
        api_key = or_key
        model = os.environ.get("AURPG_MODEL", "anthropic/claude-haiku-4-5-20251001")
    else:
        provider = "anthropic"
        api_key = anth_key
        model = os.environ.get("AURPG_MODEL", "claude-haiku-4-5-20251001")
    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "saves_dir": os.environ.get(
            "AURPG_SAVES_DIR", str(Path.home() / ".aurpg" / "saves")
        ),
        "port": int(os.environ.get("AURPG_PORT", "8000")),
    }


def _load() -> AppSettings:
    base = _env_defaults()
    if _SETTINGS_FILE.exists():
        try:
            stored = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            base.update({k: v for k, v in stored.items() if k in AppSettings.model_fields})
        except Exception:
            pass
    return AppSettings(**base)


_current: AppSettings = _load()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_app_settings() -> AppSettings:
    return _current


def update_app_settings(**kwargs) -> AppSettings:
    global _current
    data = {**_current.model_dump(), **{k: v for k, v in kwargs.items() if v is not None}}
    _current = AppSettings(**data)
    _persist(_current)
    return _current


def _persist(settings: AppSettings) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(
        json.dumps(settings.model_dump(), indent=2), encoding="utf-8"
    )
