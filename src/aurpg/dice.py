"""Dice oracle for AURPG.

Provides seeded-deterministic and high-entropy seeded roll functions for all
dice expressions used by the system prompt spec.  Every public function accepts
``rng`` as a keyword-only argument so tests can inject a seeded
:class:`random.Random` instance and get reproducible sequences.

Typical usage::

    rng = make_rng()                          # high-entropy seeded (live play)
    action = roll_action(attribute=2, bonuses=1, rng=rng)
    c1, c2 = roll_challenge(rng=rng)
    squad  = roll_squad(n=3, rng=rng)

For tests::

    rng = make_rng(seed=42)                   # deterministic
    action = roll_action(attribute=2, bonuses=0, rng=rng)
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

__all__ = [
    "OutcomeTier",
    "ActionRoll",
    "SquadRoll",
    "RNG",
    "make_rng",
    "roll_action",
    "roll_challenge",
    "roll_squad",
]

# ---------------------------------------------------------------------------
# RNG type alias / protocol
# ---------------------------------------------------------------------------


class RNG(Protocol):
    """Minimal interface expected from any RNG object passed to roll functions."""

    def randint(self, a: int, b: int) -> int:  # noqa: D102
        ...


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OutcomeTier(str, Enum):
    """Resolution outcome tiers shared by squad (pool) mode.

    Values are string-typed so they serialise cleanly into JSON / XML logs.
    """

    CRITICAL = "critical"
    STRONG_HIT = "strong_hit"
    WEAK_HIT = "weak_hit"
    MISS = "miss"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActionRoll:
    """Result of a solo-mode action roll (1d6 + Attribute + Bonuses, capped at 10).

    Attributes:
        die_face:     Raw face of the 1d6 (1–6), before adding attribute or bonuses.
        action_score: Final capped value ``min(die_face + attribute + bonuses, 10)``.
    """

    die_face: int
    action_score: int


@dataclass(frozen=True, slots=True)
class SquadRoll:
    """Result of a squad-mode pool roll (Nd6, N = 1–4).

    Attributes:
        dice:    Tuple of raw die faces (1–6 each), length equals *n* passed to
                 :func:`roll_squad`.
        outcome: Resolved :class:`OutcomeTier` based on the highest die and
                 whether multiple 6s were rolled.
    """

    dice: tuple[int, ...]
    outcome: OutcomeTier


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_rng(seed: int | None = None) -> random.Random:
    """Return a :class:`random.Random` instance suitable for die rolling.

    Args:
        seed: Integer seed for a fully deterministic sequence.  Pass ``None``
              (default) to seed from ``os.urandom`` so live play is
              cryptographically unpredictable.

    Returns:
        A :class:`random.Random` instance.  When *seed* is ``None`` the
        instance is seeded via :func:`os.urandom`, giving high-entropy seeded
        unpredictability in normal play without requiring any external library.
    """
    if seed is None:
        # Seed from os.urandom for high-entropy, unpredictable seeding.
        entropy = int.from_bytes(os.urandom(8), "big")
        return random.Random(entropy)
    return random.Random(seed)


# ---------------------------------------------------------------------------
# Roll functions
# ---------------------------------------------------------------------------


def roll_action(attribute: int, bonuses: int, *, rng: RNG) -> ActionRoll:
    """Roll a solo-mode action: 1d6 + *attribute* + *bonuses*, capped at 10.

    Args:
        attribute: The relevant attribute value (0–4 in normal play).
        bonuses:   Sum of situational bonuses (+add values, gear, etc.).
        rng:       RNG instance to use; must be keyword-only to allow test
                   injection.

    Returns:
        :class:`ActionRoll` with the raw ``die_face`` (1–6) and the final
        ``action_score`` (1–10).
    """
    die_face = rng.randint(1, 6)
    action_score = min(die_face + attribute + bonuses, 10)
    return ActionRoll(die_face=die_face, action_score=action_score)


def roll_challenge(*, rng: RNG) -> tuple[int, int]:
    """Roll two independent 1d10 challenge dice.

    Args:
        rng: RNG instance to use; must be keyword-only.

    Returns:
        A plain ``(d1, d2)`` tuple of two integers in [1, 10].  Using a plain
        tuple keeps the call site concise (unpacking is natural) while staying
        consistent with the spec's "two independent challenge dice" framing.
    """
    d1 = rng.randint(1, 10)
    d2 = rng.randint(1, 10)
    return (d1, d2)


def roll_squad(n: int, *, rng: RNG) -> SquadRoll:
    """Roll a squad-mode Nd6 pool (N = 1–4) and resolve the outcome tier.

    Outcome rules (highest die, with multi-6 check first):

    * Two or more 6s → :attr:`OutcomeTier.CRITICAL`
    * Exactly one 6  → :attr:`OutcomeTier.STRONG_HIT`
    * Highest die 4–5 → :attr:`OutcomeTier.WEAK_HIT`
    * Highest die 1–3 → :attr:`OutcomeTier.MISS`

    Args:
        n:   Number of dice in the pool (1–4).
        rng: RNG instance to use; must be keyword-only.

    Returns:
        :class:`SquadRoll` with the raw ``dice`` tuple and resolved
        ``outcome``.

    Raises:
        ValueError: If *n* is outside the range 1–4.
    """
    if not (1 <= n <= 4):
        raise ValueError(f"Squad pool size must be 1–4, got {n!r}")

    dice = tuple(rng.randint(1, 6) for _ in range(n))

    count_sixes = dice.count(6)
    highest = max(dice)

    if count_sixes >= 2:
        outcome = OutcomeTier.CRITICAL
    elif count_sixes == 1:
        outcome = OutcomeTier.STRONG_HIT
    elif highest >= 4:
        outcome = OutcomeTier.WEAK_HIT
    else:
        outcome = OutcomeTier.MISS

    return SquadRoll(dice=dice, outcome=outcome)
