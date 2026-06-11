"""Session CRUD endpoints: GET /sessions, POST /sessions, GET /sessions/{id}/state, DELETE /sessions/{id}"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException

from aurpg.server._settings import SYSTEM_PROMPT_PATH, get_app_settings
from aurpg.server._store import get_session, remove_session, set_session
from aurpg.server._utils import state_snapshot
from aurpg.server.schemas import (
    SessionCreateResponse,
    SessionStateResponse,
    SessionSummary,
    ClockSnapshot,
    WizardConfigBody,
)
from aurpg.session import load_session, new_session, save_session
from aurpg.wizard import WizardConfig, config_to_state_xml, validate_config

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _saves_dir() -> Path:
    return Path(get_app_settings().saves_dir)


def _require_uuid(session_id: str) -> None:
    if not _UUID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")


def _get_or_load(session_id: str):
    """Return a session from the in-memory store, loading from disk if absent."""
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    saves = _saves_dir()
    saves.mkdir(parents=True, exist_ok=True)

    results: list[SessionSummary] = []
    for session_dir in sorted(saves.iterdir()):
        if not session_dir.is_dir():
            continue
        meta_path = session_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        turn_count = 0
        turns_path = session_dir / "turns.jsonl"
        if turns_path.exists():
            try:
                turn_count = sum(
                    1
                    for line in turns_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            except OSError:
                pass

        character_name: str | None = None
        session_id = meta.get("id", session_dir.name)
        in_mem = get_session(session_id)
        if in_mem:
            character_name = (
                in_mem.state.session_state.get("player_state", {}).get("character_name")
            )
        else:
            state_path = session_dir / "state.xml"
            if state_path.exists():
                try:
                    tree = ET.parse(str(state_path))
                    ps_elem = tree.getroot().find("session_state/player_state")
                    if ps_elem is not None:
                        character_name = ps_elem.get("character_name")
                except (ET.ParseError, OSError):
                    pass

        results.append(
            SessionSummary(
                id=session_id,
                model=meta.get("model", "unknown"),
                last_saved=meta.get("last_saved", ""),
                turn_count=turn_count,
                character_name=character_name,
            )
        )
    return results


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(body: WizardConfigBody) -> SessionCreateResponse:
    config = WizardConfig(
        title=body.title,
        genre=body.genre,
        tone=body.tone,
        canon_mode=body.canon_mode,
        character_name=body.character_name,
        edge=body.edge,
        heart=body.heart,
        iron=body.iron,
        shadow=body.shadow,
        wits=body.wits,
        load=body.load,
        safety=body.safety,
        orchestration_mode=body.orchestration_mode,
        initial_position=body.initial_position,
        initial_effect=body.initial_effect,
    )

    errors = validate_config(config)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    state_xml = config_to_state_xml(config)
    session_id = str(uuid.uuid4())
    saves = _saves_dir()
    session_dir = saves / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    state_path = session_dir / "state.xml"
    state_path.write_text(state_xml, encoding="utf-8")

    settings = get_app_settings()
    session = new_session(
        state_path,
        SYSTEM_PROMPT_PATH,
        model=settings.model,
        session_id=session_id,
    )
    save_session(session, saves)
    set_session(session_id, session)

    return SessionCreateResponse(session_id=session_id, state=state_snapshot(session))


@router.get("/sessions/{session_id}/state", response_model=SessionStateResponse)
def get_session_state(session_id: str) -> SessionStateResponse:
    _require_uuid(session_id)
    session = _get_or_load(session_id)

    ps = session.state.session_state.get("player_state", {})
    return SessionStateResponse(
        stress=int(ps.get("stress", 0)),
        momentum=int(ps.get("momentum", 2)),
        harm=ps.get("harm", "none"),
        clocks=[
            ClockSnapshot(
                id=c.get("id", ""),
                label=c.get("label", ""),
                clock_type=c.get("clock_type", "standard"),
                segments=int(c.get("segments", 4)),
                filled=int(c.get("filled", 0)),
            )
            for c in session.state.clocks
        ],
        turn_history=session.state.turn_history[-50:],
    )


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    _require_uuid(session_id)
    session_dir = _saves_dir() / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    remove_session(session_id)
    return {"deleted": True}
