"""Tests for AURPG dice oracle module."""

from __future__ import annotations

import pytest

from aurpg.dice import (
    ActionRoll,
    OutcomeTier,
    SquadRoll,
    make_rng,
    roll_action,
    roll_challenge,
    roll_squad,
)


# ---------------------------------------------------------------------------
# make_rng
# ---------------------------------------------------------------------------


def test_make_rng_seeded_returns_random_instance():
    rng = make_rng(seed=42)
    assert rng is not None


def test_make_rng_seeded_deterministic():
    """Two RNGs with the same seed must produce identical sequences."""
    rng1 = make_rng(seed=99)
    rng2 = make_rng(seed=99)
    results1 = [rng1.randint(1, 6) for _ in range(20)]
    results2 = [rng2.randint(1, 6) for _ in range(20)]
    assert results1 == results2


def test_make_rng_different_seeds_different_sequences():
    rng_a = make_rng(seed=1)
    rng_b = make_rng(seed=2)
    seq_a = [rng_a.randint(1, 10) for _ in range(20)]
    seq_b = [rng_b.randint(1, 10) for _ in range(20)]
    assert seq_a != seq_b


def test_make_rng_no_seed_returns_random_instance():
    rng = make_rng()
    assert rng is not None


# ---------------------------------------------------------------------------
# roll_action — dataclass structure
# ---------------------------------------------------------------------------


def test_roll_action_returns_action_roll():
    rng = make_rng(seed=0)
    result = roll_action(attribute=2, bonuses=1, rng=rng)
    assert isinstance(result, ActionRoll)


def test_roll_action_has_die_face_and_score():
    rng = make_rng(seed=0)
    result = roll_action(attribute=2, bonuses=0, rng=rng)
    assert hasattr(result, "die_face")
    assert hasattr(result, "action_score")


def test_roll_action_die_face_in_range():
    """Raw 1d6 face must be 1–6 regardless of attribute or bonuses."""
    rng = make_rng(seed=7)
    for _ in range(100):
        result = roll_action(attribute=0, bonuses=0, rng=rng)
        assert 1 <= result.die_face <= 6


def test_roll_action_score_equals_die_plus_attribute_plus_bonuses():
    """When total ≤ 10, score = die_face + attribute + bonuses."""
    # Seed chosen to keep total ≤ 10 (attribute=1, bonuses=0, die ≤ 9 needed)
    rng = make_rng(seed=0)
    result = roll_action(attribute=1, bonuses=0, rng=rng)
    raw_total = result.die_face + 1 + 0
    if raw_total <= 10:
        assert result.action_score == raw_total
    else:
        assert result.action_score == 10


def test_roll_action_score_capped_at_10():
    """action_score must never exceed 10."""
    rng = make_rng(seed=0)
    for _ in range(200):
        result = roll_action(attribute=4, bonuses=4, rng=rng)
        assert result.action_score <= 10


def test_roll_action_score_minimum_is_one():
    """With attribute=0 and bonuses=0, lowest possible is die face (1–6), always ≥ 1."""
    rng = make_rng(seed=0)
    for _ in range(50):
        result = roll_action(attribute=0, bonuses=0, rng=rng)
        assert result.action_score >= 1


def test_roll_action_zero_attribute_zero_bonus():
    """Score == die_face when attribute=0 and bonuses=0 (and die ≤ 6, always ≤ 10)."""
    rng = make_rng(seed=42)
    result = roll_action(attribute=0, bonuses=0, rng=rng)
    assert result.action_score == result.die_face


def test_roll_action_large_attribute_caps():
    """attribute=3, bonuses=4: die face 1–6 → raw 8–13 → always capped to 10 when ≥ 10."""
    rng = make_rng(seed=5)
    for _ in range(100):
        result = roll_action(attribute=3, bonuses=4, rng=rng)
        assert result.action_score <= 10
        # raw uncapped value
        uncapped = result.die_face + 3 + 4
        assert result.action_score == min(uncapped, 10)


# ---------------------------------------------------------------------------
# roll_challenge — structure and ranges
# ---------------------------------------------------------------------------


def test_roll_challenge_returns_tuple_of_two_ints():
    rng = make_rng(seed=0)
    result = roll_challenge(rng=rng)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(v, int) for v in result)


def test_roll_challenge_each_die_in_range():
    rng = make_rng(seed=11)
    for _ in range(200):
        d1, d2 = roll_challenge(rng=rng)
        assert 1 <= d1 <= 10
        assert 1 <= d2 <= 10


def test_roll_challenge_dice_independent():
    """Over many rolls the two dice should not always be equal (independence check)."""
    rng = make_rng(seed=13)
    pairs = [roll_challenge(rng=rng) for _ in range(50)]
    assert not all(d1 == d2 for d1, d2 in pairs)


# ---------------------------------------------------------------------------
# roll_squad — dataclass structure
# ---------------------------------------------------------------------------


def test_roll_squad_returns_squad_roll():
    rng = make_rng(seed=0)
    result = roll_squad(n=2, rng=rng)
    assert isinstance(result, SquadRoll)


def test_roll_squad_has_dice_and_outcome():
    rng = make_rng(seed=0)
    result = roll_squad(n=2, rng=rng)
    assert hasattr(result, "dice")
    assert hasattr(result, "outcome")


def test_roll_squad_n1_returns_one_die():
    rng = make_rng(seed=0)
    result = roll_squad(n=1, rng=rng)
    assert len(result.dice) == 1


def test_roll_squad_n2_returns_two_dice():
    rng = make_rng(seed=0)
    result = roll_squad(n=2, rng=rng)
    assert len(result.dice) == 2


def test_roll_squad_n3_returns_three_dice():
    rng = make_rng(seed=0)
    result = roll_squad(n=3, rng=rng)
    assert len(result.dice) == 3


def test_roll_squad_n4_returns_four_dice():
    rng = make_rng(seed=0)
    result = roll_squad(n=4, rng=rng)
    assert len(result.dice) == 4


def test_roll_squad_all_dice_in_range():
    rng = make_rng(seed=22)
    for n in range(1, 5):
        for _ in range(50):
            result = roll_squad(n=n, rng=rng)
            for die in result.dice:
                assert 1 <= die <= 6


def test_roll_squad_outcome_is_outcome_tier():
    rng = make_rng(seed=0)
    result = roll_squad(n=2, rng=rng)
    assert isinstance(result.outcome, OutcomeTier)


# ---------------------------------------------------------------------------
# OutcomeTier enum
# ---------------------------------------------------------------------------


def test_outcome_tier_members_exist():
    assert hasattr(OutcomeTier, "CRITICAL")
    assert hasattr(OutcomeTier, "STRONG_HIT")
    assert hasattr(OutcomeTier, "WEAK_HIT")
    assert hasattr(OutcomeTier, "MISS")


# ---------------------------------------------------------------------------
# roll_squad — outcome tier correctness
# ---------------------------------------------------------------------------


def _squad_with_fixed_dice(faces: list[int]) -> SquadRoll:
    """Helper: create a SquadRoll using a pre-determined sequence of die faces."""
    sequence = iter(faces)
    mock_rng = type("MockRNG", (), {"randint": lambda self, *_: next(sequence)})()
    return roll_squad(n=len(faces), rng=mock_rng)


def test_roll_squad_two_sixes_is_critical():
    result = _squad_with_fixed_dice([6, 6])
    assert result.outcome == OutcomeTier.CRITICAL


def test_roll_squad_three_sixes_is_critical():
    result = _squad_with_fixed_dice([6, 6, 6])
    assert result.outcome == OutcomeTier.CRITICAL


def test_roll_squad_four_sixes_is_critical():
    result = _squad_with_fixed_dice([6, 6, 6, 6])
    assert result.outcome == OutcomeTier.CRITICAL


def test_roll_squad_exactly_one_six_is_strong_hit():
    result = _squad_with_fixed_dice([6, 3, 2])
    assert result.outcome == OutcomeTier.STRONG_HIT


def test_roll_squad_one_six_with_others_is_strong_hit():
    result = _squad_with_fixed_dice([1, 6, 4])
    assert result.outcome == OutcomeTier.STRONG_HIT


def test_roll_squad_highest_five_is_weak_hit():
    result = _squad_with_fixed_dice([5, 3, 2])
    assert result.outcome == OutcomeTier.WEAK_HIT


def test_roll_squad_highest_four_is_weak_hit():
    result = _squad_with_fixed_dice([4, 2, 1])
    assert result.outcome == OutcomeTier.WEAK_HIT


def test_roll_squad_highest_three_is_miss():
    result = _squad_with_fixed_dice([3, 1, 2])
    assert result.outcome == OutcomeTier.MISS


def test_roll_squad_highest_one_is_miss():
    result = _squad_with_fixed_dice([1])
    assert result.outcome == OutcomeTier.MISS


def test_roll_squad_n1_single_six_is_strong_hit():
    """N=1 with a single 6 is exactly one 6 → STRONG_HIT (not CRITICAL)."""
    result = _squad_with_fixed_dice([6])
    assert result.outcome == OutcomeTier.STRONG_HIT


def test_roll_squad_n1_five_is_weak_hit():
    result = _squad_with_fixed_dice([5])
    assert result.outcome == OutcomeTier.WEAK_HIT


def test_roll_squad_n1_three_is_miss():
    result = _squad_with_fixed_dice([3])
    assert result.outcome == OutcomeTier.MISS


def test_roll_squad_n2_one_six_one_five_strong_hit():
    result = _squad_with_fixed_dice([6, 5])
    assert result.outcome == OutcomeTier.STRONG_HIT


def test_roll_squad_n4_mixed_highest_four_weak_hit():
    result = _squad_with_fixed_dice([4, 3, 2, 1])
    assert result.outcome == OutcomeTier.WEAK_HIT


# ---------------------------------------------------------------------------
# Seeded determinism end-to-end
# ---------------------------------------------------------------------------


def test_action_roll_seeded_deterministic():
    rng1 = make_rng(seed=555)
    rng2 = make_rng(seed=555)
    r1 = [roll_action(attribute=2, bonuses=1, rng=rng1) for _ in range(20)]
    r2 = [roll_action(attribute=2, bonuses=1, rng=rng2) for _ in range(20)]
    assert [(r.die_face, r.action_score) for r in r1] == [(r.die_face, r.action_score) for r in r2]


def test_challenge_roll_seeded_deterministic():
    rng1 = make_rng(seed=777)
    rng2 = make_rng(seed=777)
    r1 = [roll_challenge(rng=rng1) for _ in range(20)]
    r2 = [roll_challenge(rng=rng2) for _ in range(20)]
    assert r1 == r2


def test_squad_roll_seeded_deterministic():
    rng1 = make_rng(seed=888)
    rng2 = make_rng(seed=888)
    r1 = [roll_squad(n=3, rng=rng1) for _ in range(20)]
    r2 = [roll_squad(n=3, rng=rng2) for _ in range(20)]
    assert [(r.dice, r.outcome) for r in r1] == [(r.dice, r.outcome) for r in r2]


# ---------------------------------------------------------------------------
# Keyword-only rng enforcement
# ---------------------------------------------------------------------------


def test_roll_action_rng_is_keyword_only():
    """Passing rng as positional should raise TypeError."""
    rng = make_rng(seed=0)
    with pytest.raises(TypeError):
        roll_action(2, 0, rng)  # type: ignore[call-arg]


def test_roll_challenge_rng_is_keyword_only():
    rng = make_rng(seed=0)
    with pytest.raises(TypeError):
        roll_challenge(rng)  # type: ignore[call-arg]


def test_roll_squad_rng_is_keyword_only():
    rng = make_rng(seed=0)
    with pytest.raises(TypeError):
        roll_squad(2, rng)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# roll_squad — out-of-range n raises ValueError
# ---------------------------------------------------------------------------


def test_roll_squad_n0_raises_value_error():
    """n=0 is below the valid range (1–4) and must raise ValueError."""
    rng = make_rng(seed=0)
    with pytest.raises(ValueError):
        roll_squad(n=0, rng=rng)


def test_roll_squad_n5_raises_value_error():
    """n=5 is above the valid range (1–4) and must raise ValueError."""
    rng = make_rng(seed=0)
    with pytest.raises(ValueError):
        roll_squad(n=5, rng=rng)


def test_roll_squad_negative_n_raises_value_error():
    """Negative n is outside the valid range (1–4) and must raise ValueError."""
    rng = make_rng(seed=0)
    with pytest.raises(ValueError):
        roll_squad(n=-1, rng=rng)
