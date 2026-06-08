"""Tests for AURPG LLM integration layer (src/aurpg/llm.py).

All tests are offline — the Anthropic API is never called.  The
``client.messages.create`` method is replaced with a simple mock object so
no network credentials are required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

import anthropic

from aurpg.llm import (
    EngineResponse,
    assemble_prompt,
    call_engine,
    call_engine_with_retry,
    make_client,
)


# ---------------------------------------------------------------------------
# Helpers — build a minimal mock of anthropic.types.Message
# ---------------------------------------------------------------------------


def _make_mock_message(
    text: str,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Return a MagicMock that quacks like anthropic.types.Message."""
    msg = MagicMock()
    # content is a list of content blocks; we only need TextBlock-like objects
    block = MagicMock()
    block.text = text
    msg.content = [block]
    msg.usage = MagicMock()
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


def _make_mock_client(text: str, input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    """Return a MagicMock client whose messages.create() returns a fake message."""
    client = MagicMock()
    client.messages.create.return_value = _make_mock_message(text, input_tokens, output_tokens)
    return client


# ---------------------------------------------------------------------------
# assemble_prompt
# ---------------------------------------------------------------------------


SYSTEM_XML = "<system>rules</system>"
CAMPAIGN_XML = "<state>data</state>"
PLAYER_INPUT = "I draw my sword."


def test_assemble_prompt_returns_list():
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    assert isinstance(result, list)


def test_assemble_prompt_has_one_message():
    """State and player input must be merged into a single user message (API requires alternating roles)."""
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    assert len(result) == 1


def test_assemble_prompt_message_has_role_and_content():
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    msg = result[0]
    assert "role" in msg
    assert "content" in msg


def test_assemble_prompt_message_role_user():
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    assert result[0]["role"] == "user"


def test_assemble_prompt_campaign_state_wrapped_in_tags():
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    # The campaign state XML must appear inside <current_campaign_state> tags somewhere
    full_content = " ".join(str(m["content"]) for m in result)
    assert "<current_campaign_state>" in full_content
    assert "</current_campaign_state>" in full_content
    assert CAMPAIGN_XML in full_content


def test_assemble_prompt_player_input_appears_in_messages():
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    full_content = " ".join(str(m["content"]) for m in result)
    assert PLAYER_INPUT in full_content


def test_assemble_prompt_system_xml_not_in_messages():
    """The system prompt belongs in the 'system' param, not in the messages list."""
    result = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    full_content = " ".join(str(m["content"]) for m in result)
    # System XML should NOT be embedded in the messages list
    assert SYSTEM_XML not in full_content


# ---------------------------------------------------------------------------
# call_engine — basic extraction
# ---------------------------------------------------------------------------


SIMPLE_RESPONSE = "Some narrative text.\n1) Go left\n2) Go right\n3) Stay put"


def test_call_engine_returns_engine_response():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="claude-3-5-haiku-20241022")
    assert isinstance(result, EngineResponse)


def test_call_engine_raw_text_matches_response():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="claude-3-5-haiku-20241022")
    assert result.raw_text == SIMPLE_RESPONSE


def test_call_engine_input_tokens_extracted():
    client = _make_mock_client(SIMPLE_RESPONSE, input_tokens=123)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="claude-3-5-haiku-20241022")
    assert result.input_tokens == 123


def test_call_engine_output_tokens_extracted():
    client = _make_mock_client(SIMPLE_RESPONSE, output_tokens=77)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="claude-3-5-haiku-20241022")
    assert result.output_tokens == 77


def test_call_engine_passes_model_to_create():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    call_engine(messages, SYSTEM_XML, client=client, model="test-model-slug")
    call_kwargs = client.messages.create.call_args[1]
    assert call_kwargs["model"] == "test-model-slug"


def test_call_engine_passes_max_tokens_to_create():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    call_engine(messages, SYSTEM_XML, client=client, model="m", max_tokens=2048)
    call_kwargs = client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 2048


def test_call_engine_default_max_tokens_is_1024():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    call_engine(messages, SYSTEM_XML, client=client, model="m")
    call_kwargs = client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 1024


def test_call_engine_passes_system_to_create():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    call_engine(messages, SYSTEM_XML, client=client, model="m")
    call_kwargs = client.messages.create.call_args[1]
    assert call_kwargs["system"] == SYSTEM_XML


# ---------------------------------------------------------------------------
# EngineResponse.options — CYOA option extraction
# ---------------------------------------------------------------------------


def test_options_three_numbered_lines():
    response_text = "Narrative.\n1) Option A\n2) Option B\n3) Option C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert len(result.options) == 3


def test_options_content_stripped():
    response_text = "Narrative.\n1) Option A\n2) Option B\n3) Option C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert result.options[0] == "Option A"
    assert result.options[1] == "Option B"
    assert result.options[2] == "Option C"


def test_options_no_numbered_lines_returns_empty_list():
    response_text = "Some text without options."
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert result.options == []


def test_options_only_two_numbered_lines():
    """Fewer than 3 options — still extracted; caller handles validation."""
    response_text = "Text.\n1) First\n2) Second"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert len(result.options) == 2
    assert result.options[0] == "First"


def test_options_handles_whitespace_in_numbered_lines():
    response_text = "1)  Spaced option A\n2)  Spaced option B\n3)  Spaced option C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert result.options[0] == "Spaced option A"


def test_options_with_full_response():
    """Options extracted even when mixed into longer narrative output."""
    response_text = (
        "[SCENE] Forest path\n"
        "[STRESS] +1\n"
        "You stand at a crossroads, heart pounding.\n"
        "1) Draw your blade and advance\n"
        "2) Hide behind the oak tree\n"
        "3) Call out to the stranger\n"
        "Or describe your own action."
    )
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert len(result.options) == 3
    assert result.options[0] == "Draw your blade and advance"
    assert result.options[1] == "Hide behind the oak tree"
    assert result.options[2] == "Call out to the stranger"


# ---------------------------------------------------------------------------
# EngineResponse.ledger_block — state-update block extraction
# ---------------------------------------------------------------------------


def test_ledger_block_none_when_no_bracket_lines():
    response_text = "Pure narrative, no ledger entries."
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert result.ledger_block is None


def test_ledger_block_extracted_when_bracket_lines_present():
    response_text = "[SCENE] Dark alley\n[STRESS] +1\nNarrative prose.\n1) Run\n2) Fight\n3) Hide"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert result.ledger_block is not None


def test_ledger_block_contains_scene_line():
    response_text = "[SCENE] Dark alley\n[STRESS] +1\nNarrative.\n1) A\n2) B\n3) C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert "[SCENE] Dark alley" in result.ledger_block


def test_ledger_block_contains_stress_line():
    response_text = "[SCENE] Dark alley\n[STRESS] +1\nNarrative.\n1) A\n2) B\n3) C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert "[STRESS] +1" in result.ledger_block


def test_ledger_block_multiple_tag_types():
    response_text = (
        "[SCENE] Tavern\n"
        "[CLOCKS] mission_clock: 3/8\n"
        "[MOMENTUM] +2\n"
        "[HARM] cut on left arm\n"
        "Prose here.\n"
        "1) A\n2) B\n3) C"
    )
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert "[SCENE]" in result.ledger_block
    assert "[CLOCKS]" in result.ledger_block
    assert "[MOMENTUM]" in result.ledger_block
    assert "[HARM]" in result.ledger_block


def test_ledger_block_excludes_non_bracket_lines():
    """The ledger block should only contain `[TAG]` lines, not prose."""
    response_text = "[SCENE] Rooftop\nThis is prose.\n1) A\n2) B\n3) C"
    client = _make_mock_client(response_text)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    result = call_engine(messages, SYSTEM_XML, client=client, model="m")
    assert "This is prose." not in result.ledger_block


# ---------------------------------------------------------------------------
# call_engine_with_retry — retry behavior
# ---------------------------------------------------------------------------


def _make_429_error() -> anthropic.APIStatusError:
    """Construct a minimal APIStatusError that looks like a 429."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.headers = httpx.Headers({})
    return anthropic.APIStatusError(
        "Rate limit exceeded",
        response=mock_response,
        body={"error": {"type": "rate_limit_error"}},
    )


def test_retry_succeeds_on_first_attempt():
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with patch("time.sleep"):  # no actual sleeping in tests
        result = call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m")
    assert isinstance(result, EngineResponse)
    assert client.messages.create.call_count == 1


def test_retry_retries_on_429_and_eventually_succeeds():
    """Client fails twice with 429, then succeeds on the third call."""
    client = MagicMock()
    error = _make_429_error()
    success = _make_mock_message(SIMPLE_RESPONSE)
    client.messages.create.side_effect = [error, error, success]
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with patch("time.sleep"):
        result = call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m", max_retries=3)
    assert isinstance(result, EngineResponse)
    assert client.messages.create.call_count == 3


def test_retry_raises_after_max_retries_exhausted():
    """After max_retries all fail, the error should propagate."""
    client = MagicMock()
    error = _make_429_error()
    client.messages.create.side_effect = error
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with patch("time.sleep"):
        with pytest.raises(anthropic.APIStatusError):
            call_engine_with_retry(
                messages, SYSTEM_XML, client=client, model="m", max_retries=3
            )
    assert client.messages.create.call_count == 3


def test_retry_uses_exponential_backoff():
    """Verify sleep is called with 2^attempt seconds (1, 2, 4, …)."""
    client = MagicMock()
    error = _make_429_error()
    # Fail twice, succeed on third
    success = _make_mock_message(SIMPLE_RESPONSE)
    client.messages.create.side_effect = [error, error, success]
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    sleep_calls: list[float] = []
    with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
        call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m", max_retries=3)
    # First failure → sleep(1), second failure → sleep(2)
    assert sleep_calls == [1, 2]


def test_retry_non_status_error_not_retried():
    """A non-APIStatusError (e.g., ValueError) must NOT be retried — raise immediately."""
    client = MagicMock()
    client.messages.create.side_effect = ValueError("Unexpected error")
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with patch("time.sleep"):
        with pytest.raises(ValueError):
            call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m", max_retries=3)
    assert client.messages.create.call_count == 1


def test_retry_raises_value_error_when_max_retries_less_than_one():
    """max_retries=0 (or negative) must raise ValueError immediately, before any API call."""
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with pytest.raises(ValueError, match="max_retries must be >= 1"):
        call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m", max_retries=0)
    assert client.messages.create.call_count == 0


def test_retry_raises_value_error_when_max_retries_negative():
    """Negative max_retries must also raise ValueError."""
    client = _make_mock_client(SIMPLE_RESPONSE)
    messages = assemble_prompt(CAMPAIGN_XML, PLAYER_INPUT)
    with pytest.raises(ValueError, match="max_retries must be >= 1"):
        call_engine_with_retry(messages, SYSTEM_XML, client=client, model="m", max_retries=-1)
    assert client.messages.create.call_count == 0


# ---------------------------------------------------------------------------
# make_client
# ---------------------------------------------------------------------------


def test_make_client_returns_anthropic_instance():
    client = make_client(api_key="sk-test-key")
    assert isinstance(client, anthropic.Anthropic)


def test_make_client_uses_provided_api_key():
    client = make_client(api_key="sk-provided-key")
    assert client.api_key == "sk-provided-key"


def test_make_client_uses_env_var_when_no_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    client = make_client()
    assert client.api_key == "sk-from-env"


# ---------------------------------------------------------------------------
# EngineResponse — dataclass field existence
# ---------------------------------------------------------------------------


def test_engine_response_has_raw_text_field():
    er = EngineResponse(
        raw_text="text", ledger_block=None, options=[], input_tokens=0, output_tokens=0
    )
    assert er.raw_text == "text"


def test_engine_response_has_ledger_block_field():
    er = EngineResponse(
        raw_text="text", ledger_block="[SCENE] A", options=[], input_tokens=0, output_tokens=0
    )
    assert er.ledger_block == "[SCENE] A"


def test_engine_response_has_options_field():
    er = EngineResponse(
        raw_text="text", ledger_block=None, options=["a", "b", "c"], input_tokens=0, output_tokens=0
    )
    assert er.options == ["a", "b", "c"]


def test_engine_response_has_input_tokens_field():
    er = EngineResponse(
        raw_text="t", ledger_block=None, options=[], input_tokens=42, output_tokens=0
    )
    assert er.input_tokens == 42


def test_engine_response_has_output_tokens_field():
    er = EngineResponse(
        raw_text="t", ledger_block=None, options=[], input_tokens=0, output_tokens=99
    )
    assert er.output_tokens == 99
