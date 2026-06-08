"""XML round-trip tests for AURPG campaign state.

Validates that sample_campaign_state.xml survives a parse → mutate → serialize
→ validate cycle without losing structural integrity. This is the closest
approximation to a full round-trip until the Phase 1 XML ↔ Pydantic parser
is written.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from aurpg.validator import validate

SAMPLE_STATE = (
    Path(__file__).parent.parent
    / "src/aurpg/prompts/examples/sample_campaign_state.xml"
)


def _parse_and_reserialize(path: Path) -> str:
    """Parse an XML file and return it as a re-serialized string."""
    tree = ET.parse(path)
    return ET.tostring(tree.getroot(), encoding="unicode")


def _reserialize_to_file(xml_string: str, tmp_path: Path) -> Path:
    dest = tmp_path / "roundtrip.xml"
    dest.write_text(xml_string, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Round-trip: parse → re-serialize → validate
# ---------------------------------------------------------------------------


def test_sample_state_survives_parse_and_reserialize(tmp_path: Path) -> None:
    """Sample state must pass validation after an ElementTree round-trip."""
    xml_string = _parse_and_reserialize(SAMPLE_STATE)
    dest = _reserialize_to_file(xml_string, tmp_path)
    errors = validate(dest)
    assert errors == [], "Validation errors after round-trip:\n" + "\n".join(errors)


def test_roundtrip_preserves_root_tag() -> None:
    xml_string = _parse_and_reserialize(SAMPLE_STATE)
    root = ET.fromstring(xml_string)
    assert root.tag == "aurpg_campaign_state"


def test_roundtrip_preserves_clock_count() -> None:
    original_tree = ET.parse(SAMPLE_STATE)
    original_clocks = original_tree.findall(".//clocks/clock")

    xml_string = _parse_and_reserialize(SAMPLE_STATE)
    roundtrip_root = ET.fromstring(xml_string)
    roundtrip_clocks = roundtrip_root.findall(".//clocks/clock")

    assert len(original_clocks) == len(roundtrip_clocks), (
        f"Clock count changed after round-trip: "
        f"{len(original_clocks)} → {len(roundtrip_clocks)}"
    )


def test_roundtrip_preserves_player_state_fields() -> None:
    original_tree = ET.parse(SAMPLE_STATE)
    original_ps = original_tree.find(".//player_state")
    assert original_ps is not None

    xml_string = _parse_and_reserialize(SAMPLE_STATE)
    roundtrip_root = ET.fromstring(xml_string)
    roundtrip_ps = roundtrip_root.find(".//player_state")
    assert roundtrip_ps is not None

    for attr in ("stress", "momentum", "harm", "character_name"):
        assert original_ps.get(attr) == roundtrip_ps.get(attr), (
            f"player_state.{attr} changed after round-trip: "
            f"{original_ps.get(attr)!r} → {roundtrip_ps.get(attr)!r}"
        )


# ---------------------------------------------------------------------------
# Round-trip with mutation: advance a clock, re-validate
# ---------------------------------------------------------------------------


def test_clock_mutation_survives_roundtrip(tmp_path: Path) -> None:
    """Advancing a clock fill value must still pass validation after round-trip."""
    tree = ET.parse(SAMPLE_STATE)
    root = tree.getroot()

    clock = root.find('.//clocks/clock[@id="clk-danger-alarm-sweep"]')
    assert clock is not None, "Test clock not found in sample state"

    original_filled = int(clock.attrib["filled"])
    segments = int(clock.attrib["segments"])
    new_filled = min(original_filled + 1, segments)
    clock.set("filled", str(new_filled))

    mutated_xml = ET.tostring(root, encoding="unicode")
    dest = _reserialize_to_file(mutated_xml, tmp_path)
    errors = validate(dest)
    assert errors == [], (
        f"Validation errors after clock mutation (filled {original_filled}→{new_filled}):\n"
        + "\n".join(errors)
    )


def test_stress_mutation_survives_roundtrip(tmp_path: Path) -> None:
    """Updating player stress must still pass validation after round-trip."""
    tree = ET.parse(SAMPLE_STATE)
    root = tree.getroot()

    player_state = root.find(".//player_state")
    assert player_state is not None

    original_stress = int(player_state.attrib["stress"])
    new_stress = min(original_stress + 1, 10)
    player_state.set("stress", str(new_stress))

    mutated_xml = ET.tostring(root, encoding="unicode")
    dest = _reserialize_to_file(mutated_xml, tmp_path)
    errors = validate(dest)
    assert errors == [], (
        f"Validation errors after stress mutation ({original_stress}→{new_stress}):\n"
        + "\n".join(errors)
    )
