"""Tests for aurpg.cli.renderer — pure formatting functions."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aurpg.state.manager import load_state

SAMPLE_XML = (
    Path(__file__).parent.parent.parent
    / "src" / "aurpg" / "prompts" / "examples" / "sample_campaign_state.xml"
)


@pytest.fixture
def state():
    return load_state(SAMPLE_XML)


class TestRenderLedger:
    def test_returns_string(self, state):
        from aurpg.cli.renderer import render_ledger
        assert isinstance(render_ledger(state), str)

    def test_contains_stress_value(self, state):
        from aurpg.cli.renderer import render_ledger
        # sample has stress=4
        assert "4" in render_ledger(state)

    def test_contains_momentum_value(self, state):
        from aurpg.cli.renderer import render_ledger
        # sample has momentum=6
        assert "6" in render_ledger(state)

    def test_contains_harm(self, state):
        from aurpg.cli.renderer import render_ledger
        assert "bruised" in render_ledger(state)

    def test_contains_clock_id(self, state):
        from aurpg.cli.renderer import render_ledger
        result = render_ledger(state)
        assert any(c["id"] in result for c in state.clocks)

    def test_contains_position(self, state):
        from aurpg.cli.renderer import render_ledger
        assert "risky" in render_ledger(state)

    def test_contains_track_id(self, state):
        from aurpg.cli.renderer import render_ledger
        if not state.progress_tracks:
            pytest.skip("no progress tracks in sample")
        result = render_ledger(state)
        assert any(t["id"] in result for t in state.progress_tracks)

    def test_track_ticks_computed_correctly(self, state):
        from aurpg.cli.renderer import render_ledger
        if not state.progress_tracks:
            pytest.skip("no progress tracks in sample")
        # verify at least one track renders with a numeric ticks value in "N/40" format
        result = render_ledger(state)
        import re
        assert re.search(r"\d+/40", result), "Expected 'N/40' ticks format in ledger"


class TestRenderCharacterSheet:
    def test_returns_string(self, state):
        from aurpg.cli.renderer import render_character_sheet
        assert isinstance(render_character_sheet(state), str)

    def test_contains_character_name(self, state):
        from aurpg.cli.renderer import render_character_sheet
        assert "Mara Voss" in render_character_sheet(state)

    def test_contains_all_attribute_names(self, state):
        from aurpg.cli.renderer import render_character_sheet
        result = render_character_sheet(state)
        for attr in ("edge", "heart", "iron", "shadow", "wits"):
            assert attr in result

    def test_contains_inventory_item(self, state):
        from aurpg.cli.renderer import render_character_sheet
        assert "signal_scrambler" in render_character_sheet(state)

    def test_contains_npc_name(self, state):
        from aurpg.cli.renderer import render_character_sheet
        assert "Lattice" in render_character_sheet(state)


class TestRenderSafetyBanner:
    def test_empty_when_no_safety_active(self, state):
        from aurpg.cli.renderer import render_safety_banner
        # sample has hard_stop=false, pause=false
        assert render_safety_banner(state) == ""

    def test_banner_when_paused(self, state):
        from aurpg.cli.renderer import render_safety_banner
        paused = copy.deepcopy(state)
        paused.session_state["safety_state"]["pause"] = "true"
        result = render_safety_banner(paused)
        assert len(result) > 0
        assert "OOC" in result.upper() or "PAUSE" in result.upper()

    def test_banner_when_hard_stop(self, state):
        from aurpg.cli.renderer import render_safety_banner
        stopped = copy.deepcopy(state)
        stopped.session_state["safety_state"]["hard_stop"] = "true"
        result = render_safety_banner(stopped)
        assert len(result) > 0
        assert "STOP" in result.upper() or "FICTION" in result.upper()


class TestRenderOptions:
    def test_returns_string(self):
        from aurpg.cli.renderer import render_options
        assert isinstance(render_options(["A", "B", "C"]), str)

    def test_all_options_present(self):
        from aurpg.cli.renderer import render_options
        result = render_options(["Go north", "Search the room", "Call for help"])
        assert "Go north" in result
        assert "Search the room" in result
        assert "Call for help" in result

    def test_numbered(self):
        from aurpg.cli.renderer import render_options
        result = render_options(["Alpha", "Beta", "Gamma"])
        assert "1" in result and "2" in result and "3" in result

    def test_empty_list_returns_string(self):
        from aurpg.cli.renderer import render_options
        assert isinstance(render_options([]), str)
        assert len(render_options([])) > 0
