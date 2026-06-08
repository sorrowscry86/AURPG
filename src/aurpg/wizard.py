"""AURPG Campaign Creation Wizard.

Drives a 4-stage onboarding dialogue and produces an initial campaign state XML file.

Stages:
    1. System      — campaign title, genre, tone, canon_mode
    2. Character   — character_name, attributes (edge/heart/iron/shadow/wits), load
    3. Safety      — per-category consent (horror/health/relationships/social_issues)
                     plus orchestration_mode
    4. Orchestration — confirm orchestration_mode, set initial position and effect

Public API:
    WizardConfig        — dataclass holding all wizard answers
    validate_config     — returns list of error strings (empty = valid)
    config_to_state_xml — produces a valid campaign state XML string
    run_wizard          — interactive CLI driver (injectable prompt_fn for testing)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, SubElement


# ---------------------------------------------------------------------------
# WizardConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class WizardConfig:
    # Stage 1 — System
    title: str
    genre: str
    tone: str
    canon_mode: str              # "strict_continuity" | "flexible_canon" | "sandbox"

    # Stage 2 — Character
    character_name: str
    edge: int
    heart: int
    iron: int
    shadow: int
    wits: int
    load: str                    # "light" | "normal" | "heavy"

    # Stage 3 — Safety
    safety: dict[str, str]       # category -> "green"|"yellow"|"red"
    orchestration_mode: str      # "strict_manual"|"collaborative_consult"|"generative_synthesis"

    # Stage 4 — Orchestration
    initial_position: str        # "controlled"|"risky"|"desperate"
    initial_effect: str          # "limited"|"standard"|"great"


# ---------------------------------------------------------------------------
# Allowed enum sets
# ---------------------------------------------------------------------------

_VALID_CANON_MODES = {"strict_continuity", "flexible_canon", "sandbox"}
_VALID_LOADS = {"light", "normal", "heavy"}
_VALID_SAFETY_STATUSES = {"green", "yellow", "red"}
_VALID_ORCHESTRATION_MODES = {"strict_manual", "collaborative_consult", "generative_synthesis"}
_VALID_POSITIONS = {"controlled", "risky", "desperate"}
_VALID_EFFECTS = {"limited", "standard", "great"}
_SAFETY_CATEGORIES = ("horror", "health", "relationships", "social_issues")


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def validate_config(config: WizardConfig) -> list[str]:
    """Return a list of validation error strings.  Empty list means valid.

    Checks:
    - Each attribute (edge/heart/iron/shadow/wits) is in [1, 3]
    - Attribute sum ≤ 10
    - load in {"light", "normal", "heavy"}
    - canon_mode in {"strict_continuity", "flexible_canon", "sandbox"}
    - Each safety category status in {"green", "yellow", "red"}
    - orchestration_mode in {"strict_manual", "collaborative_consult", "generative_synthesis"}
    - initial_position in {"controlled", "risky", "desperate"}
    - initial_effect in {"limited", "standard", "great"}
    """
    errors: list[str] = []

    # Attribute range checks
    attrs = {
        "edge": config.edge,
        "heart": config.heart,
        "iron": config.iron,
        "shadow": config.shadow,
        "wits": config.wits,
    }
    for name, value in attrs.items():
        if not isinstance(value, int) or not (1 <= value <= 3):
            errors.append(f"Attribute '{name}' must be an integer in [1, 3]; got {value!r}")

    attr_sum = sum(attrs.values())
    if not errors and attr_sum > 10:
        errors.append(
            f"Attribute sum must be ≤ 10; got {attr_sum} "
            f"(edge={config.edge}, heart={config.heart}, iron={config.iron}, "
            f"shadow={config.shadow}, wits={config.wits})"
        )

    # load
    if config.load not in _VALID_LOADS:
        errors.append(
            f"'load' must be one of {sorted(_VALID_LOADS)}; got {config.load!r}"
        )

    # canon_mode
    if config.canon_mode not in _VALID_CANON_MODES:
        errors.append(
            f"'canon_mode' must be one of {sorted(_VALID_CANON_MODES)}; got {config.canon_mode!r}"
        )

    # safety categories
    for category in _SAFETY_CATEGORIES:
        status = config.safety.get(category)
        if status not in _VALID_SAFETY_STATUSES:
            errors.append(
                f"safety category '{category}' must be one of {sorted(_VALID_SAFETY_STATUSES)}; "
                f"got {status!r}"
            )

    # orchestration_mode
    if config.orchestration_mode not in _VALID_ORCHESTRATION_MODES:
        errors.append(
            f"'orchestration_mode' must be one of {sorted(_VALID_ORCHESTRATION_MODES)}; "
            f"got {config.orchestration_mode!r}"
        )

    # initial_position
    if config.initial_position not in _VALID_POSITIONS:
        errors.append(
            f"'initial_position' must be one of {sorted(_VALID_POSITIONS)}; "
            f"got {config.initial_position!r}"
        )

    # initial_effect
    if config.initial_effect not in _VALID_EFFECTS:
        errors.append(
            f"'initial_effect' must be one of {sorted(_VALID_EFFECTS)}; "
            f"got {config.initial_effect!r}"
        )

    return errors


# ---------------------------------------------------------------------------
# config_to_state_xml
# ---------------------------------------------------------------------------


def config_to_state_xml(config: WizardConfig) -> str:
    """Produce a valid campaign state XML string from *config*.

    Starting state values:
        stress=0, momentum=2, harm="none"
        No clocks, no progress tracks, empty turn_history.

    The result passes ``aurpg.validator.validate()`` when written to a file.
    """
    root = Element("aurpg_campaign_state", version="0.1-prototype")

    # ------------------------------------------------------------------
    # <session_state>
    # ------------------------------------------------------------------
    session = SubElement(root, "session_state")

    campaign_id = f"camp-{uuid.uuid4().hex[:8]}"
    SubElement(session, "campaign", attrib={
        "id": campaign_id,
        "title": config.title,
        "genre": config.genre,
        "tone": config.tone,
        "canon_mode": config.canon_mode,
        "orchestration_mode": config.orchestration_mode,
    })

    SubElement(session, "play_state", attrib={
        "mode": "solo",
        "scene_id": "scene-001",
        "location": "unknown",
        "objective": "none",
        "time_marker": "start",
    })

    SubElement(session, "player_state", attrib={
        "character_name": config.character_name,
        "deep_pov": "true",
        "stress": "0",
        "momentum": "2",
        "harm": "none",
        "load": config.load,
    })

    SubElement(session, "resolution_state", attrib={
        "position": config.initial_position,
        "effect": config.initial_effect,
        "move_trigger": "none",
        "stakes": "none",
    })

    SubElement(session, "safety_state", attrib={
        "hard_stop": "false",
        "pause": "false",
        "intensity_check": "none",
    })

    # ------------------------------------------------------------------
    # <resources>
    # ------------------------------------------------------------------
    resources = SubElement(root, "resources")
    attributes_elem = SubElement(resources, "attributes")
    for attr_name in ("edge", "heart", "iron", "shadow", "wits"):
        SubElement(attributes_elem, "attribute", attrib={
            "name": attr_name,
            "value": str(getattr(config, attr_name)),
        })
    SubElement(resources, "bonuses")
    SubElement(resources, "relationships")
    SubElement(resources, "inventory")

    # ------------------------------------------------------------------
    # <state_machines> — empty clocks and tracks
    # ------------------------------------------------------------------
    machines = SubElement(root, "state_machines")
    SubElement(machines, "clocks")
    SubElement(machines, "progress_tracks")

    # ------------------------------------------------------------------
    # <safety_profile>
    # ------------------------------------------------------------------
    profile = SubElement(root, "safety_profile")
    for category in _SAFETY_CATEGORIES:
        status = config.safety.get(category, "green")
        SubElement(profile, "content_category", attrib={
            "name": category,
            "status": status,
        })

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


# ---------------------------------------------------------------------------
# Interactive wizard helpers
# ---------------------------------------------------------------------------


def _ask_choice(prompt_fn: Callable[[str], str], prompt: str, valid: set[str]) -> str:
    """Prompt until user enters a valid choice."""
    while True:
        answer = prompt_fn(prompt).strip()
        if answer in valid:
            return answer


def _ask_int(
    prompt_fn: Callable[[str], str],
    prompt: str,
    lo: int,
    hi: int,
) -> int:
    """Prompt until user enters an integer in [lo, hi]."""
    while True:
        raw = prompt_fn(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            continue
        if lo <= value <= hi:
            return value


def _ask_text(prompt_fn: Callable[[str], str], prompt: str) -> str:
    """Prompt until user enters a non-empty string."""
    while True:
        answer = prompt_fn(prompt).strip()
        if answer:
            return answer


# ---------------------------------------------------------------------------
# run_wizard
# ---------------------------------------------------------------------------


def run_wizard(prompt_fn: Callable[[str], str] = input) -> WizardConfig:
    """Drive the 4-stage campaign creation wizard.

    Args:
        prompt_fn: Callable used for all I/O (defaults to built-in ``input``).
                   Accept an injectable so tests can supply a fake.
                   The callable receives a prompt string and returns a string.

    Returns:
        A fully populated :class:`WizardConfig`.

    Each stage prompts for its fields in order.  Invalid input triggers a
    re-prompt until a valid value is supplied.  Attribute sum > 10 causes the
    whole attribute block to be re-prompted.
    """
    # ------------------------------------------------------------------
    # Stage 1 — System
    # ------------------------------------------------------------------
    title = _ask_text(prompt_fn, "Campaign title: ")
    genre = _ask_text(prompt_fn, "Genre: ")
    tone = _ask_text(prompt_fn, "Tone: ")
    canon_mode = _ask_choice(
        prompt_fn,
        f"Canon mode {sorted(_VALID_CANON_MODES)}: ",
        _VALID_CANON_MODES,
    )

    # ------------------------------------------------------------------
    # Stage 2 — Character
    # ------------------------------------------------------------------
    character_name = _ask_text(prompt_fn, "Character name: ")

    # Attributes with sum constraint — re-prompt the block if sum > 10
    while True:
        edge = _ask_int(prompt_fn, "Edge [1-3]: ", 1, 3)
        heart = _ask_int(prompt_fn, "Heart [1-3]: ", 1, 3)
        iron = _ask_int(prompt_fn, "Iron [1-3]: ", 1, 3)
        shadow = _ask_int(prompt_fn, "Shadow [1-3]: ", 1, 3)
        wits = _ask_int(prompt_fn, "Wits [1-3]: ", 1, 3)
        if edge + heart + iron + shadow + wits <= 10:
            break
        # Sum exceeded — loop back and re-prompt all five attributes

    load = _ask_choice(prompt_fn, f"Load {sorted(_VALID_LOADS)}: ", _VALID_LOADS)

    # ------------------------------------------------------------------
    # Stage 3 — Safety
    # ------------------------------------------------------------------
    safety: dict[str, str] = {}
    for category in _SAFETY_CATEGORIES:
        safety[category] = _ask_choice(
            prompt_fn,
            f"Safety for '{category}' {sorted(_VALID_SAFETY_STATUSES)}: ",
            _VALID_SAFETY_STATUSES,
        )

    orchestration_mode = _ask_choice(
        prompt_fn,
        f"Orchestration mode {sorted(_VALID_ORCHESTRATION_MODES)}: ",
        _VALID_ORCHESTRATION_MODES,
    )

    # ------------------------------------------------------------------
    # Stage 4 — Orchestration
    # ------------------------------------------------------------------
    initial_position = _ask_choice(
        prompt_fn,
        f"Initial position {sorted(_VALID_POSITIONS)}: ",
        _VALID_POSITIONS,
    )
    initial_effect = _ask_choice(
        prompt_fn,
        f"Initial effect {sorted(_VALID_EFFECTS)}: ",
        _VALID_EFFECTS,
    )

    return WizardConfig(
        title=title,
        genre=genre,
        tone=tone,
        canon_mode=canon_mode,
        character_name=character_name,
        edge=edge,
        heart=heart,
        iron=iron,
        shadow=shadow,
        wits=wits,
        load=load,
        safety=safety,
        orchestration_mode=orchestration_mode,
        initial_position=initial_position,
        initial_effect=initial_effect,
    )
