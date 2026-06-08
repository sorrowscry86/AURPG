"""Tests for AURPG safety command parser (TDD — tests written before implementation)."""

from __future__ import annotations

import pytest

from aurpg.safety import SafetyCommand, apply_safety_command, build_ooc_response, detect_safety_command


# ---------------------------------------------------------------------------
# SafetyCommand enum
# ---------------------------------------------------------------------------


def test_safety_command_members_exist():
    assert hasattr(SafetyCommand, "X_CARD")
    assert hasattr(SafetyCommand, "REWIND")
    assert hasattr(SafetyCommand, "FAST_FORWARD")
    assert hasattr(SafetyCommand, "PAUSE")
    assert hasattr(SafetyCommand, "HARD_STOP")


def test_safety_command_is_str_enum():
    """SafetyCommand values must be strings (str, Enum)."""
    for member in SafetyCommand:
        assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# detect_safety_command — canonical forms
# ---------------------------------------------------------------------------


def test_detect_x_card_canonical():
    assert detect_safety_command("[X-Card]") == SafetyCommand.X_CARD


def test_detect_rewind_canonical():
    assert detect_safety_command("[Rewind]") == SafetyCommand.REWIND


def test_detect_fast_forward_canonical():
    assert detect_safety_command("[Fast-Forward]") == SafetyCommand.FAST_FORWARD


def test_detect_pause_canonical():
    assert detect_safety_command("[Pause]") == SafetyCommand.PAUSE


def test_detect_hard_stop_canonical():
    assert detect_safety_command("!enforce_hard_stop") == SafetyCommand.HARD_STOP


# ---------------------------------------------------------------------------
# detect_safety_command — case-insensitivity
# ---------------------------------------------------------------------------


def test_detect_x_card_lowercase():
    assert detect_safety_command("[x-card]") == SafetyCommand.X_CARD


def test_detect_x_card_uppercase():
    assert detect_safety_command("[X-CARD]") == SafetyCommand.X_CARD


def test_detect_x_card_mixed_case():
    assert detect_safety_command("[x-Card]") == SafetyCommand.X_CARD


def test_detect_rewind_uppercase():
    assert detect_safety_command("[REWIND]") == SafetyCommand.REWIND


def test_detect_rewind_lowercase():
    assert detect_safety_command("[rewind]") == SafetyCommand.REWIND


def test_detect_fast_forward_uppercase():
    assert detect_safety_command("[FAST-FORWARD]") == SafetyCommand.FAST_FORWARD


def test_detect_fast_forward_lowercase():
    assert detect_safety_command("[fast-forward]") == SafetyCommand.FAST_FORWARD


def test_detect_pause_uppercase():
    assert detect_safety_command("[PAUSE]") == SafetyCommand.PAUSE


def test_detect_pause_lowercase():
    assert detect_safety_command("[pause]") == SafetyCommand.PAUSE


def test_detect_hard_stop_uppercase():
    assert detect_safety_command("!ENFORCE_HARD_STOP") == SafetyCommand.HARD_STOP


def test_detect_hard_stop_mixed_case():
    assert detect_safety_command("!Enforce_Hard_Stop") == SafetyCommand.HARD_STOP


# ---------------------------------------------------------------------------
# detect_safety_command — embedded in longer player input
# ---------------------------------------------------------------------------


def test_detect_x_card_embedded_in_sentence():
    result = detect_safety_command("I need to call [X-Card] right now, please stop.")
    assert result == SafetyCommand.X_CARD


def test_detect_rewind_embedded_in_sentence():
    result = detect_safety_command("Can we use [Rewind] to go back to before the fight?")
    assert result == SafetyCommand.REWIND


def test_detect_fast_forward_embedded_in_sentence():
    result = detect_safety_command("Let's just [Fast-Forward] past this part.")
    assert result == SafetyCommand.FAST_FORWARD


def test_detect_pause_embedded_in_sentence():
    result = detect_safety_command("Hold on, [Pause] — I need a minute.")
    assert result == SafetyCommand.PAUSE


def test_detect_hard_stop_embedded_in_sentence():
    result = detect_safety_command("Please !enforce_hard_stop, I'm done for tonight.")
    assert result == SafetyCommand.HARD_STOP


def test_detect_command_with_leading_whitespace():
    assert detect_safety_command("   [X-Card]") == SafetyCommand.X_CARD


def test_detect_command_with_trailing_whitespace():
    assert detect_safety_command("[Pause]   ") == SafetyCommand.PAUSE


def test_detect_command_with_surrounding_punctuation():
    assert detect_safety_command("([X-Card]!)") == SafetyCommand.X_CARD


# ---------------------------------------------------------------------------
# detect_safety_command — returns None when no command present
# ---------------------------------------------------------------------------


def test_detect_returns_none_for_normal_input():
    assert detect_safety_command("I draw my sword and charge the guard.") is None


def test_detect_returns_none_for_empty_string():
    assert detect_safety_command("") is None


def test_detect_returns_none_for_whitespace_only():
    assert detect_safety_command("   ") is None


def test_detect_returns_none_for_partial_bracket_match():
    """Partial command names without proper structure should not match."""
    assert detect_safety_command("[X-Ca]") is None


def test_detect_returns_none_for_unbracketed_keyword():
    """'Rewind' without brackets should not match [Rewind]."""
    assert detect_safety_command("Let me rewind what happened.") is None


def test_detect_returns_none_for_enforce_without_bang():
    """enforce_hard_stop without the ! prefix should not match."""
    assert detect_safety_command("enforce_hard_stop") is None


# ---------------------------------------------------------------------------
# detect_safety_command — first command wins when multiple present
# ---------------------------------------------------------------------------


def test_multiple_commands_first_wins_x_card_before_pause():
    result = detect_safety_command("[X-Card] and also [Pause]")
    assert result == SafetyCommand.X_CARD


def test_multiple_commands_first_wins_pause_before_rewind():
    result = detect_safety_command("[Pause] — actually [Rewind]")
    assert result == SafetyCommand.PAUSE


def test_multiple_commands_first_wins_hard_stop_before_fast_forward():
    result = detect_safety_command("!enforce_hard_stop then maybe [Fast-Forward]")
    assert result == SafetyCommand.HARD_STOP


def test_multiple_commands_first_wins_rewind_before_hard_stop():
    result = detect_safety_command("[Rewind] or !enforce_hard_stop")
    assert result == SafetyCommand.REWIND


# ---------------------------------------------------------------------------
# build_ooc_response — non-empty for each command
# ---------------------------------------------------------------------------


def test_build_ooc_response_x_card_returns_string():
    response = build_ooc_response(SafetyCommand.X_CARD)
    assert isinstance(response, str)
    assert len(response) > 0


def test_build_ooc_response_rewind_returns_string():
    response = build_ooc_response(SafetyCommand.REWIND)
    assert isinstance(response, str)
    assert len(response) > 0


def test_build_ooc_response_fast_forward_returns_string():
    response = build_ooc_response(SafetyCommand.FAST_FORWARD)
    assert isinstance(response, str)
    assert len(response) > 0


def test_build_ooc_response_pause_returns_string():
    response = build_ooc_response(SafetyCommand.PAUSE)
    assert isinstance(response, str)
    assert len(response) > 0


def test_build_ooc_response_hard_stop_returns_string():
    response = build_ooc_response(SafetyCommand.HARD_STOP)
    assert isinstance(response, str)
    assert len(response) > 0


def test_build_ooc_response_x_card_mentions_content_removed():
    """X_CARD response should confirm content removed."""
    response = build_ooc_response(SafetyCommand.X_CARD)
    lower = response.lower()
    assert any(phrase in lower for phrase in ("removed", "skipped", "cut", "cleared", "aside"))


def test_build_ooc_response_rewind_asks_how_far():
    """REWIND response should ask how far back to rewind."""
    response = build_ooc_response(SafetyCommand.REWIND)
    lower = response.lower()
    assert any(phrase in lower for phrase in ("how far", "where", "back to", "point", "moment"))


def test_build_ooc_response_fast_forward_asks_where():
    """FAST_FORWARD response should ask where to skip to."""
    response = build_ooc_response(SafetyCommand.FAST_FORWARD)
    lower = response.lower()
    assert any(phrase in lower for phrase in ("where", "skip", "ahead", "forward", "scene"))


def test_build_ooc_response_pause_confirms_ready_to_resume():
    """PAUSE response should mention resuming when ready."""
    response = build_ooc_response(SafetyCommand.PAUSE)
    lower = response.lower()
    assert any(phrase in lower for phrase in ("ready", "resume", "whenever", "take", "space"))


def test_build_ooc_response_hard_stop_offers_aftercare():
    """HARD_STOP response should offer aftercare / full exit from fiction."""
    response = build_ooc_response(SafetyCommand.HARD_STOP)
    lower = response.lower()
    assert any(phrase in lower for phrase in ("aftercare", "care", "support", "check in", "okay", "alright"))


def test_build_ooc_response_includes_player_note_when_provided():
    """When player_note is given it should appear or be acknowledged in the response."""
    note = "the violence was too graphic"
    response = build_ooc_response(SafetyCommand.X_CARD, player_note=note)
    # The note itself or a reference to it should appear somewhere in the response
    assert note in response or "noted" in response.lower() or "heard" in response.lower()


def test_build_ooc_response_player_note_default_empty():
    """Calling with no player_note should not raise and still return a response."""
    response = build_ooc_response(SafetyCommand.PAUSE, player_note="")
    assert isinstance(response, str)
    assert len(response) > 0


# ---------------------------------------------------------------------------
# apply_safety_command — correct fields and no mutation
# ---------------------------------------------------------------------------


def _base_safety_state() -> dict:
    return {"hard_stop": False, "pause": False, "intensity_check": "none"}


def test_apply_x_card_sets_hard_stop_and_pause():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.X_CARD, state)
    assert result["hard_stop"] is True
    assert result["pause"] is True


def test_apply_x_card_sets_intensity_check_pending():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.X_CARD, state)
    assert result["intensity_check"] == "pending"


def test_apply_hard_stop_sets_hard_stop_and_pause():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.HARD_STOP, state)
    assert result["hard_stop"] is True
    assert result["pause"] is True


def test_apply_hard_stop_sets_intensity_check_pending():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.HARD_STOP, state)
    assert result["intensity_check"] == "pending"


def test_apply_pause_sets_pause():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.PAUSE, state)
    assert result["pause"] is True


def test_apply_pause_sets_intensity_check_pending():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.PAUSE, state)
    assert result["intensity_check"] == "pending"


def test_apply_pause_does_not_set_hard_stop():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.PAUSE, state)
    assert result["hard_stop"] is False


def test_apply_rewind_sets_intensity_check_pending():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.REWIND, state)
    assert result["intensity_check"] == "pending"


def test_apply_rewind_leaves_hard_stop_unchanged():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.REWIND, state)
    assert result["hard_stop"] is False


def test_apply_rewind_leaves_pause_unchanged():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.REWIND, state)
    assert result["pause"] is False


def test_apply_fast_forward_sets_intensity_check_pending():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.FAST_FORWARD, state)
    assert result["intensity_check"] == "pending"


def test_apply_fast_forward_leaves_hard_stop_unchanged():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.FAST_FORWARD, state)
    assert result["hard_stop"] is False


def test_apply_fast_forward_leaves_pause_unchanged():
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.FAST_FORWARD, state)
    assert result["pause"] is False


def test_apply_does_not_mutate_input_x_card():
    state = _base_safety_state()
    original_hard_stop = state["hard_stop"]
    apply_safety_command(SafetyCommand.X_CARD, state)
    assert state["hard_stop"] == original_hard_stop  # original unchanged


def test_apply_does_not_mutate_input_pause():
    state = _base_safety_state()
    original_pause = state["pause"]
    apply_safety_command(SafetyCommand.PAUSE, state)
    assert state["pause"] == original_pause  # original unchanged


def test_apply_does_not_mutate_input_rewind():
    state = _base_safety_state()
    original_check = state["intensity_check"]
    apply_safety_command(SafetyCommand.REWIND, state)
    assert state["intensity_check"] == original_check  # original unchanged


def test_apply_returns_new_dict_not_same_object():
    """apply_safety_command must return a new dict, not the same reference."""
    state = _base_safety_state()
    result = apply_safety_command(SafetyCommand.X_CARD, state)
    assert result is not state


def test_apply_preserves_extra_keys_in_state():
    """Unknown keys in safety_state must pass through untouched."""
    state = {**_base_safety_state(), "custom_flag": "important_value"}
    result = apply_safety_command(SafetyCommand.PAUSE, state)
    assert result["custom_flag"] == "important_value"
