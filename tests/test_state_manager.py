"""Tests for aurpg.state.manager — TDD suite covering load, mutate, persist, rewind."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aurpg.safety import SafetyCommand
from aurpg.state.manager import (
    CampaignState,
    StateError,
    append_turn,
    apply_safety,
    load_state,
    rewind,
    save_state,
    set_momentum,
    set_stress,
    tick_clock,
)

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

SAMPLE_XML = (
    Path(__file__).parent.parent
    / "src"
    / "aurpg"
    / "prompts"
    / "examples"
    / "sample_campaign_state.xml"
)


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------


class TestLoadState:
    def test_load_valid_xml_returns_campaign_state(self):
        state = load_state(SAMPLE_XML)
        assert isinstance(state, CampaignState)
        assert state.path == SAMPLE_XML

    def test_load_populates_session_state(self):
        state = load_state(SAMPLE_XML)
        assert "campaign" in state.session_state
        assert "player_state" in state.session_state
        assert state.session_state["campaign"]["id"] == "camp-neon-ash-01"

    def test_load_populates_clocks(self):
        state = load_state(SAMPLE_XML)
        assert len(state.clocks) == 8
        ids = {c["id"] for c in state.clocks}
        assert "clk-mission-archive-extraction" in ids

    def test_load_populates_progress_tracks(self):
        state = load_state(SAMPLE_XML)
        assert len(state.progress_tracks) == 2
        assert state.progress_tracks[0]["id"] == "trk-clear-name"

    def test_load_populates_safety_profile(self):
        state = load_state(SAMPLE_XML)
        assert len(state.safety_profile) == 4
        names = {c["name"] for c in state.safety_profile}
        assert "horror" in names

    def test_load_turn_history_starts_empty(self):
        state = load_state(SAMPLE_XML)
        assert state.turn_history == []

    def test_load_populates_resources(self):
        state = load_state(SAMPLE_XML)
        assert "attributes" in state.resources
        assert isinstance(state.resources["attributes"], list)
        assert len(state.resources["attributes"]) == 5

    def test_load_resources_attribute_values(self):
        state = load_state(SAMPLE_XML)
        edge = next(a for a in state.resources["attributes"] if a["name"] == "edge")
        assert edge["value"] == "3"

    def test_load_resources_inventory(self):
        state = load_state(SAMPLE_XML)
        items = state.resources.get("inventory", [])
        names = [i["name"] for i in items]
        assert "signal_scrambler" in names

    def test_load_invalid_xml_raises_state_error(self, tmp_path: Path):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("<not_valid_aurpg />")
        with pytest.raises(StateError, match="Validation failed"):
            load_state(bad_xml)

    def test_load_missing_file_raises_state_error(self, tmp_path: Path):
        missing = tmp_path / "missing.xml"
        with pytest.raises(StateError):
            load_state(missing)

    def test_load_malformed_xml_raises_state_error(self, tmp_path: Path):
        bad_xml = tmp_path / "malformed.xml"
        bad_xml.write_text("<unclosed>")
        with pytest.raises(StateError):
            load_state(bad_xml)


# ---------------------------------------------------------------------------
# tick_clock
# ---------------------------------------------------------------------------


class TestTickClock:
    def test_tick_advances_filled_by_one(self):
        state = load_state(SAMPLE_XML)
        # clk-danger-alarm-sweep starts at filled=3, segments=6
        new_state = tick_clock(state, "clk-danger-alarm-sweep")
        clock = next(c for c in new_state.clocks if c["id"] == "clk-danger-alarm-sweep")
        assert clock["filled"] == "4"

    def test_tick_advances_by_custom_amount(self):
        state = load_state(SAMPLE_XML)
        new_state = tick_clock(state, "clk-danger-alarm-sweep", amount=2)
        clock = next(c for c in new_state.clocks if c["id"] == "clk-danger-alarm-sweep")
        assert clock["filled"] == "5"

    def test_tick_caps_at_segments(self):
        state = load_state(SAMPLE_XML)
        # clk-mission-archive-extraction: segments=8, filled=5; advance by 99
        new_state = tick_clock(state, "clk-mission-archive-extraction", amount=99)
        clock = next(
            c for c in new_state.clocks if c["id"] == "clk-mission-archive-extraction"
        )
        assert clock["filled"] == "8"

    def test_tick_raises_on_unknown_id(self):
        state = load_state(SAMPLE_XML)
        with pytest.raises(StateError, match="not found"):
            tick_clock(state, "clk-does-not-exist")

    def test_tick_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        original_clocks = copy.deepcopy(state.clocks)
        tick_clock(state, "clk-danger-alarm-sweep")
        assert state.clocks == original_clocks

    def test_tick_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        new_state = tick_clock(state, "clk-danger-alarm-sweep")
        assert new_state is not state

    def test_tick_other_clocks_unchanged(self):
        state = load_state(SAMPLE_XML)
        new_state = tick_clock(state, "clk-danger-alarm-sweep")
        original_mission = next(
            c for c in state.clocks if c["id"] == "clk-mission-archive-extraction"
        )
        new_mission = next(
            c for c in new_state.clocks if c["id"] == "clk-mission-archive-extraction"
        )
        assert new_mission["filled"] == original_mission["filled"]

    def test_tick_clock_negative_amount_clamps_to_zero(self):
        state = load_state(SAMPLE_XML)
        # clk-danger-alarm-sweep starts at filled=3; subtracting 99 must not go below 0
        new_state = tick_clock(state, "clk-danger-alarm-sweep", amount=-99)
        clock = next(c for c in new_state.clocks if c["id"] == "clk-danger-alarm-sweep")
        assert clock["filled"] == "0"

    def test_tick_clock_zero_amount_is_noop(self):
        state = load_state(SAMPLE_XML)
        original_clock = next(
            c for c in state.clocks if c["id"] == "clk-danger-alarm-sweep"
        )
        original_filled = original_clock["filled"]
        new_state = tick_clock(state, "clk-danger-alarm-sweep", amount=0)
        clock = next(c for c in new_state.clocks if c["id"] == "clk-danger-alarm-sweep")
        assert clock["filled"] == original_filled


# ---------------------------------------------------------------------------
# set_stress
# ---------------------------------------------------------------------------


class TestSetStress:
    def test_set_stress_updates_value(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, 7)
        assert new_state.session_state["player_state"]["stress"] == "7"

    def test_set_stress_clamps_above_ten(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, 99)
        assert new_state.session_state["player_state"]["stress"] == "10"

    def test_set_stress_clamps_below_zero(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, -5)
        assert new_state.session_state["player_state"]["stress"] == "0"

    def test_set_stress_exact_boundary_zero(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, 0)
        assert new_state.session_state["player_state"]["stress"] == "0"

    def test_set_stress_exact_boundary_ten(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, 10)
        assert new_state.session_state["player_state"]["stress"] == "10"

    def test_set_stress_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        original_stress = state.session_state["player_state"]["stress"]
        set_stress(state, 9)
        assert state.session_state["player_state"]["stress"] == original_stress

    def test_set_stress_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        new_state = set_stress(state, 5)
        assert new_state is not state


# ---------------------------------------------------------------------------
# set_momentum
# ---------------------------------------------------------------------------


class TestSetMomentum:
    def test_set_momentum_updates_value(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, 3)
        assert new_state.session_state["player_state"]["momentum"] == "3"

    def test_set_momentum_clamps_above_ten(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, 99)
        assert new_state.session_state["player_state"]["momentum"] == "10"

    def test_set_momentum_clamps_below_minus_six(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, -99)
        assert new_state.session_state["player_state"]["momentum"] == "-6"

    def test_set_momentum_exact_boundary_minus_six(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, -6)
        assert new_state.session_state["player_state"]["momentum"] == "-6"

    def test_set_momentum_exact_boundary_ten(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, 10)
        assert new_state.session_state["player_state"]["momentum"] == "10"

    def test_set_momentum_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        original = state.session_state["player_state"]["momentum"]
        set_momentum(state, -3)
        assert state.session_state["player_state"]["momentum"] == original

    def test_set_momentum_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        new_state = set_momentum(state, 0)
        assert new_state is not state


# ---------------------------------------------------------------------------
# apply_safety
# ---------------------------------------------------------------------------


class TestApplySafety:
    def test_pause_sets_pause_and_intensity_check(self):
        state = load_state(SAMPLE_XML)
        new_state = apply_safety(state, SafetyCommand.PAUSE)
        ss = new_state.session_state["safety_state"]
        assert ss["pause"] == "true"
        assert ss["intensity_check"] == "pending"

    def test_x_card_sets_hard_stop_and_pause(self):
        state = load_state(SAMPLE_XML)
        new_state = apply_safety(state, SafetyCommand.X_CARD)
        ss = new_state.session_state["safety_state"]
        assert ss["hard_stop"] == "true"
        assert ss["pause"] == "true"
        assert ss["intensity_check"] == "pending"

    def test_hard_stop_sets_hard_stop(self):
        state = load_state(SAMPLE_XML)
        new_state = apply_safety(state, SafetyCommand.HARD_STOP)
        ss = new_state.session_state["safety_state"]
        assert ss["hard_stop"] == "true"

    def test_rewind_sets_intensity_check_only(self):
        state = load_state(SAMPLE_XML)
        new_state = apply_safety(state, SafetyCommand.REWIND)
        ss = new_state.session_state["safety_state"]
        assert ss["intensity_check"] == "pending"
        # hard_stop and pause should remain at original values from XML
        assert ss.get("hard_stop") == "false"
        assert ss.get("pause") == "false"

    def test_apply_safety_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        original = copy.deepcopy(state.session_state["safety_state"])
        apply_safety(state, SafetyCommand.HARD_STOP)
        assert state.session_state["safety_state"] == original

    def test_apply_safety_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        new_state = apply_safety(state, SafetyCommand.PAUSE)
        assert new_state is not state


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------


class TestSaveState:
    def test_save_writes_to_default_path(self, tmp_path: Path):
        state = load_state(SAMPLE_XML)
        target = tmp_path / "saved.xml"
        # Override path so we don't overwrite the fixture
        state = CampaignState(
            path=target,
            session_state=state.session_state,
            clocks=state.clocks,
            progress_tracks=state.progress_tracks,
            safety_profile=state.safety_profile,
            turn_history=state.turn_history,
        )
        returned = save_state(state)
        assert returned == target
        assert target.exists()

    def test_save_to_explicit_path(self, tmp_path: Path):
        state = load_state(SAMPLE_XML)
        target = tmp_path / "explicit.xml"
        returned = save_state(state, path=target)
        assert returned == target
        assert target.exists()

    def test_saved_xml_passes_validation(self, tmp_path: Path):
        from aurpg.validator import validate

        state = load_state(SAMPLE_XML)
        target = tmp_path / "roundtrip.xml"
        save_state(state, path=target)
        errors = validate(target)
        assert errors == [], f"Validation errors: {errors}"

    def test_save_preserves_clock_filled_value(self, tmp_path: Path):
        state = load_state(SAMPLE_XML)
        state = tick_clock(state, "clk-danger-alarm-sweep", amount=1)  # 3 → 4
        target = tmp_path / "mutated.xml"
        save_state(state, path=target)
        reloaded = load_state(target)
        clock = next(c for c in reloaded.clocks if c["id"] == "clk-danger-alarm-sweep")
        assert clock["filled"] == "4"

    def test_save_preserves_stress_value(self, tmp_path: Path):
        state = load_state(SAMPLE_XML)
        state = set_stress(state, 8)
        target = tmp_path / "stress.xml"
        save_state(state, path=target)
        reloaded = load_state(target)
        assert reloaded.session_state["player_state"]["stress"] == "8"


# ---------------------------------------------------------------------------
# append_turn
# ---------------------------------------------------------------------------


class TestAppendTurn:
    def test_append_adds_turn_to_history(self):
        state = load_state(SAMPLE_XML)
        turn = {"action": "face_danger", "roll": 8, "outcome": "weak_hit"}
        new_state = append_turn(state, turn)
        assert len(new_state.turn_history) == 1
        assert new_state.turn_history[0] == turn

    def test_append_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        append_turn(state, {"action": "test"})
        assert state.turn_history == []

    def test_append_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        new_state = append_turn(state, {"x": 1})
        assert new_state is not state

    def test_append_multiple_turns(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        state = append_turn(state, {"n": 2})
        state = append_turn(state, {"n": 3})
        assert len(state.turn_history) == 3
        assert [t["n"] for t in state.turn_history] == [1, 2, 3]

    def test_append_turn_is_deep_copied(self):
        state = load_state(SAMPLE_XML)
        mutable = {"data": [1, 2, 3]}
        new_state = append_turn(state, mutable)
        mutable["data"].append(99)  # mutate original after appending
        assert new_state.turn_history[0]["data"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# rewind
# ---------------------------------------------------------------------------


class TestRewind:
    def test_rewind_removes_last_entry(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        state = append_turn(state, {"n": 2})
        state = append_turn(state, {"n": 3})
        rewound = rewind(state, steps=1)
        assert len(rewound.turn_history) == 2
        assert rewound.turn_history[-1]["n"] == 2

    def test_rewind_multiple_steps(self):
        state = load_state(SAMPLE_XML)
        for i in range(5):
            state = append_turn(state, {"n": i})
        rewound = rewind(state, steps=3)
        assert len(rewound.turn_history) == 2
        assert [t["n"] for t in rewound.turn_history] == [0, 1]

    def test_rewind_clears_all_if_steps_exceeds_history(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        rewound = rewind(state, steps=99)
        assert rewound.turn_history == []

    def test_rewind_does_not_mutate_input(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        state = append_turn(state, {"n": 2})
        before = copy.deepcopy(state.turn_history)
        rewind(state, steps=1)
        assert state.turn_history == before

    def test_rewind_returns_new_object(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        rewound = rewind(state)
        assert rewound is not state

    def test_rewind_zero_steps_preserves_history(self):
        state = load_state(SAMPLE_XML)
        state = append_turn(state, {"n": 1})
        rewound = rewind(state, steps=0)
        assert len(rewound.turn_history) == 1


# ---------------------------------------------------------------------------
# resources round-trip
# ---------------------------------------------------------------------------


def test_save_roundtrip_preserves_resources(tmp_path):
    state = load_state(SAMPLE_XML)
    out = tmp_path / "state.xml"
    save_state(state, out)
    reloaded = load_state(out)
    assert reloaded.resources["attributes"] == state.resources["attributes"]
    assert reloaded.resources["inventory"] == state.resources["inventory"]
