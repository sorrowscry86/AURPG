"""Validate AURPG campaign state XML files against the canonical schema.

Usage:
    python -m aurpg.validator <campaign_state.xml> [...]

Exits 0 if all files pass, 1 if any file has errors.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Allowed enum values (mirrors state.py enumerations)
# ---------------------------------------------------------------------------

VALID_PLAY_MODES = {"solo", "squad"}
VALID_POSITIONS = {"controlled", "risky", "desperate"}
VALID_EFFECTS = {"limited", "standard", "great"}
VALID_CLOCK_TYPES = {"standard", "danger", "racing", "linked", "mission"}
VALID_TRACK_RANKS = {"troublesome", "dangerous", "formidable", "extreme", "epic"}
VALID_CONTENT_STATUS = {"green", "yellow", "red"}
VALID_ORCHESTRATION_MODES = {"strict_manual", "collaborative_consult", "generative_synthesis"}
VALID_CLOCK_SEGMENTS = {4, 6, 8}

# Required attributes per session_state child element
REQUIRED_SESSION_ATTRS: dict[str, list[str]] = {
    "campaign": ["id", "title", "genre", "tone", "canon_mode", "orchestration_mode"],
    "play_state": ["mode", "scene_id", "location", "objective", "time_marker"],
    "player_state": ["character_name", "deep_pov", "stress", "momentum", "harm", "load"],
    "resolution_state": ["position", "effect", "move_trigger", "stakes"],
    "safety_state": ["hard_stop", "pause", "intensity_check"],
}


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------


def validate(path: Path) -> list[str]:
    """Return a list of validation error strings.  Empty list means valid."""
    errors: list[str] = []

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"]
    except OSError as exc:
        return [f"File error: {exc}"]

    root = tree.getroot()

    # -- session_state -------------------------------------------------------
    session = root.find("session_state")
    if session is None:
        errors.append("Missing <session_state>")
        return errors

    for tag, attrs in REQUIRED_SESSION_ATTRS.items():
        elem = session.find(tag)
        if elem is None:
            errors.append(f"Missing <{tag}> in <session_state>")
            continue
        for attr in attrs:
            if elem.get(attr) is None:
                errors.append(f"<{tag}> missing required attribute '{attr}'")

    play_state = session.find("play_state")
    if play_state is not None:
        mode = play_state.get("mode", "")
        if mode not in VALID_PLAY_MODES:
            errors.append(
                f"<play_state mode='{mode}'> must be one of {sorted(VALID_PLAY_MODES)}"
            )

    resolution = session.find("resolution_state")
    if resolution is not None:
        pos = resolution.get("position", "")
        if pos not in VALID_POSITIONS:
            errors.append(
                f"<resolution_state position='{pos}'> must be one of {sorted(VALID_POSITIONS)}"
            )
        eff = resolution.get("effect", "")
        if eff not in VALID_EFFECTS:
            errors.append(
                f"<resolution_state effect='{eff}'> must be one of {sorted(VALID_EFFECTS)}"
            )

    campaign = session.find("campaign")
    if campaign is not None:
        orch = campaign.get("orchestration_mode", "")
        if orch not in VALID_ORCHESTRATION_MODES:
            errors.append(
                f"<campaign orchestration_mode='{orch}'> must be one of "
                f"{sorted(VALID_ORCHESTRATION_MODES)}"
            )

    player = session.find("player_state")
    if player is not None:
        _check_int_range(errors, player, "stress", 0, 10)
        _check_int_range(errors, player, "momentum", -6, 10)

        valid_harm = {"none", "bruised", "wounded", "incapacitated"}
        harm = player.get("harm", "")
        if harm not in valid_harm:
            errors.append(
                f"<player_state harm='{harm}'> must be one of {sorted(valid_harm)}"
            )

        valid_load = {"light", "normal", "heavy"}
        load = player.get("load", "")
        if load not in valid_load:
            errors.append(
                f"<player_state load='{load}'> must be one of {sorted(valid_load)}"
            )

    # -- state_machines ------------------------------------------------------
    machines = root.find("state_machines")
    if machines is not None:
        clocks_elem = machines.find("clocks")
        if clocks_elem is not None:
            for clock in clocks_elem.findall("clock"):
                _validate_clock(errors, clock)

        tracks_elem = machines.find("progress_tracks")
        if tracks_elem is not None:
            for track in tracks_elem.findall("track"):
                _validate_track(errors, track)

    # -- safety_profile ------------------------------------------------------
    profile = root.find("safety_profile")
    if profile is not None:
        for cat in profile.findall("content_category"):
            name = cat.get("name", "<unnamed>")
            status = cat.get("status", "")
            if status not in VALID_CONTENT_STATUS:
                errors.append(
                    f"<content_category name='{name}' status='{status}'> "
                    f"must be one of {sorted(VALID_CONTENT_STATUS)}"
                )

    return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_int_range(
    errors: list[str],
    elem: ET.Element,
    attr: str,
    lo: int,
    hi: int,
) -> None:
    raw = elem.get(attr)
    if raw is None:
        return  # already caught by required-attrs check
    try:
        val = int(raw)
    except ValueError:
        errors.append(f"<{elem.tag} {attr}='{raw}'> must be an integer")
        return
    if not (lo <= val <= hi):
        errors.append(f"<{elem.tag} {attr}={val}> must be in [{lo}, {hi}]")


def _validate_clock(errors: list[str], clock: ET.Element) -> None:
    cid = clock.get("id", "<no-id>")

    ctype = clock.get("type", "")
    if ctype not in VALID_CLOCK_TYPES:
        errors.append(f"clock id='{cid}' type='{ctype}' must be one of {sorted(VALID_CLOCK_TYPES)}")

    try:
        segments = int(clock.get("segments", "0"))
    except ValueError:
        errors.append(f"clock id='{cid}' segments must be an integer")
        return
    if segments not in VALID_CLOCK_SEGMENTS:
        errors.append(f"clock id='{cid}' segments={segments} must be one of {sorted(VALID_CLOCK_SEGMENTS)}")

    try:
        filled = int(clock.get("filled", "0"))
    except ValueError:
        errors.append(f"clock id='{cid}' filled must be an integer")
        return
    if filled < 0 or filled > segments:
        errors.append(f"clock id='{cid}' filled={filled} must be in [0, {segments}]")


def _validate_track(errors: list[str], track: ET.Element) -> None:
    tid = track.get("id", "<no-id>")

    rank = track.get("rank", "")
    if rank not in VALID_TRACK_RANKS:
        errors.append(f"track id='{tid}' rank='{rank}' must be one of {sorted(VALID_TRACK_RANKS)}")

    try:
        boxes = int(track.get("boxes_filled", "0"))
    except ValueError:
        errors.append(f"track id='{tid}' boxes_filled must be an integer")
        return
    if boxes < 0 or boxes > 10:
        errors.append(f"track id='{tid}' boxes_filled={boxes} must be in [0, 10]")

    try:
        ticks = int(track.get("ticks_in_current_box", "0"))
    except ValueError:
        errors.append(f"track id='{tid}' ticks_in_current_box must be an integer")
        return
    if ticks < 0 or ticks > 3:
        errors.append(f"track id='{tid}' ticks_in_current_box={ticks} must be in [0, 3]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m aurpg.validator <campaign_state.xml> [...]")
        sys.exit(1)

    any_error = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        errors = validate(path)
        if errors:
            print(f"FAIL  {path}")
            for e in errors:
                print(f"      {e}")
            any_error = True
        else:
            print(f"OK    {path}")

    sys.exit(1 if any_error else 0)


if __name__ == "__main__":
    main()
