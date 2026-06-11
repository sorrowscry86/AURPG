"""Pydantic request/response models for the AURPG server."""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared state shapes
# ---------------------------------------------------------------------------


class ClockSnapshot(BaseModel):
    id: str
    label: str
    clock_type: str
    segments: int
    filled: int


class StateSnapshot(BaseModel):
    stress: int
    momentum: int
    harm: str
    clocks: list[ClockSnapshot]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class WizardConfigBody(BaseModel):
    # Stage 1 — System
    title: str
    genre: str
    tone: str
    canon_mode: str

    # Stage 2 — Character
    character_name: str
    edge: int
    heart: int
    iron: int
    shadow: int
    wits: int
    load: str

    # Stage 3 — Safety
    safety: dict[str, str]
    orchestration_mode: str

    # Stage 4 — Orchestration
    initial_position: str
    initial_effect: str


class SessionSummary(BaseModel):
    id: str
    model: str
    last_saved: str
    turn_count: int
    character_name: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    state: StateSnapshot


class SessionStateResponse(BaseModel):
    stress: int
    momentum: int
    harm: str
    clocks: list[ClockSnapshot]
    turn_history: list[dict]


# ---------------------------------------------------------------------------
# Turns
# ---------------------------------------------------------------------------


class TurnRequest(BaseModel):
    player_input: str


class SafetyEvent(BaseModel):
    command: str
    ooc_text: str


class TurnResponse(BaseModel):
    raw_text: str
    options: list[str]
    ledger_block: str | None
    state: StateSnapshot
    safety_event: SafetyEvent | None


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class SettingsResponse(BaseModel):
    provider: str
    api_key_set: bool
    api_key_preview: str
    model: str
    saves_dir: str
    port: int


class SettingsUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    model: str | None = None
    saves_dir: str | None = None
    port: int | None = None


class ModelInfo(BaseModel):
    id: str
    name: str
    context_length: int
    provider: str


class ModelsResponse(BaseModel):
    provider: str
    models: list[ModelInfo]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
