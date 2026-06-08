"""Pre-LLM safety command parser for AURPG.

Intercepts safety commands in player input BEFORE the turn reaches the LLM,
providing immediate out-of-character acknowledgements and state updates.

Supported commands (case-insensitive, allow surrounding whitespace/punctuation):

    [X-Card]         — freeze and remove flagged content
    [Rewind]         — go back to an earlier story moment
    [Fast-Forward]   — skip ahead past difficult content
    [Pause]          — open an out-of-character space
    !enforce_hard_stop — fully exit fiction; highest-severity stop

Typical usage::

    command = detect_safety_command(player_input)
    if command is not None:
        response = build_ooc_response(command, player_note=player_input)
        new_state = apply_safety_command(command, session.safety_state)
        # …route OOC response, update state, do NOT send turn to LLM
"""

from __future__ import annotations

import copy
import re
from enum import Enum
from typing import Any

__all__ = [
    "SafetyCommand",
    "detect_safety_command",
    "build_ooc_response",
    "apply_safety_command",
]

# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


class SafetyCommand(str, Enum):
    """Enumeration of recognised in-session safety commands.

    Values are string-typed so they serialise cleanly into JSON / XML logs.
    """

    X_CARD = "x_card"
    REWIND = "rewind"
    FAST_FORWARD = "fast_forward"
    PAUSE = "pause"
    HARD_STOP = "hard_stop"


# ---------------------------------------------------------------------------
# Detection patterns — ordered by priority (first match wins)
# ---------------------------------------------------------------------------

# Each entry is (SafetyCommand, compiled_pattern).
# Patterns are case-insensitive and allow arbitrary surrounding characters so
# commands embedded inside prose are still caught.
_PATTERNS: list[tuple[SafetyCommand, re.Pattern[str]]] = [
    (SafetyCommand.X_CARD, re.compile(r"\[x-card\]", re.IGNORECASE)),
    (SafetyCommand.REWIND, re.compile(r"\[rewind\]", re.IGNORECASE)),
    (SafetyCommand.FAST_FORWARD, re.compile(r"\[fast-forward\]", re.IGNORECASE)),
    (SafetyCommand.PAUSE, re.compile(r"\[pause\]", re.IGNORECASE)),
    (SafetyCommand.HARD_STOP, re.compile(r"!enforce_hard_stop", re.IGNORECASE)),
]


def detect_safety_command(player_input: str | None) -> SafetyCommand | None:
    """Scan *player_input* for a safety command and return the first one found.

    Matching is case-insensitive and commands may appear anywhere within the
    input string (embedded in prose, surrounded by punctuation, etc.).

    Args:
        player_input: Raw text from the player before any LLM processing.

    Returns:
        The first :class:`SafetyCommand` found, scanning left-to-right through
        the input.  Returns ``None`` when no safety command is present.
    """
    if not player_input or not player_input.strip():
        return None

    # Find the position of each matching pattern so we can honour "first wins".
    earliest_pos: int | None = None
    earliest_command: SafetyCommand | None = None

    for command, pattern in _PATTERNS:
        match = pattern.search(player_input)
        if match is None:
            continue
        pos = match.start()
        if earliest_pos is None or pos < earliest_pos:
            earliest_pos = pos
            earliest_command = command

    return earliest_command


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_command_tokens(text: str) -> str:
    """Remove all safety command tokens from *text* and collapse extra whitespace.

    Runs every pattern in ``_PATTERNS`` over the text and deletes any matches,
    then strips leading/trailing whitespace from the result.
    """
    result = text
    for _cmd, pattern in _PATTERNS:
        result = pattern.sub("", result)
    # Collapse multiple spaces left behind by removal
    result = re.sub(r" {2,}", " ", result)
    return result.strip()


# ---------------------------------------------------------------------------
# OOC response builder
# ---------------------------------------------------------------------------

_OOC_TEMPLATES: dict[SafetyCommand, str] = {
    SafetyCommand.X_CARD: (
        "[OOC — Safety] The X-Card has been called. Fiction is frozen immediately. "
        "The flagged content has been removed and set aside — no explanation needed. "
        "{note_clause}"
        "We can redirect from here whenever you're ready. "
        "Where would you like the story to go next?"
    ),
    SafetyCommand.REWIND: (
        "[OOC — Safety] Rewind acknowledged. We can step back to an earlier moment in the story. "
        "{note_clause}"
        "How far back would you like to go — which scene or beat should we return to?"
    ),
    SafetyCommand.FAST_FORWARD: (
        "[OOC — Safety] Fast-Forward acknowledged. We can skip past this section entirely. "
        "{note_clause}"
        "Where should we pick the story back up — which scene or moment do you want to jump ahead to?"
    ),
    SafetyCommand.PAUSE: (
        "[OOC — Safety] Paused. The fiction is on hold and this is a safe out-of-character space. "
        "{note_clause}"
        "Take all the time you need. Just say the word whenever you're ready to resume."
    ),
    SafetyCommand.HARD_STOP: (
        "[OOC — Safety] Hard stop acknowledged. We have fully exited the fiction — no narrative "
        "framing, no in-character voice. "
        "{note_clause}"
        "Your wellbeing comes first. Please check in with yourself; aftercare resources are available "
        "if helpful. I'm here whenever and however you need."
    ),
}


def build_ooc_response(command: SafetyCommand, player_note: str = "") -> str:
    """Build an out-of-character acknowledgement for the given safety command.

    Args:
        command:     The :class:`SafetyCommand` that was detected.
        player_note: Optional free-text context from the player's message.
                     Safety command tokens (e.g. ``[X-Card]``) are stripped
                     automatically before embedding the note so the raw sigil
                     is never echoed back to the player.  When a non-empty
                     note remains after stripping it is woven into the
                     acknowledgement so the player feels heard.

    Returns:
        A non-empty OOC acknowledgement string appropriate for the command.
    """
    template = _OOC_TEMPLATES[command]
    note_clause = ""
    if player_note and player_note.strip():
        cleaned = _strip_command_tokens(player_note)
        stripped = cleaned.rstrip(".,!?")
        if stripped:
            note_clause = f'I heard you: "{stripped}." '

    return template.format(note_clause=note_clause)


# ---------------------------------------------------------------------------
# State update
# ---------------------------------------------------------------------------


def apply_safety_command(command: SafetyCommand, safety_state: dict[str, Any]) -> dict[str, Any]:
    """Return a new safety-state dict reflecting the effect of *command*.

    Does **not** mutate the input dict (uses :func:`copy.deepcopy`, so nested
    mutable values are fully independent of the original).  All keys from
    *safety_state* are preserved; only the relevant fields are updated.

    State update rules:

    * ``X_CARD`` / ``HARD_STOP``: ``hard_stop=True``, ``pause=True``,
      ``intensity_check="pending"``
    * ``PAUSE``: ``pause=True``, ``intensity_check="pending"``
    * ``REWIND`` / ``FAST_FORWARD``: ``intensity_check="pending"`` only;
      ``hard_stop`` and ``pause`` are left unchanged.

    Args:
        command:      The :class:`SafetyCommand` to apply.
        safety_state: Current safety state dict (e.g. from
                      :class:`~aurpg.state.SafetyState` serialised to dict).

    Returns:
        A new dict with updated fields.
    """
    new_state: dict[str, Any] = copy.deepcopy(safety_state)

    if command in (SafetyCommand.X_CARD, SafetyCommand.HARD_STOP):
        new_state["hard_stop"] = True
        new_state["pause"] = True
        new_state["intensity_check"] = "pending"
    elif command == SafetyCommand.PAUSE:
        new_state["pause"] = True
        new_state["intensity_check"] = "pending"
    elif command in (SafetyCommand.REWIND, SafetyCommand.FAST_FORWARD):
        new_state["intensity_check"] = "pending"

    return new_state
