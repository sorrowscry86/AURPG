"""Integration tests for the full AURPG session lifecycle.

Exercises the complete pipeline end-to-end using real in-process calls.
The LLM layer is mocked (no API key required); all other layers — wizard,
state manager, session, safety — run for real.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurpg.dice import ActionRoll, SquadRoll, make_rng, roll_action, roll_squad
from aurpg.llm import EngineResponse
from aurpg.session import (
    Session,
    build_recap_context,
    load_session,
    needs_recap,
    new_session,
    run_turn,
    save_session,
)
from aurpg.state.manager import rewind
from aurpg.validator import validate
from aurpg.wizard import WizardConfig, config_to_state_xml, validate_config

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_SYSTEM_PROMPT_PATH = _REPO_ROOT / "src" / "aurpg" / "prompts" / "aurpg_system_prompt_prototype.xml"
_TEST_MODEL = "claude-haiku-4-5-20251001"

_MINIMAL_CONFIG = WizardConfig(
    title="Iron Wastes",
    genre="dark fantasy",
    tone="grim",
    canon_mode="flexible_canon",
    character_name="Maren",
    edge=2,
    heart=2,
    iron=2,
    shadow=2,
    wits=2,
    load="normal",
    safety={
        "horror": "yellow",
        "health": "green",
        "relationships": "green",
        "social_issues": "green",
    },
    orchestration_mode="collaborative_consult",
    initial_position="risky",
    initial_effect="standard",
)

_FAKE_RESPONSE = EngineResponse(
    raw_text="The goblin lunges. Option A. Option B. Option C.",
    ledger_block="stress: 0→1",
    options=["Option A", "Option B", "Option C"],
    input_tokens=100,
    output_tokens=50,
)


def _fake_engine(*args, **kwargs) -> EngineResponse:
    return _FAKE_RESPONSE


def _write_state(tmp_path: Path) -> Path:
    """Write a minimal campaign state XML to tmp_path and return the path."""
    xml = config_to_state_xml(_MINIMAL_CONFIG)
    state_path = tmp_path / "state.xml"
    state_path.write_text(xml, encoding="utf-8")
    return state_path


# ---------------------------------------------------------------------------
# Test 1 — Wizard → session pipeline (no LLM)
# ---------------------------------------------------------------------------


def test_wizard_to_session_pipeline(tmp_path: Path) -> None:
    errors = validate_config(_MINIMAL_CONFIG)
    assert errors == []

    state_path = _write_state(tmp_path)

    validator_errors = validate(state_path)
    assert validator_errors == [], f"Validator errors: {validator_errors}"

    session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)

    assert session.state.turn_history == []
    assert session.model == _TEST_MODEL


# ---------------------------------------------------------------------------
# Test 2 — Ten-turn session with mocked LLM
# ---------------------------------------------------------------------------


def test_ten_turn_session_with_mocked_llm(tmp_path: Path) -> None:
    state_path = _write_state(tmp_path)
    session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)
    mock_client = MagicMock()

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        for i in range(10):
            session, _ = run_turn(session, f"action {i}", client=mock_client)

    assert len(session.state.turn_history) == 10

    expected_keys = {
        "player_input",
        "raw_response",
        "options",
        "ledger_block",
        "input_tokens",
        "output_tokens",
    }
    for turn in session.state.turn_history:
        assert expected_keys.issubset(turn.keys()), (
            f"Turn record missing keys. Have: {set(turn.keys())}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Save and resume
# ---------------------------------------------------------------------------


def test_save_and_resume(tmp_path: Path) -> None:
    state_path = _write_state(tmp_path)
    save_dir = tmp_path / "saves"
    session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)
    mock_client = MagicMock()

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        for i in range(5):
            session, _ = run_turn(session, f"action {i}", client=mock_client)

    save_session(session, save_dir)

    assert (save_dir / session.id / "state.xml").exists()
    assert (save_dir / session.id / "meta.json").exists()

    loaded_session = load_session(save_dir, session.id, _SYSTEM_PROMPT_PATH)

    assert loaded_session.id == session.id
    assert loaded_session.model == session.model
    assert loaded_session.recap_threshold == session.recap_threshold

    # turn_history is runtime-only; the loaded session starts empty
    assert loaded_session.state.turn_history == []

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        for i in range(5):
            loaded_session, _ = run_turn(loaded_session, f"resumed action {i}", client=mock_client)

    assert len(loaded_session.state.turn_history) == 5


# ---------------------------------------------------------------------------
# Test 4 — Safety interrupt stops LLM
# ---------------------------------------------------------------------------


def test_safety_interrupt_stops_llm(tmp_path: Path) -> None:
    state_path = _write_state(tmp_path)
    session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)
    mock_client = MagicMock()

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("call_engine_with_retry must not be called for safety commands")

    with patch("aurpg.session.call_engine_with_retry", side_effect=_should_not_be_called):
        new_sess, response = run_turn(session, "[X-Card] I need to stop", client=mock_client)

    assert response.raw_text.startswith("[OOC — Safety]")
    assert new_sess.state.session_state["safety_state"]["hard_stop"] is True


# ---------------------------------------------------------------------------
# Test 5 — needs_recap threshold
# ---------------------------------------------------------------------------


def test_needs_recap_threshold(tmp_path: Path) -> None:
    state_path = _write_state(tmp_path)
    base_session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)
    mock_client = MagicMock()

    session = Session(
        id=base_session.id,
        state=base_session.state,
        system_prompt=base_session.system_prompt,
        model=base_session.model,
        max_tokens=base_session.max_tokens,
        recap_threshold=3,
    )

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        session, _ = run_turn(session, "turn 1", client=mock_client)
        session, _ = run_turn(session, "turn 2", client=mock_client)

    assert not needs_recap(session)

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        session, _ = run_turn(session, "turn 3", client=mock_client)

    assert needs_recap(session)

    recap_text = build_recap_context(session)
    assert recap_text != ""
    lines = [ln for ln in recap_text.splitlines() if ln.strip()]
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# Test 6 — rewind removes turns
# ---------------------------------------------------------------------------


def test_rewind_removes_turns(tmp_path: Path) -> None:
    state_path = _write_state(tmp_path)
    session = new_session(state_path, _SYSTEM_PROMPT_PATH, model=_TEST_MODEL)
    mock_client = MagicMock()

    with patch("aurpg.session.call_engine_with_retry", side_effect=_fake_engine):
        for i in range(3):
            session, _ = run_turn(session, f"action {i}", client=mock_client)

    assert len(session.state.turn_history) == 3

    new_state = rewind(session.state, steps=2)
    assert len(new_state.turn_history) == 1


# ---------------------------------------------------------------------------
# Test 7 — Dice seeded determinism
# ---------------------------------------------------------------------------


def test_dice_seeded_determinism() -> None:
    rng1a = make_rng(seed=42)
    rng1b = make_rng(seed=42)

    roll_a = roll_action(attribute=2, bonuses=1, rng=rng1a)
    roll_b = roll_action(attribute=2, bonuses=1, rng=rng1b)

    assert isinstance(roll_a, ActionRoll)
    assert roll_a == roll_b

    rng2a = make_rng(seed=42)
    rng2b = make_rng(seed=42)

    squad_a = roll_squad(n=3, rng=rng2a)
    squad_b = roll_squad(n=3, rng=rng2b)

    assert isinstance(squad_a, SquadRoll)
    assert squad_a == squad_b
