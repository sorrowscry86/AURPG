"""POST /sessions/{id}/turn — the hot path."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from aurpg.safety import detect_safety_command
from aurpg.server._settings import get_app_settings
from aurpg.server._store import get_client, get_session, set_session
from aurpg.server._utils import state_snapshot
from aurpg.server.schemas import SafetyEvent, TurnRequest, TurnResponse
from aurpg.session import load_session, run_turn, save_session

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _saves_dir() -> Path:
    return Path(get_app_settings().saves_dir)


def _get_or_load(session_id: str):
    session = get_session(session_id)
    if session is not None:
        return session
    session_dir = _saves_dir() / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = load_session(_saves_dir(), session_id)
        set_session(session_id, session)
        return session
    except (OSError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# Plain def — FastAPI runs this in a threadpool, keeping the LLM call off the event loop.
@router.post("/sessions/{session_id}/turn", response_model=TurnResponse)
def post_turn(session_id: str, body: TurnRequest) -> TurnResponse:
    if not _UUID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    session = _get_or_load(session_id)
    client = get_client()

    # Detect safety command before the turn so we can populate safety_event
    safety_cmd = detect_safety_command(body.player_input)

    try:
        new_sess, response = run_turn(session, body.player_input, client=client)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "engine_timeout", "message": str(exc)},
        ) from exc

    # Autosave after every turn
    try:
        save_session(new_sess, _saves_dir())
    except OSError:
        pass  # surfaced as a toast by the client; state remains in memory

    set_session(session_id, new_sess)

    safety_event: SafetyEvent | None = None
    if safety_cmd is not None:
        safety_event = SafetyEvent(command=safety_cmd.value, ooc_text=response.raw_text)

    return TurnResponse(
        raw_text=response.raw_text,
        options=response.options,
        ledger_block=response.ledger_block,
        state=state_snapshot(new_sess),
        safety_event=safety_event,
    )
