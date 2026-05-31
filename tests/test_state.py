"""Tests for AURPG state model logic."""

from aurpg.state import Clock, ClockType, ProgressTrack, TrackRank


# ---------------------------------------------------------------------------
# Clock.tick
# ---------------------------------------------------------------------------


def test_clock_tick_advances():
    c = Clock("id", "name", ClockType.STANDARD, segments=6, filled=2)
    c.tick()
    assert c.filled == 3


def test_clock_tick_caps_at_segments():
    c = Clock("id", "name", ClockType.DANGER, segments=4, filled=3)
    c.tick(5)
    assert c.filled == 4


def test_clock_tick_negative_clamps_to_zero():
    c = Clock("id", "name", ClockType.STANDARD, segments=6, filled=1)
    c.tick(-99)
    assert c.filled == 0


def test_clock_tick_negative_decrements():
    c = Clock("id", "name", ClockType.STANDARD, segments=6, filled=3)
    c.tick(-1)
    assert c.filled == 2


def test_clock_is_complete():
    c = Clock("id", "name", ClockType.MISSION, segments=4, filled=4)
    assert c.is_complete


def test_clock_remaining():
    c = Clock("id", "name", ClockType.RACING, segments=6, filled=2)
    assert c.remaining == 4


# ---------------------------------------------------------------------------
# ProgressTrack.advance_success — box-based ranks
# ---------------------------------------------------------------------------


def test_advance_troublesome_adds_three_boxes():
    t = ProgressTrack("t1", "Test", TrackRank.TROUBLESOME, boxes_filled=0, ticks_in_current_box=0)
    t.advance_success()
    assert t.boxes_filled == 3
    assert t.ticks_in_current_box == 0


def test_advance_dangerous_adds_two_boxes():
    t = ProgressTrack("t1", "Test", TrackRank.DANGEROUS, boxes_filled=1, ticks_in_current_box=0)
    t.advance_success()
    assert t.boxes_filled == 3
    assert t.ticks_in_current_box == 0


def test_advance_formidable_adds_one_box():
    t = ProgressTrack("t1", "Test", TrackRank.FORMIDABLE, boxes_filled=2, ticks_in_current_box=0)
    t.advance_success()
    assert t.boxes_filled == 3
    assert t.ticks_in_current_box == 0


def test_advance_box_rank_preserves_existing_ticks():
    """Advancing a box-based rank converts existing partial ticks into the total correctly."""
    # boxes_filled=2, ticks=2 → total ticks = 10
    # Formidable adds 4 ticks (1 box) → total = 14 → boxes=3, ticks=2
    t = ProgressTrack("t1", "Test", TrackRank.FORMIDABLE, boxes_filled=2, ticks_in_current_box=2)
    t.advance_success()
    assert t.boxes_filled == 3
    assert t.ticks_in_current_box == 2


def test_advance_dangerous_preserves_partial_ticks():
    # boxes=1, ticks=3 → total=7; Dangerous adds 8 ticks → 15 → boxes=3, ticks=3
    t = ProgressTrack("t1", "Test", TrackRank.DANGEROUS, boxes_filled=1, ticks_in_current_box=3)
    t.advance_success()
    assert t.boxes_filled == 3
    assert t.ticks_in_current_box == 3


# ---------------------------------------------------------------------------
# ProgressTrack.advance_success — tick-based ranks
# ---------------------------------------------------------------------------


def test_advance_extreme_adds_two_ticks():
    t = ProgressTrack("t1", "Test", TrackRank.EXTREME, boxes_filled=0, ticks_in_current_box=0)
    t.advance_success()
    assert t.ticks_in_current_box == 2
    assert t.boxes_filled == 0


def test_advance_epic_adds_one_tick():
    t = ProgressTrack("t1", "Test", TrackRank.EPIC, boxes_filled=0, ticks_in_current_box=0)
    t.advance_success()
    assert t.ticks_in_current_box == 1
    assert t.boxes_filled == 0


def test_advance_tick_overflow_increments_box():
    # 3 existing ticks + 2 extreme ticks = 5 → 1 box, 1 tick
    t = ProgressTrack("t1", "Test", TrackRank.EXTREME, boxes_filled=0, ticks_in_current_box=3)
    t.advance_success()
    assert t.boxes_filled == 1
    assert t.ticks_in_current_box == 1


# ---------------------------------------------------------------------------
# ProgressTrack cap at maximum
# ---------------------------------------------------------------------------


def test_advance_caps_at_max_boxes():
    t = ProgressTrack("t1", "Test", TrackRank.TROUBLESOME, boxes_filled=9, ticks_in_current_box=0)
    t.advance_success()
    assert t.boxes_filled == 10
    assert t.ticks_in_current_box == 0


def test_advance_caps_and_no_overflow_ticks():
    # Epic: boxes=10, ticks=0 → already at max; adding 1 tick should stay at max, ticks=0
    t = ProgressTrack("t1", "Test", TrackRank.EPIC, boxes_filled=10, ticks_in_current_box=0)
    t.advance_success()
    assert t.boxes_filled == 10
    assert t.ticks_in_current_box == 0


def test_advance_extreme_near_cap_no_stray_ticks():
    # boxes=9, ticks=3 → total=39; Extreme adds 2 → 41 → cap at 40 → boxes=10, ticks=0
    t = ProgressTrack("t1", "Test", TrackRank.EXTREME, boxes_filled=9, ticks_in_current_box=3)
    t.advance_success()
    assert t.boxes_filled == 10
    assert t.ticks_in_current_box == 0


# ---------------------------------------------------------------------------
# progress_score
# ---------------------------------------------------------------------------


def test_progress_score_equals_boxes_filled():
    t = ProgressTrack("t1", "Test", TrackRank.FORMIDABLE, boxes_filled=5, ticks_in_current_box=2)
    assert t.progress_score == 5
