"""AURPG campaign state manager.

Handles loading, validating, mutating, and persisting campaign state XML files.
All mutation operations are immutable — they return a new CampaignState and
never modify the input in place.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from aurpg.safety import SafetyCommand, apply_safety_command
from aurpg.validator import validate


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class StateError(Exception):
    """Raised when state loading, validation, or a mutation precondition fails."""


# ---------------------------------------------------------------------------
# CampaignState dataclass
# ---------------------------------------------------------------------------


@dataclass
class CampaignState:
    """In-memory representation of a parsed AURPG campaign state XML file.

    All container fields hold raw attribute dicts so the manager stays
    decoupled from the typed dataclasses in ``aurpg.state``.  Typed access is
    provided by the higher-level session layer.

    Note: ``<resources>`` (attributes, bonuses, relationships, inventory) is not
    stored in this dataclass and is therefore not serialized by ``save_state``.
    """

    path: Path                    # source file path (used as default save target)
    session_state: dict           # nested dict mirroring the <session_state> element
    clocks: list[dict]            # list of attribute dicts, one per <clock>
    progress_tracks: list[dict]   # list of attribute dicts, one per <track>
    safety_profile: list[dict]    # list of attribute dicts, one per <content_category>
    turn_history: list[dict] = field(default_factory=list)  # append-only mutation log


# ---------------------------------------------------------------------------
# XML parsing helpers
# ---------------------------------------------------------------------------


def _elem_to_dict(elem: Element) -> dict:
    """Return a shallow dict of *elem*'s attributes."""
    return dict(elem.attrib)


def _parse_session_state(session: Element) -> dict:
    """Parse <session_state> into a nested dict.

    Top-level keys match the child tag names (campaign, play_state, etc.).
    Each value is the attribute dict of the corresponding child element.
    """
    result: dict = {}
    for child in session:
        result[child.tag] = _elem_to_dict(child)
    return result


def _parse_clocks(root: Element) -> list[dict]:
    clocks: list[dict] = []
    machines = root.find("state_machines")
    if machines is not None:
        clocks_elem = machines.find("clocks")
        if clocks_elem is not None:
            for clock in clocks_elem.findall("clock"):
                clocks.append(_elem_to_dict(clock))
    return clocks


def _parse_tracks(root: Element) -> list[dict]:
    tracks: list[dict] = []
    machines = root.find("state_machines")
    if machines is not None:
        tracks_elem = machines.find("progress_tracks")
        if tracks_elem is not None:
            for track in tracks_elem.findall("track"):
                tracks.append(_elem_to_dict(track))
    return tracks


def _parse_safety_profile(root: Element) -> list[dict]:
    categories: list[dict] = []
    profile = root.find("safety_profile")
    if profile is not None:
        for cat in profile.findall("content_category"):
            categories.append(_elem_to_dict(cat))
    return categories


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def load_state(path: Path) -> CampaignState:
    """Load and validate a campaign state XML file.

    Args:
        path: Path to the XML file.

    Returns:
        A :class:`CampaignState` populated from the file.

    Raises:
        StateError: If the file fails validation or cannot be parsed.
    """
    errors = validate(path)
    if errors:
        summary = "; ".join(errors[:5])
        if len(errors) > 5:
            summary += f" … ({len(errors) - 5} more)"
        raise StateError(f"Validation failed for {path}: {summary}")

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise StateError(f"XML parse error in {path}: {exc}") from exc
    except OSError as exc:
        raise StateError(f"File error reading {path}: {exc}") from exc

    root = tree.getroot()

    session_elem = root.find("session_state")
    if session_elem is None:
        raise StateError(f"Missing <session_state> in {path}")

    return CampaignState(
        path=path,
        session_state=_parse_session_state(session_elem),
        clocks=_parse_clocks(root),
        progress_tracks=_parse_tracks(root),
        safety_profile=_parse_safety_profile(root),
        turn_history=[],
    )


# ---------------------------------------------------------------------------
# Immutable copy helpers
# ---------------------------------------------------------------------------


def _copy_state(state: CampaignState) -> CampaignState:
    """Return a deep copy of *state* (all nested dicts/lists are independent)."""
    return CampaignState(
        path=state.path,
        session_state=copy.deepcopy(state.session_state),
        clocks=copy.deepcopy(state.clocks),
        progress_tracks=copy.deepcopy(state.progress_tracks),
        safety_profile=copy.deepcopy(state.safety_profile),
        turn_history=copy.deepcopy(state.turn_history),
    )


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def tick_clock(state: CampaignState, clock_id: str, amount: int = 1) -> CampaignState:
    """Advance a clock's ``filled`` counter by *amount*, capped at ``segments``.

    Args:
        state:    Current campaign state (not modified).
        clock_id: The ``id`` attribute of the clock to advance.
        amount:   Number of ticks to add (default 1).

    Returns:
        A new :class:`CampaignState` with the clock updated.

    Raises:
        StateError: If no clock with *clock_id* exists.
    """
    new_state = _copy_state(state)
    for clock in new_state.clocks:
        if clock.get("id") == clock_id:
            segments = int(clock["segments"])
            filled = int(clock["filled"])
            clock["filled"] = str(max(0, min(segments, filled + amount)))
            return new_state
    raise StateError(f"Clock '{clock_id}' not found in state")


def set_stress(state: CampaignState, value: int) -> CampaignState:
    """Set the player's stress level, clamped to [0, 10].

    Args:
        state: Current campaign state (not modified).
        value: New stress value (will be clamped to 0–10).

    Returns:
        A new :class:`CampaignState` with ``player_state.stress`` updated.
    """
    new_state = _copy_state(state)
    clamped = max(0, min(10, value))
    new_state.session_state.setdefault("player_state", {})["stress"] = str(clamped)
    return new_state


def set_momentum(state: CampaignState, value: int) -> CampaignState:
    """Set the player's momentum, clamped to [-6, 10].

    Args:
        state: Current campaign state (not modified).
        value: New momentum value (will be clamped to -6–10).

    Returns:
        A new :class:`CampaignState` with ``player_state.momentum`` updated.
    """
    new_state = _copy_state(state)
    clamped = max(-6, min(10, value))
    new_state.session_state.setdefault("player_state", {})["momentum"] = str(clamped)
    return new_state


def apply_safety(state: CampaignState, command: SafetyCommand) -> CampaignState:
    """Apply a safety command, merging updated fields into ``session_state.safety_state``.

    Delegates to :func:`aurpg.safety.apply_safety_command` for the field logic.

    Args:
        state:   Current campaign state (not modified).
        command: The safety command to apply.

    Returns:
        A new :class:`CampaignState` with ``safety_state`` fields updated.
    """
    new_state = _copy_state(state)
    current_safety = new_state.session_state.get("safety_state", {})
    updated_safety = apply_safety_command(command, current_safety)
    new_state.session_state["safety_state"] = updated_safety
    return new_state


# ---------------------------------------------------------------------------
# Turn history
# ---------------------------------------------------------------------------


def append_turn(state: CampaignState, turn: dict) -> CampaignState:
    """Return a new state with *turn* appended to ``turn_history``.

    Args:
        state: Current campaign state (not modified).
        turn:  Dict describing the turn (keys are caller-defined).

    Returns:
        A new :class:`CampaignState` with the turn recorded.
    """
    new_state = _copy_state(state)
    new_state.turn_history = [*new_state.turn_history, copy.deepcopy(turn)]
    return new_state


def rewind(state: CampaignState, steps: int = 1) -> CampaignState:
    """Return the state *steps* turns ago by removing the last *steps* entries.

    This is a lightweight Phase 2 implementation: the last ``steps`` entries
    are dropped from ``turn_history``.  Full replay from the original loaded
    state is deferred to Phase 3+.

    Args:
        state: Current campaign state (not modified).
        steps: Number of turns to rewind (default 1).  If *steps* exceeds the
               history length, all history is cleared.

    Returns:
        A new :class:`CampaignState` with ``turn_history`` truncated.
    """
    new_state = _copy_state(state)
    trim = max(0, len(new_state.turn_history) - steps)
    new_state.turn_history = new_state.turn_history[:trim]
    return new_state


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _build_session_state_elem(session_state: dict) -> Element:
    """Reconstruct a <session_state> element from the nested attribute dict."""
    session_elem = Element("session_state")
    for tag, attrs in session_state.items():
        child = SubElement(session_elem, tag)
        for k, v in attrs.items():
            child.set(k, str(v))
    return session_elem


def _build_state_machines_elem(clocks: list[dict], tracks: list[dict]) -> Element:
    machines_elem = Element("state_machines")
    clocks_elem = SubElement(machines_elem, "clocks")
    for clock_attrs in clocks:
        clock_el = SubElement(clocks_elem, "clock")
        for k, v in clock_attrs.items():
            clock_el.set(k, str(v))
    tracks_elem = SubElement(machines_elem, "progress_tracks")
    for track_attrs in tracks:
        track_el = SubElement(tracks_elem, "track")
        for k, v in track_attrs.items():
            track_el.set(k, str(v))
    return machines_elem


def _build_safety_profile_elem(safety_profile: list[dict]) -> Element:
    profile_elem = Element("safety_profile")
    for cat_attrs in safety_profile:
        cat_el = SubElement(profile_elem, "content_category")
        for k, v in cat_attrs.items():
            cat_el.set(k, str(v))
    return profile_elem


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_state(state: CampaignState, path: Path | None = None) -> Path:
    """Serialise *state* back to XML and write it to disk.

    Args:
        state: Campaign state to serialise.
        path:  Destination path.  Defaults to ``state.path`` when ``None``.

    Returns:
        The path that was written.
    """
    target = path if path is not None else state.path

    root = Element("aurpg_campaign_state")
    root.set("version", "0.1-prototype")

    root.append(_build_session_state_elem(state.session_state))
    root.append(_build_state_machines_elem(state.clocks, state.progress_tracks))
    root.append(_build_safety_profile_elem(state.safety_profile))
    # TODO: <resources> (attributes, bonuses, relationships, inventory) is not held in
    #       CampaignState and is therefore silently dropped on save.  Tracked for Phase 3.

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    target.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(target), encoding="unicode", xml_declaration=False)

    return target
