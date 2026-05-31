"""Tests for the AURPG campaign state XML validator."""

from pathlib import Path

import pytest

from aurpg.validator import validate

SAMPLE_STATE = (
    Path(__file__).parent.parent
    / "src/aurpg/prompts/examples/sample_campaign_state.xml"
)


def test_sample_campaign_state_is_valid():
    errors = validate(SAMPLE_STATE)
    assert errors == [], f"Unexpected validation errors:\n" + "\n".join(errors)


def test_invalid_xml_returns_parse_error(tmp_path: Path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<unclosed>")
    errors = validate(bad)
    assert len(errors) == 1
    assert "parse error" in errors[0].lower()


def test_missing_session_state(tmp_path: Path):
    xml = tmp_path / "empty.xml"
    xml.write_text('<aurpg_campaign_state version="0.1"/>')
    errors = validate(xml)
    assert any("session_state" in e for e in errors)


def test_invalid_play_mode(tmp_path: Path):
    xml = tmp_path / "bad_mode.xml"
    xml.write_text(
        """<aurpg_campaign_state>
          <session_state>
            <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
            <play_state mode="coop" scene_id="s1" location="L" objective="O" time_marker="now"/>
            <player_state character_name="Hero" stress="0" momentum="0" harm="none" load="light"/>
            <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
            <safety_state hard_stop="false" pause="false" intensity_check="none"/>
          </session_state>
        </aurpg_campaign_state>"""
    )
    errors = validate(xml)
    assert any("play_state" in e and "mode" in e for e in errors)


def test_stress_out_of_range(tmp_path: Path):
    xml = tmp_path / "bad_stress.xml"
    xml.write_text(
        """<aurpg_campaign_state>
          <session_state>
            <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
            <play_state mode="solo" scene_id="s1" location="L" objective="O" time_marker="now"/>
            <player_state character_name="Hero" stress="99" momentum="0" harm="none" load="light"/>
            <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
            <safety_state hard_stop="false" pause="false" intensity_check="none"/>
          </session_state>
        </aurpg_campaign_state>"""
    )
    errors = validate(xml)
    assert any("stress" in e for e in errors)


def test_invalid_clock_segments(tmp_path: Path):
    xml = tmp_path / "bad_clock.xml"
    xml.write_text(
        """<aurpg_campaign_state>
          <session_state>
            <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
            <play_state mode="solo" scene_id="s1" location="L" objective="O" time_marker="now"/>
            <player_state character_name="Hero" stress="0" momentum="0" harm="none" load="light"/>
            <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
            <safety_state hard_stop="false" pause="false" intensity_check="none"/>
          </session_state>
          <state_machines>
            <clocks>
              <clock id="clk-test" name="Test" type="standard" segments="5" filled="0"/>
            </clocks>
          </state_machines>
        </aurpg_campaign_state>"""
    )
    errors = validate(xml)
    assert any("segments" in e for e in errors)


def test_invalid_content_status(tmp_path: Path):
    xml = tmp_path / "bad_safety.xml"
    xml.write_text(
        """<aurpg_campaign_state>
          <session_state>
            <campaign id="c1" title="T" genre="g" tone="t" canon_mode="strict" orchestration_mode="strict_manual"/>
            <play_state mode="solo" scene_id="s1" location="L" objective="O" time_marker="now"/>
            <player_state character_name="Hero" stress="0" momentum="0" harm="none" load="light"/>
            <resolution_state position="risky" effect="standard" move_trigger="none" stakes="low"/>
            <safety_state hard_stop="false" pause="false" intensity_check="none"/>
          </session_state>
          <safety_profile>
            <content_category name="horror" status="maybe" guidance="test"/>
          </safety_profile>
        </aurpg_campaign_state>"""
    )
    errors = validate(xml)
    assert any("horror" in e and "status" in e for e in errors)
