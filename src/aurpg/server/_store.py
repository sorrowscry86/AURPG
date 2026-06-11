"""In-memory session store and LLM client cache."""

from __future__ import annotations

from aurpg.session import Session

_sessions: dict[str, Session] = {}
_client = None


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def set_session(session_id: str, session: Session) -> None:
    _sessions[session_id] = session


def remove_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# LLM client cache
# ---------------------------------------------------------------------------


def get_client():
    """Return the cached LLM client, creating it from current settings if needed."""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def invalidate_client() -> None:
    """Force the next ``get_client()`` call to create a fresh client."""
    global _client
    _client = None


def _make_client():
    from aurpg.llm import make_client  # noqa: PLC0415
    from aurpg.server._settings import get_app_settings  # noqa: PLC0415

    s = get_app_settings()
    return make_client(api_key=s.api_key or None, provider=s.provider)
