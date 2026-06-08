"""Golden-transcript tests for the AURPG system prompt.

Tests are marked `live` and skip automatically when ANTHROPIC_API_KEY is not
set. Run them explicitly:

    pytest -m live tests/prompts/

Each test:
1. Loads the system prompt + sample campaign state.
2. Sends a canonical player action from a YAML fixture.
3. Asserts expected patterns are present and banned patterns are absent.
"""
from __future__ import annotations

import re
from typing import Any

import pytest

from .conftest import all_fixture_names, load_fixture

MODEL = "claude-haiku-4-5-20251001"  # fast, cheap; swap to sonnet/opus for higher fidelity
MAX_TOKENS = 1024


def _call_engine(
    client: Any,
    system_prompt: str,
    campaign_state: str,
    player_input: str,
) -> str:
    """Send one engine turn and return the assistant response text."""
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
    return response.content[0].text


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

    failures = _check_patterns(response, fixture)

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


def test_system_prompt_xml_is_present(system_prompt: str) -> None:
    assert "<aurpg_system_prompt" in system_prompt
    assert "<hard_rules>" in system_prompt
    assert "<resolution_engine>" in system_prompt
    assert "<safety_and_consent_modules>" in system_prompt


def test_campaign_state_xml_is_present(campaign_state: str) -> None:
    assert "<aurpg_campaign_state" in campaign_state
    assert "<session_state>" in campaign_state
    assert "<state_machines>" in campaign_state
    assert "<safety_profile>" in campaign_state


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
