"""Tests for aurpg.session — session manager TDD suite.

All LLM client calls and file I/O are mocked.  No Anthropic API calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurpg.llm import EngineResponse
from aurpg.safety import SafetyCommand
from aurpg.state.manager import CampaignState, load_state
from aurpg.session import (
    Session,
    build_recap_context,
    load_session,
    needs_recap,
    new_session,
    run_turn,
    save_session,
)

# ---------------------------------------------------------------------------
# Paths — reuse the sample XML for integration-like tests
# ---------------------------------------------------------------------------

SAMPLE_STATE_XML = (
    Path(__file__).parent.parent
    / "src"
    / "aurpg"
    / "prompts"
    / "examples"
    / "sample_campaign_state.xml"
)

SAMPLE_SYSTEM_PROMPT = (
    Path(__file__).parent.parent
    / "src"
    / "aurpg"
    / "prompts"
    / "aurpg_system_prompt_prototype.xml"
)

TEST_MODEL = "claude-sonnet-4-5"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine_response(text: str = "Some narrative.\n1) Go left\n2) Go right\n3) Stay") -> EngineResponse:
    return EngineResponse(
        raw_text=text,
        ledger_block=None,
        options=["Go left", "Go right", "Stay"],
        input_tokens=100,
        output_tokens=50,
    )


# ---------------------------------------------------------------------------
# new_session
# ---------------------------------------------------------------------------


class TestNewSession:
    def test_returns_session_instance(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert isinstance(session, Session)

    def test_state_is_campaign_state(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert isinstance(session.state, CampaignState)

    def test_system_prompt_is_string(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert isinstance(session.system_prompt, str)
        assert len(session.system_prompt) > 0

    def test_system_prompt_loaded_from_file(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        expected_text = SAMPLE_SYSTEM_PROMPT.read_text(encoding="utf-8")
        assert session.system_prompt == expected_text

    def test_model_stored_on_session(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert session.model == TEST_MODEL

    def test_generates_uuid_when_no_session_id(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert isinstance(session.id, str)
        assert len(session.id) == 36  # standard UUID hyphenated form
        # basic UUID format check
        parts = session.id.split("-")
        assert len(parts) == 5

    def test_uses_provided_session_id(self):
        custom_id = "my-custom-id-abc"
        session = new_session(
            SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL, session_id=custom_id
        )
        assert session.id == custom_id

    def test_different_calls_generate_different_uuids(self):
        s1 = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        s2 = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert s1.id != s2.id

    def test_default_max_tokens(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert session.max_tokens == 1024

    def test_default_recap_threshold(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert session.recap_threshold == 20


# ---------------------------------------------------------------------------
# run_turn — normal (no safety command)
# ---------------------------------------------------------------------------


class TestRunTurnNormal:
    @pytest.fixture
    def session(self):
        return new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    def test_returns_tuple_of_session_and_engine_response(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            result = run_turn(session, "I draw my sword.", client=mock_client)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_updated_session(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            new_sess, _ = run_turn(session, "I draw my sword.", client=mock_client)
        assert isinstance(new_sess, Session)

    def test_returns_engine_response(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            _, response = run_turn(session, "I draw my sword.", client=mock_client)
        assert isinstance(response, EngineResponse)

    def test_calls_llm_once(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng) as mock_llm:
            run_turn(session, "I draw my sword.", client=mock_client)
        mock_llm.assert_called_once()

    def test_appends_turn_to_history(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            new_sess, _ = run_turn(session, "I draw my sword.", client=mock_client)
        assert len(new_sess.state.turn_history) == 1

    def test_original_session_not_mutated(self, session, mock_client):
        original_history_len = len(session.state.turn_history)
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            run_turn(session, "I draw my sword.", client=mock_client)
        assert len(session.state.turn_history) == original_history_len

    def test_llm_receives_model_from_session(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng) as mock_llm:
            run_turn(session, "I draw my sword.", client=mock_client)
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["model"] == TEST_MODEL

    def test_llm_receives_max_tokens_from_session(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng) as mock_llm:
            run_turn(session, "I draw my sword.", client=mock_client)
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["max_tokens"] == session.max_tokens

    def test_llm_receives_client(self, session, mock_client):
        eng = _make_engine_response()
        with patch("aurpg.session.call_engine_with_retry", return_value=eng) as mock_llm:
            run_turn(session, "I draw my sword.", client=mock_client)
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["client"] is mock_client

    def test_response_raw_text_matches_llm_output(self, session, mock_client):
        eng = _make_engine_response("The blade sings.\n1) A\n2) B\n3) C")
        with patch("aurpg.session.call_engine_with_retry", return_value=eng):
            _, response = run_turn(session, "I draw my sword.", client=mock_client)
        assert "The blade sings." in response.raw_text

    def test_run_turn_propagates_llm_exception(self, session, mock_client):
        original_history_len = len(session.state.turn_history)
        with patch(
            "aurpg.session.call_engine_with_retry", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError, match="boom"):
                run_turn(session, "I do something.", client=mock_client)
        # Session state must be unchanged after the exception
        assert len(session.state.turn_history) == original_history_len


# ---------------------------------------------------------------------------
# run_turn — safety command path
# ---------------------------------------------------------------------------


class TestRunTurnSafety:
    @pytest.fixture
    def session(self):
        return new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    def test_safety_command_detected_prevents_llm_call(self, session, mock_client):
        with patch("aurpg.session.call_engine_with_retry") as mock_llm:
            run_turn(session, "[X-Card]", client=mock_client)
        mock_llm.assert_not_called()

    def test_safety_returns_ooc_response(self, session, mock_client):
        _, response = run_turn(session, "[X-Card]", client=mock_client)
        assert "[OOC" in response.raw_text

    def test_safety_response_has_empty_options(self, session, mock_client):
        _, response = run_turn(session, "[X-Card]", client=mock_client)
        assert response.options == []

    def test_safety_response_has_none_ledger(self, session, mock_client):
        _, response = run_turn(session, "[X-Card]", client=mock_client)
        assert response.ledger_block is None

    def test_safety_updates_session_state(self, session, mock_client):
        new_sess, _ = run_turn(session, "[X-Card]", client=mock_client)
        safety_state = new_sess.state.session_state.get("safety_state", {})
        assert safety_state.get("hard_stop") == "true"

    def test_pause_command_does_not_call_llm(self, session, mock_client):
        with patch("aurpg.session.call_engine_with_retry") as mock_llm:
            run_turn(session, "[Pause]", client=mock_client)
        mock_llm.assert_not_called()

    def test_rewind_command_does_not_call_llm(self, session, mock_client):
        with patch("aurpg.session.call_engine_with_retry") as mock_llm:
            run_turn(session, "[Rewind]", client=mock_client)
        mock_llm.assert_not_called()

    def test_hard_stop_command_does_not_call_llm(self, session, mock_client):
        with patch("aurpg.session.call_engine_with_retry") as mock_llm:
            run_turn(session, "!enforce_hard_stop", client=mock_client)
        mock_llm.assert_not_called()

    def test_safety_response_input_tokens_zero(self, session, mock_client):
        _, response = run_turn(session, "[X-Card]", client=mock_client)
        assert response.input_tokens == 0

    def test_safety_response_output_tokens_zero(self, session, mock_client):
        _, response = run_turn(session, "[X-Card]", client=mock_client)
        assert response.output_tokens == 0


# ---------------------------------------------------------------------------
# save_session / load_session
# ---------------------------------------------------------------------------


class TestSaveSession:
    def test_save_creates_state_xml(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        state_path = tmp_path / session.id / "state.xml"
        assert state_path.exists()

    def test_save_creates_meta_json(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        meta_path = tmp_path / session.id / "meta.json"
        assert meta_path.exists()

    def test_save_returns_session_directory(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        result = save_session(session, tmp_path)
        assert result == tmp_path / session.id

    def test_meta_json_contains_id(self, tmp_path):
        session = new_session(
            SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL, session_id="test-id-xyz"
        )
        save_session(session, tmp_path)
        meta = json.loads((tmp_path / session.id / "meta.json").read_text(encoding="utf-8"))
        assert meta["id"] == "test-id-xyz"

    def test_meta_json_contains_model(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        meta = json.loads((tmp_path / session.id / "meta.json").read_text(encoding="utf-8"))
        assert meta["model"] == TEST_MODEL

    def test_meta_json_contains_max_tokens(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        meta = json.loads((tmp_path / session.id / "meta.json").read_text(encoding="utf-8"))
        assert meta["max_tokens"] == 1024

    def test_meta_json_contains_recap_threshold(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        meta = json.loads((tmp_path / session.id / "meta.json").read_text(encoding="utf-8"))
        assert meta["recap_threshold"] == 20

    def test_state_xml_is_valid_xml(self, tmp_path):
        from xml.etree import ElementTree as ET

        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        state_path = tmp_path / session.id / "state.xml"
        # Should not raise
        ET.parse(str(state_path))

    def test_save_creates_parent_directories(self, tmp_path):
        nested_dir = tmp_path / "deep" / "nested" / "saves"
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, nested_dir)
        assert (nested_dir / session.id / "meta.json").exists()


class TestLoadSession:
    def test_load_returns_session(self, tmp_path):
        session = new_session(
            SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL, session_id="abc-123"
        )
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, "abc-123", SAMPLE_SYSTEM_PROMPT)
        assert isinstance(loaded, Session)

    def test_load_restores_session_id(self, tmp_path):
        session = new_session(
            SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL, session_id="abc-123"
        )
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, "abc-123", SAMPLE_SYSTEM_PROMPT)
        assert loaded.id == "abc-123"

    def test_load_restores_model(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        assert loaded.model == TEST_MODEL

    def test_load_restores_max_tokens(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        assert loaded.max_tokens == session.max_tokens

    def test_load_restores_recap_threshold(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        assert loaded.recap_threshold == session.recap_threshold

    def test_load_restores_system_prompt(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        assert loaded.system_prompt == session.system_prompt

    def test_load_state_is_campaign_state(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        assert isinstance(loaded.state, CampaignState)

    def test_roundtrip_preserves_session_state_keys(self, tmp_path):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        original_keys = set(session.state.session_state.keys())
        save_session(session, tmp_path)
        loaded = load_session(tmp_path, session.id, SAMPLE_SYSTEM_PROMPT)
        loaded_keys = set(loaded.state.session_state.keys())
        assert original_keys == loaded_keys


# ---------------------------------------------------------------------------
# needs_recap
# ---------------------------------------------------------------------------


class TestNeedsRecap:
    def test_false_when_history_is_empty(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        assert not needs_recap(session)

    def test_false_when_below_threshold(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        # Add 19 turns (threshold is 20)
        from aurpg.state.manager import append_turn

        state = session.state
        for i in range(19):
            state = append_turn(state, {"turn": i})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        assert not needs_recap(session)

    def test_true_when_at_threshold(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = session.state
        for i in range(20):
            state = append_turn(state, {"turn": i})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        assert needs_recap(session)

    def test_true_when_above_threshold(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = session.state
        for i in range(25):
            state = append_turn(state, {"turn": i})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        assert needs_recap(session)

    def test_custom_recap_threshold(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = session.state
        for i in range(5):
            state = append_turn(state, {"turn": i})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=5,  # custom lower threshold
        )
        assert needs_recap(session)


# ---------------------------------------------------------------------------
# build_recap_context
# ---------------------------------------------------------------------------


class TestBuildRecapContext:
    def test_returns_string(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        result = build_recap_context(session)
        assert isinstance(result, str)

    def test_empty_history_returns_empty_or_short_string(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        result = build_recap_context(session)
        # Should be a string (possibly empty or a placeholder for no turns)
        assert isinstance(result, str)

    def test_returns_nonempty_string_when_turns_exist(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = append_turn(session.state, {"player_input": "I draw my sword.", "response": "Steel rings."})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        result = build_recap_context(session)
        assert len(result) > 0

    def test_recap_contains_turn_data(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = append_turn(session.state, {"player_input": "unique-action-xyz"})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        result = build_recap_context(session)
        assert "unique-action-xyz" in result

    def test_recap_limits_to_last_5_turns(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = session.state
        for i in range(10):
            state = append_turn(state, {"turn_index": str(i), "player_input": f"action-{i}"})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        result = build_recap_context(session)
        # The first 5 turns (0-4) should NOT appear; the last 5 (5-9) should
        assert "action-9" in result
        assert "action-5" in result
        assert "action-0" not in result
        assert "action-4" not in result

    def test_recap_returns_json_lines(self):
        session = new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model=TEST_MODEL)
        from aurpg.state.manager import append_turn

        state = append_turn(session.state, {"player_input": "I look around."})
        session = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
        )
        result = build_recap_context(session)
        # Each line should be parseable JSON
        lines = [ln for ln in result.splitlines() if ln.strip()]
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
