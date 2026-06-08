"""Tests for the AURPG XML ↔ SessionState parser round-trip."""

from pathlib import Path

import pytest

from aurpg.parser import dump_state, load_state, parse_state
from aurpg.state import (
    ClockType,
    ContentStatus,
    Effect,
    HarmLevel,
    LoadState,
    OrchestrationMode,
    PlayMode,
    Position,
    TrackRank,
)

SAMPLE_STATE = (
    Path(__file__).parent.parent
    / "src/aurpg/prompts/examples/sample_campaign_state.xml"
)


# ---------------------------------------------------------------------------
# load_state — sample fixture
# ---------------------------------------------------------------------------


def test_load_state_campaign_meta():
    state = load_state(SAMPLE_STATE)
    assert state.campaign.id == "camp-neon-ash-01"
    assert state.campaign.title == "Neon Ash Protocol"
    assert state.campaign.orchestration_mode == OrchestrationMode.COLLABORATIVE_CONSULT


def test_load_state_play_state():
    state = load_state(SAMPLE_STATE)
    assert state.play_state.mode == PlayMode.SOLO
    assert "Dockyard" in state.play_state.location


def test_load_state_player_state():
    state = load_state(SAMPLE_STATE)
    ps = state.player_state
    assert ps.character_name == "Mara Voss"
    assert ps.stress == 4
    assert ps.momentum == 6
    assert ps.harm == HarmLevel.BRUISED
    assert ps.load == LoadState.NORMAL


def test_load_state_resolution_state():
    state = load_state(SAMPLE_STATE)
    rs = state.resolution_state
    assert rs.position == Position.RISKY
    assert rs.effect == Effect.STANDARD


def test_load_state_safety_state():
    state = load_state(SAMPLE_STATE)
    ss = state.safety_state
    assert ss.hard_stop is False
    assert ss.pause is False


def test_load_state_attributes():
    state = load_state(SAMPLE_STATE)
    assert state.resources.attribute("edge") == 3
    assert state.resources.attribute("heart") == 1
    assert state.resources.attribute("iron") == 2
    assert state.resources.attribute("shadow") == 2
    assert state.resources.attribute("wits") == 2


def test_load_state_bonuses():
    state = load_state(SAMPLE_STATE)
    assert state.resources.total_bonus() == 2  # picks +1, intel +1


def test_load_state_relationships():
    state = load_state(SAMPLE_STATE)
    rels = {r.npc: r for r in state.resources.relationships}
    assert "Lattice" in rels
    assert rels["Lattice"].clock_ref == "clk-trust-lattice"


def test_load_state_inventory():
    state = load_state(SAMPLE_STATE)
    names = [i.name for i in state.resources.inventory]
    assert "signal_scrambler" in names
    assert "breach_kit" in names


def test_load_state_clocks():
    state = load_state(SAMPLE_STATE)
    mission = state.state_machines.clock("clk-mission-archive-extraction")
    assert mission is not None
    assert mission.type == ClockType.MISSION
    assert mission.segments == 8
    assert mission.filled == 5


def test_load_state_progress_tracks():
    state = load_state(SAMPLE_STATE)
    track = state.state_machines.track("trk-clear-name")
    assert track is not None
    assert track.rank == TrackRank.EXTREME
    assert track.boxes_filled == 2


def test_load_state_safety_profile():
    state = load_state(SAMPLE_STATE)
    assert state.safety_profile.status("horror") == ContentStatus.YELLOW
    assert state.safety_profile.status("relationships") == ContentStatus.GREEN


# ---------------------------------------------------------------------------
# parse_state — inline XML
# ---------------------------------------------------------------------------


_MINIMAL_XML = """\
<aurpg_campaign_state version="0.1">
  <session_state>
    <campaign id="c1" title="Test" genre="fantasy" tone="dark"
              canon_mode="strict" orchestration_mode="strict_manual"/>
    <play_state mode="solo" scene_id="s1" location="Cave"
                objective="Survive" time_marker="dawn"/>
    <player_state character_name="Hero" deep_pov="true"
                  stress="0" momentum="2" harm="none" load="light"/>
    <resolution_state position="controlled" effect="great"
                      move_trigger="none" stakes="minimal"/>
    <safety_state hard_stop="false" pause="false" intensity_check="none"/>
  </session_state>
</aurpg_campaign_state>
"""


def test_parse_state_minimal_valid():
    state = parse_state(_MINIMAL_XML)
    assert state.campaign.id == "c1"
    assert state.play_state.mode == PlayMode.SOLO
    assert state.player_state.harm == HarmLevel.NONE
    assert state.resolution_state.position == Position.CONTROLLED
    assert state.resolution_state.effect == Effect.GREAT


def test_parse_state_missing_session_state_raises():
    with pytest.raises(ValueError, match="session_state"):
        parse_state("<aurpg_campaign_state/>")


def test_parse_state_missing_required_attr_raises():
    bad = _MINIMAL_XML.replace('id="c1"', "")
    with pytest.raises(ValueError, match="id"):
        parse_state(bad)


def test_parse_state_invalid_enum_raises():
    bad = _MINIMAL_XML.replace('mode="solo"', 'mode="coop"')
    with pytest.raises(ValueError):
        parse_state(bad)


def test_parse_state_invalid_bool_raises():
    bad = _MINIMAL_XML.replace('deep_pov="true"', 'deep_pov="invalid"')
    with pytest.raises(ValueError, match="must be 'true' or 'false'"):
        parse_state(bad)


def test_parse_state_invalid_attribute_name_raises():
    bad = _MINIMAL_XML.replace(
        "</session_state>",
        "</session_state>"
        "<resources><attributes>"
        '<attribute name="invalid_attr" value="3"/>'
        "</attributes></resources>",
    )
    with pytest.raises(ValueError, match="Invalid attribute name"):
        parse_state(bad)


# ---------------------------------------------------------------------------
# Round-trip: load → dump → parse produces equal state
# ---------------------------------------------------------------------------


def test_round_trip_campaign_meta():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    assert restored.campaign.id == original.campaign.id
    assert restored.campaign.orchestration_mode == original.campaign.orchestration_mode


def test_round_trip_player_state():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    assert restored.player_state.stress == original.player_state.stress
    assert restored.player_state.momentum == original.player_state.momentum
    assert restored.player_state.harm == original.player_state.harm


def test_round_trip_clocks():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    orig_ids = {c.id for c in original.state_machines.clocks}
    rest_ids = {c.id for c in restored.state_machines.clocks}
    assert orig_ids == rest_ids


def test_round_trip_progress_tracks():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    for orig_track in original.state_machines.progress_tracks:
        rest_track = restored.state_machines.track(orig_track.id)
        assert rest_track is not None
        assert rest_track.boxes_filled == orig_track.boxes_filled
        assert rest_track.ticks_in_current_box == orig_track.ticks_in_current_box


def test_round_trip_safety_profile():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    for cat in original.safety_profile.categories:
        assert restored.safety_profile.status(cat.name) == cat.status


def test_round_trip_inventory_tags():
    original = load_state(SAMPLE_STATE)
    xml_out = dump_state(original)
    restored = parse_state(xml_out)
    orig_item = next(i for i in original.resources.inventory if i.name == "signal_scrambler")
    rest_item = next(i for i in restored.resources.inventory if i.name == "signal_scrambler")
    assert set(rest_item.tags) == set(orig_item.tags)
