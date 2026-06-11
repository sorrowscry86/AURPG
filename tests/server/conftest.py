"""Shared fixtures for server endpoint tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from aurpg.server.app import app
from aurpg.server._settings import AppSettings

_MINIMAL_BODY: dict = {
    "title": "Iron Wastes",
    "genre": "dark fantasy",
    "tone": "grim",
    "canon_mode": "flexible_canon",
    "character_name": "Maren",
    "edge": 2,
    "heart": 2,
    "iron": 2,
    "shadow": 2,
    "wits": 2,
    "load": "normal",
    "safety": {
        "horror": "yellow",
        "health": "green",
        "relationships": "green",
        "social_issues": "green",
    },
    "orchestration_mode": "collaborative_consult",
    "initial_position": "risky",
    "initial_effect": "standard",
}

@pytest.fixture(autouse=True)
def _reset_store():
    """Clear in-memory session store and client cache between tests."""
    import aurpg.server._store as _store

    _store._sessions.clear()
    _store._client = None
    yield
    _store._sessions.clear()
    _store._client = None


@pytest.fixture
def patched_settings(tmp_path, monkeypatch):
    """Override app settings to use an isolated tmp_path for saves."""
    import aurpg.server._settings as _settings

    settings = AppSettings(
        provider="anthropic",
        api_key="sk-test-key",
        model="claude-haiku-4-5-20251001",
        saves_dir=str(tmp_path / "saves"),
        port=8000,
    )
    monkeypatch.setattr(_settings, "_current", settings)
    monkeypatch.setattr(_settings, "_persist", lambda *_: None)
    return settings


@pytest.fixture
async def client(patched_settings):
    """Async HTTP client pointed at the in-process FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def fake_client():
    """A mock LLM client that never makes real network calls."""
    return MagicMock()


@pytest.fixture
async def session_id(client):
    """Create a session via the API and return its ID."""
    resp = await client.post("/sessions", json=_MINIMAL_BODY)
    assert resp.status_code == 201
    return resp.json()["session_id"]
