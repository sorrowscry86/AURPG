"""Parse LLM ledger blocks into state mutation dicts.

The ledger format (as defined in the system prompt) is a compact multi-field block:

    [SCENE] scene-003 | [TIME] 02:14 | [OBJ] Extract witness archive
    [STRESS] 4/10 | [MOMENTUM] 6 | [HARM] bruised_ribs (-1 edge)
    [CLOCKS] Archive Extraction 5→6/8 | Alarm Sweep 3→4/6

All parsing is non-fatal — unknown or malformed tags are silently skipped so a
partially-formed ledger never crashes the turn loop.
"""

from __future__ import annotations

import re
from typing import TypedDict

__all__ = ["parse_ledger", "ClockMutation", "LedgerMutations"]


class ClockMutation(TypedDict):
    label: str
    filled: int
    segments: int


class LedgerMutations(TypedDict, total=False):
    stress: int
    momentum: int
    harm: str
    scene_id: str
    time_marker: str
    objective: str
    clocks: list[ClockMutation]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_ledger(ledger_block: str | None) -> LedgerMutations:
    """Parse a ledger block string into a :class:`LedgerMutations` dict.

    Each field is extracted independently via regex so a malformed entry
    for one field doesn't prevent extraction of the others.

    Args:
        ledger_block: Newline-joined ledger lines as returned by
                      ``EngineResponse.ledger_block``, or ``None``.

    Returns:
        A (possibly empty) :class:`LedgerMutations` dict.  Only keys that
        were successfully parsed are present.
    """
    if not ledger_block:
        return {}

    mutations: LedgerMutations = {}
    text = ledger_block

    # [STRESS] n/10  or  n→m/10  — capture the final value
    m = re.search(r"\[STRESS\]\s+(?:\d+\s*→\s*)?(\d+)/\d+", text)
    if m:
        mutations["stress"] = max(0, min(10, int(m.group(1))))

    # [MOMENTUM] n  or  n→m  — can be negative
    m = re.search(r"\[MOMENTUM\]\s+(?:-?\d+\s*→\s*)?(-?\d+)", text)
    if m:
        mutations["momentum"] = max(-6, min(10, int(m.group(1))))

    # [HARM] label  or  label (penalty)  — strip trailing parenthesised penalty
    m = re.search(r"\[HARM\]\s+([^|\n]+)", text)
    if m:
        harm_raw = m.group(1).strip()
        harm_clean = re.sub(r"\s*\([^)]*\)\s*$", "", harm_raw).strip()
        mutations["harm"] = harm_clean

    # [SCENE] scene_id  (first non-space token)
    m = re.search(r"\[SCENE\]\s+(\S+)", text)
    if m:
        mutations["scene_id"] = m.group(1)

    # [TIME] marker  (up to next pipe or newline)
    m = re.search(r"\[TIME\]\s+([^|\n]+)", text)
    if m:
        mutations["time_marker"] = m.group(1).strip()

    # [OBJ] summary  (up to next pipe or newline)
    m = re.search(r"\[OBJ\]\s+([^|\n]+)", text)
    if m:
        mutations["objective"] = m.group(1).strip()

    # [CLOCKS] entries — the rest of the line, pipe-separated
    m = re.search(r"^\[CLOCKS\]\s+(.+)$", text, re.MULTILINE)
    if m:
        clock_mutations = _parse_clocks(m.group(1))
        if clock_mutations:
            mutations["clocks"] = clock_mutations

    return mutations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches: "Label text n→m/segments FULL?" or "Label text n/segments FULL?"
_CLOCK_ENTRY_RE = re.compile(
    r"^(.*?)\s+(?:\d+\s*→\s*)?(\d+)/(\d+)(?:\s+FULL)?\s*$"
)


def _parse_clocks(clocks_str: str) -> list[ClockMutation]:
    """Parse the clocks segment: ``'Name n→m/s | Name n/s'``."""
    results: list[ClockMutation] = []
    for entry in re.split(r"\s*\|\s*", clocks_str):
        entry = entry.strip()
        if not entry:
            continue
        mm = _CLOCK_ENTRY_RE.match(entry)
        if mm:
            results.append(
                ClockMutation(
                    label=mm.group(1).strip(),
                    filled=int(mm.group(2)),
                    segments=int(mm.group(3)),
                )
            )
    return results
