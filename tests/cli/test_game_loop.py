"""Tests for aurpg.cli.game_loop."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurpg.llm import EngineResponse
from aurpg.session import Session, new_session

SAMPLE_STATE_XML = (
    Path(__file__).parent.parent.parent
    / "src" / "aurpg" / "prompts" / "examples" / "sample_campaign_state.xml"
)
SAMPLE_SYSTEM_PROMPT = (
    Path(__file__).parent.parent.parent
    / "src" / "aurpg" / "prompts" / "aurpg_system_prompt_prototype.xml"
)

_FAKE_RESPONSE = EngineResponse(
    raw_text="You move forward.\n1) Go north\n2) Search the room\n3) Rest",
    ledger_block=None,
    options=["Go north", "Search the room", "Rest"],
    input_tokens=50,
    output_tokens=30,
)


@pytest.fixture
def session():
    return new_session(SAMPLE_STATE_XML, SAMPLE_SYSTEM_PROMPT, model="claude-haiku-4-5-20251001")


@pytest.fixture
def mock_client():
    return MagicMock()


class TestPlaySessionQuit:
    def test_quit_saves_session(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("builtins.input", side_effect=["/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        assert (tmp_path / session.id / "meta.json").exists()

    def test_quit_exits_without_calling_run_turn(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("builtins.input", side_effect=["/quit"]), \
             patch("aurpg.cli.game_loop.run_turn") as mock_run:
            play_session(session, save_dir=tmp_path, client=mock_client)
        mock_run.assert_not_called()


class TestPlaySessionTurn:
    def test_single_turn_calls_run_turn(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("aurpg.cli.game_loop.run_turn", return_value=(session, _FAKE_RESPONSE)) as mock_run, \
             patch("builtins.input", side_effect=["I look around.", "/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        mock_run.assert_called_once()

    def test_empty_input_skipped(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("aurpg.cli.game_loop.run_turn", return_value=(session, _FAKE_RESPONSE)) as mock_run, \
             patch("builtins.input", side_effect=["", "   ", "/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        mock_run.assert_not_called()

    def test_autosave_after_turn(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("aurpg.cli.game_loop.run_turn", return_value=(session, _FAKE_RESPONSE)), \
             patch("builtins.input", side_effect=["I act.", "/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        assert (tmp_path / session.id / "turns.jsonl").exists()


class TestPlaySessionMetaCommands:
    def test_sheet_command_does_not_call_run_turn(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("aurpg.cli.game_loop.run_turn") as mock_run, \
             patch("builtins.input", side_effect=["/sheet", "/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        mock_run.assert_not_called()

    def test_help_command_does_not_call_run_turn(self, session, mock_client, tmp_path):
        from aurpg.cli.game_loop import play_session
        with patch("aurpg.cli.game_loop.run_turn") as mock_run, \
             patch("builtins.input", side_effect=["/help", "/quit"]):
            play_session(session, save_dir=tmp_path, client=mock_client)
        mock_run.assert_not_called()


class TestPlaySessionRecap:
    def test_recap_injected_when_threshold_reached(self, session, mock_client, tmp_path):
        import copy
        from aurpg.cli.game_loop import play_session
        state = copy.deepcopy(session.state)
        for i in range(session.recap_threshold):
            state.turn_history.append({"player_input": f"t{i}", "raw_response": "r"})
        long_session = Session(
            id=session.id, state=state, system_prompt=session.system_prompt,
            model=session.model, system_prompt_path=session.system_prompt_path,
        )
        captured: list[str] = []

        def fake_run(sess, player_input, *, client):
            captured.append(player_input)
            return sess, _FAKE_RESPONSE

        with patch("aurpg.cli.game_loop.run_turn", side_effect=fake_run), \
             patch("builtins.input", side_effect=["I act.", "/quit"]):
            play_session(long_session, save_dir=tmp_path, client=mock_client)

        assert len(captured) == 1
        assert len(captured[0]) > len("I act.")  # recap was prepended


class TestPlaySessionHardStop:
    def test_hard_stop_exits_without_reading_input(self, session, mock_client, tmp_path):
        import copy
        from aurpg.cli.game_loop import play_session

        state = copy.deepcopy(session.state)
        state.session_state.setdefault("safety_state", {})["hard_stop"] = "true"
        hard_stopped = Session(
            id=session.id,
            state=state,
            system_prompt=session.system_prompt,
            model=session.model,
            system_prompt_path=session.system_prompt_path,
        )

        with patch("aurpg.cli.game_loop.run_turn") as mock_run, \
             patch("builtins.input") as mock_input:
            play_session(hard_stopped, save_dir=tmp_path, client=mock_client)

        mock_run.assert_not_called()
        mock_input.assert_not_called()
        assert (tmp_path / session.id / "meta.json").exists()
