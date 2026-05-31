"""Tests for the AURPG campaign state XML validator."""

from pathlib import Path

import pytest

from aurpg.validator import validate

SAMPLE_STATE = (
    Path(__file__).parent.parent
    / "src/aurpg/prompts/examples/sample_campaign_state.xml"
)

# Minimal valid session_state block reused across tests.
_VALID_SESSION = """
  <session_state>
    <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
    <play_state mode="solo" scene_id="s1" location="L" objective="O" time_marker="now"/>
    <player_state character_name="Hero" deep_pov="true" stress="0" momentum="0" harm="none" load="light"/>
    <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
    <safety_state hard_stop="false" pause="false" intensity_check="none"/>
  </session_state>
"""


def _wrap(session_block: str, extra: str = "") -> str:
    return f"<aurpg_campaign_state>{session_block}{extra}</aurpg_campaign_state>"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_sample_campaign_state_is_valid():
    errors = validate(SAMPLE_STATE)
    assert errors == [], "Unexpected validation errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# File / parse errors
# ---------------------------------------------------------------------------


def test_invalid_xml_returns_parse_error(tmp_path: Path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<unclosed>")
    errors = validate(bad)
    assert len(errors) == 1
    assert "parse error" in errors[0].lower()


def test_missing_file_returns_file_error(tmp_path: Path):
    errors = validate(tmp_path / "nonexistent.xml")
    assert len(errors) == 1
    assert "file error" in errors[0].lower()


# ---------------------------------------------------------------------------
# Required structure
# ---------------------------------------------------------------------------


def test_missing_session_state(tmp_path: Path):
    xml = tmp_path / "empty.xml"
    xml.write_text('<aurpg_campaign_state version="0.1"/>')
    errors = validate(xml)
    assert any("session_state" in e for e in errors)


def test_missing_deep_pov(tmp_path: Path):
    xml = tmp_path / "no_deep_pov.xml"
    xml.write_text(
        _wrap("""
          <session_state>
            <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
            <play_state mode="solo" scene_id="s1" location="L" objective="O" time_marker="now"/>
            <player_state character_name="Hero" stress="0" momentum="0" harm="none" load="light"/>
            <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
            <safety_state hard_stop="false" pause="false" intensity_check="none"/>
          </session_state>
        """)
    )
    errors = validate(xml)
    assert any("deep_pov" in e for e in errors)


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------


def test_invalid_play_mode(tmp_path: Path):
    xml = tmp_path / "bad_mode.xml"
    session = _VALID_SESSION.replace('mode="solo"', 'mode="coop"')
    xml.write_text(_wrap(session))
    errors = validate(xml)
    assert any("play_state" in e and "mode" in e for e in errors)


def test_invalid_harm(tmp_path: Path):
    xml = tmp_path / "bad_harm.xml"
    session = _VALID_SESSION.replace('harm="none"', 'harm="bruised_ribs"')
    xml.write_text(_wrap(session))
    errors = validate(xml)
    assert any("harm" in e for e in errors)


def test_invalid_load(tmp_path: Path):
    xml = tmp_path / "bad_load.xml"
    session = _VALID_SESSION.replace('load="light"', 'load="overloaded"')
    xml.write_text(_wrap(session))
    errors = validate(xml)
    assert any("load" in e for e in errors)


def test_invalid_content_status(tmp_path: Path):
    xml = tmp_path / "bad_safety.xml"
    xml.write_text(
        _wrap(
            _VALID_SESSION,
            '<safety_profile><content_category name="horror" status="maybe" guidance="test"/></safety_profile>',
        )
    )
    errors = validate(xml)
    assert any("horror" in e and "status" in e for e in errors)


# ---------------------------------------------------------------------------
# Numeric range checks
# ---------------------------------------------------------------------------


def test_stress_out_of_range(tmp_path: Path):
    xml = tmp_path / "bad_stress.xml"
    session = _VALID_SESSION.replace('stress="0"', 'stress="99"')
    xml.write_text(_wrap(session))
    errors = validate(xml)
    assert any("stress" in e for e in errors)


def test_momentum_out_of_range(tmp_path: Path):
    xml = tmp_path / "bad_momentum.xml"
    session = _VALID_SESSION.replace('momentum="0"', 'momentum="-99"')
    xml.write_text(_wrap(session))
    errors = validate(xml)
    assert any("momentum" in e for e in errors)


# ---------------------------------------------------------------------------
# Clock validation
# ---------------------------------------------------------------------------


def test_invalid_clock_segments(tmp_path: Path):
    xml = tmp_path / "bad_clock.xml"
    xml.write_text(
        _wrap(
            _VALID_SESSION,
            '<state_machines><clocks>'
            '<clock id="clk-test" name="Test" type="standard" segments="5" filled="0"/>'
            '</clocks></state_machines>',
        )
    )
    errors = validate(xml)
    assert any("segments" in e for e in errors)


def test_clock_filled_exceeds_segments(tmp_path: Path):
    xml = tmp_path / "overfull_clock.xml"
    xml.write_text(
        _wrap(
            _VALID_SESSION,
            '<state_machines><clocks>'
            '<clock id="clk-test" name="Test" type="standard" segments="4" filled="9"/>'
            '</clocks></state_machines>',
        )
    )
    errors = validate(xml)
    assert any("filled" in e for e in errors)
