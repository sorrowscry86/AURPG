"""Golden-transcript tests for the AURPG system prompt.

Tests are marked `live` and skip automatically when ANTHROPIC_API_KEY is not
set. Run them explicitly:

    pytest -m live tests/prompts/

Override the model with the AURPG_TEST_MODEL environment variable:

    AURPG_TEST_MODEL=claude-sonnet-4-6 pytest -m live tests/prompts/

Each test:
1. Loads the system prompt + sample campaign state.
2. Sends a canonical player action from a YAML fixture.
3. Asserts expected patterns are present, banned patterns are absent,
   and string-valued state deltas appear in the response.
"""
from __future__ import annotations

import os
import re
import warnings
import xml.etree.ElementTree as ET
from typing import Any

import pytest

from .conftest import all_fixture_names, load_fixture

DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # fast, cheap; override via AURPG_TEST_MODEL
MODEL = os.environ.get("AURPG_TEST_MODEL", DEFAULT_MODEL)
MAX_TOKENS = 1024


def _call_engine(
    client: Any,
    system_prompt: str,
    campaign_state: str,
    player_input: str,
) -> str:
    """Send one engine turn and return concatenated text from all response blocks."""
    messages = [
        {
            "role": "user",
            "content": (
                f"<current_campaign_state>\n{campaign_state}\n</current_campaign_state>\n\n"
                f"{player_input.strip()}"
            ),
        }
    ]
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=messages,
    )
    text_blocks = [block.text for block in response.content if block.type == "text"]
    assert text_blocks, "No text blocks returned in API response"
    return "\n".join(text_blocks)


def _check_patterns(response: str, fixture: dict) -> list[str]:
    """Return a list of failure messages (empty = all pass)."""
    failures: list[str] = []

    for pattern in fixture.get("expected_patterns", []):
        if not re.search(pattern, response, re.MULTILINE):
            failures.append(f"MISSING expected pattern: {pattern!r}")

    for pattern in fixture.get("banned_patterns", []):
        if re.search(pattern, response, re.MULTILINE | re.IGNORECASE):
            failures.append(f"FOUND banned pattern: {pattern!r}")

    return failures


def _check_state_delta(response: str, fixture: dict) -> list[str]:
    """Validate expected_state_delta entries where possible.

    String values are treated as literal substring checks against the response.
    Boolean/complex values require semantic state parsing (planned for Phase 2)
    and emit a UserWarning rather than silently passing.
    """
    failures: list[str] = []
    for key, value in fixture.get("expected_state_delta", {}).items():
        if isinstance(value, str):
            if value not in response:
                failures.append(
                    f"MISSING state delta {key!r}: expected substring {value!r} in response"
                )
        elif isinstance(value, bool | int):
            if not _semantic_state_delta_present(response, key, value):
                failures.append(
                    f"MISSING state delta {key!r}: expected semantic value {value!r}"
                )
        else:
            warnings.warn(
                f"State delta check '{key}={value}' requires semantic parsing "
                f"(Phase 2 — not yet implemented); skipped.",
                UserWarning,
                stacklevel=2,
            )
    return failures


def _semantic_state_delta_present(response: str, key: str, expected: bool | int) -> bool:
    """Return true when response contains structured evidence for a state value."""
    field_name = key.rsplit(".", maxsplit=1)[-1]

    if isinstance(expected, bool):
        expected_text = str(expected).lower()
        return bool(
            re.search(
                rf"\b{re.escape(field_name)}\b\s*[:=]\s*{expected_text}\b",
                response,
                re.IGNORECASE,
            )
        )

    ledger_label_by_field = {
        "stress": "STRESS",
        "momentum": "MOMENTUM",
    }
    ledger_label = ledger_label_by_field.get(field_name, field_name.upper())
    arrow = r"(?:->|â†’)"
    current_value = re.escape(str(expected))
    return bool(
        re.search(
            rf"\[{re.escape(ledger_label)}\]\s*(?:-?\d+\s*{arrow}\s*)?{current_value}\b",
            response,
            re.IGNORECASE,
        )
    )


def test_state_delta_accepts_boolean_ledger_values_without_warning() -> None:
    """Boolean state deltas should be validated instead of skipped."""
    fixture = {"expected_state_delta": {"safety_state.pause": True}}
    response = "[SAFETY] pause=true | hard_stop=false"

    with warnings.catch_warnings(record=True) as caught:
        failures = _check_state_delta(response, fixture)

    assert failures == []
    assert caught == []


def test_state_delta_reports_missing_boolean_value() -> None:
    """A mismatched boolean state delta should produce a failure."""
    fixture = {"expected_state_delta": {"safety_state.pause": True}}
    response = "[SAFETY] pause=false | hard_stop=false"

    failures = _check_state_delta(response, fixture)

    assert failures == [
        "MISSING state delta 'safety_state.pause': expected semantic value True"
    ]


def test_state_delta_accepts_numeric_ledger_updates_without_warning() -> None:
    """Numeric state deltas should match current ledger values after arrows."""
    fixture = {"expected_state_delta": {"player_state.stress": 6}}
    response = "[STRESS] 4->6/10 | [MOMENTUM] 6 | [HARM] none"

    with warnings.catch_warnings(record=True) as caught:
        failures = _check_state_delta(response, fixture)

    assert failures == []
    assert caught == []


def test_state_delta_reports_missing_numeric_value() -> None:
    """Numeric state deltas should fail when the response shows a different value."""
    fixture = {"expected_state_delta": {"player_state.stress": 6}}
    response = "[STRESS] 4->5/10 | [MOMENTUM] 6 | [HARM] none"

    failures = _check_state_delta(response, fixture)

    assert failures == [
        "MISSING state delta 'player_state.stress': expected semantic value 6"
    ]


@pytest.mark.live
@pytest.mark.parametrize("fixture_name", all_fixture_names())
def test_golden_transcript(
    fixture_name: str,
    system_prompt: str,
    campaign_state: str,
    anthropic_client: Any,
) -> None:
    """Run one golden-transcript evaluation against the live LLM."""
    fixture = load_fixture(fixture_name)
    player_input = fixture["player_input"]

    response = _call_engine(
        client=anthropic_client,
        system_prompt=system_prompt,
        campaign_state=campaign_state,
        player_input=player_input,
    )

    failures = _check_patterns(response, fixture) + _check_state_delta(response, fixture)

    assert not failures, (
        f"\nFixture: {fixture_name}\n"
        f"Player input: {player_input.strip()!r}\n\n"
        f"--- Response ---\n{response}\n\n"
        f"--- Failures ---\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Offline structural tests — no API key needed
# ---------------------------------------------------------------------------


def test_fixture_files_are_valid_yaml() -> None:
    """All fixture YAML files must parse without error."""
    for name in all_fixture_names():
        fixture = load_fixture(name)
        assert "player_input" in fixture, f"{name}: missing 'player_input'"
        assert "expected_patterns" in fixture, f"{name}: missing 'expected_patterns'"
        assert isinstance(fixture["expected_patterns"], list)


def test_system_prompt_is_well_formed_xml(system_prompt: str) -> None:
    """System prompt must parse as valid XML and contain key structural sections."""
    try:
        root = ET.fromstring(system_prompt)
    except ET.ParseError as e:
        pytest.fail(f"System prompt is not well-formed XML: {e}")
    assert root.tag == "aurpg_system_prompt", f"Unexpected root tag: {root.tag!r}"
    assert root.find(".//hard_rules") is not None, "Missing <hard_rules> section"
    assert root.find(".//resolution_engine") is not None, "Missing <resolution_engine> section"
    assert root.find("safety_and_consent_modules") is not None, (
        "Missing <safety_and_consent_modules> section"
    )


def test_campaign_state_is_well_formed_xml(campaign_state: str) -> None:
    """Campaign state must parse as valid XML and contain key structural sections."""
    try:
        root = ET.fromstring(campaign_state)
    except ET.ParseError as e:
        pytest.fail(f"Campaign state is not well-formed XML: {e}")
    assert root.tag == "aurpg_campaign_state", f"Unexpected root tag: {root.tag!r}"
    assert root.find("session_state") is not None, "Missing <session_state> section"
    assert root.find("state_machines") is not None, "Missing <state_machines> section"
    assert root.find("safety_profile") is not None, "Missing <safety_profile> section"


def test_expected_patterns_are_valid_regex() -> None:
    """All patterns in fixture files must compile as valid regex."""
    for name in all_fixture_names():
        fixture = load_fixture(name)
        for pattern in fixture.get("expected_patterns", []):
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"{name}: invalid regex in expected_patterns: {pattern!r} — {e}")
        for pattern in fixture.get("banned_patterns", []):
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"{name}: invalid regex in banned_patterns: {pattern!r} — {e}")
