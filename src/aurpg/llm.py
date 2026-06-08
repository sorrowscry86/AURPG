"""Anthropic SDK client layer for AURPG.

Provides prompt assembly, engine invocation, structured output extraction,
retry logic, and a client factory.  The Anthropic API is only called from
:func:`call_engine`; all other functions are pure or delegate to that entry
point.

Typical usage::

    client = make_client()                          # reads ANTHROPIC_API_KEY
    messages = assemble_prompt(system_xml, state_xml, player_input)
    result = call_engine_with_retry(
        messages, system_xml, client=client, model="claude-sonnet-4-5"
    )
    print(result.raw_text)
    print(result.options)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import anthropic

__all__ = [
    "EngineResponse",
    "assemble_prompt",
    "call_engine",
    "call_engine_with_retry",
    "make_client",
]

# ---------------------------------------------------------------------------
# Patterns for response parsing
# ---------------------------------------------------------------------------

# Matches numbered CYOA options like:  "1) Option text"  or  "1)  Padded"
_OPTION_PATTERN: re.Pattern[str] = re.compile(r"^\d+\)\s+(.+)$", re.MULTILINE)

# Matches ledger lines that begin with a [ tag:  "[SCENE] ..."  "[STRESS] +1"
_LEDGER_LINE_PATTERN: re.Pattern[str] = re.compile(r"^\[.+\].*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------


@dataclass
class EngineResponse:
    """Structured result returned by :func:`call_engine` / :func:`call_engine_with_retry`.

    Attributes:
        raw_text:     Full response text from the model (all content blocks joined).
        ledger_block: Newline-joined string of all lines starting with ``[TAG]``
                      (state-update ledger entries), or ``None`` if none were found.
        options:      List of CYOA option strings extracted from numbered lines
                      (``1) …``, ``2) …``, ``3) …``).  May contain fewer or more
                      than three entries if the model output deviates from spec.
        input_tokens: Token count for the prompt, as reported by the API.
        output_tokens: Token count for the completion, as reported by the API.
    """

    raw_text: str
    ledger_block: str | None
    options: list[str]
    input_tokens: int
    output_tokens: int


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def assemble_prompt(
    system_prompt_xml: str,  # noqa: ARG001 — passed separately as API `system`
    campaign_state_xml: str,
    player_input: str,
) -> list[dict]:
    """Build the ``messages`` list for the Anthropic API call.

    The campaign state is wrapped in ``<current_campaign_state>`` tags and
    merged with the player input into a single user message.  The system
    prompt XML is passed as the ``system`` parameter of
    ``client.messages.create`` — it does **not** appear in this list.

    Args:
        system_prompt_xml:  The engine's system prompt (XML).  Not embedded
                            here; provided for signature symmetry only.
        campaign_state_xml: The current serialised campaign state (XML).
        player_input:       The player's action / intent for this turn.

    Returns:
        A one-element list containing a single ``{"role": "user", "content": "..."}``
        dict suitable for passing directly to ``client.messages.create(messages=...)``.
        State and player input are merged into one message to satisfy the
        Anthropic API requirement that consecutive messages must alternate roles.
    """
    content = (
        "<current_campaign_state>\n"
        f"{campaign_state_xml}\n"
        "</current_campaign_state>\n\n"
        f"{player_input.strip()}"
    )
    return [{"role": "user", "content": content}]


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------


def _extract_options(text: str) -> list[str]:
    """Return CYOA option strings from numbered lines (``1) …``)."""
    return [m.group(1).strip() for m in _OPTION_PATTERN.finditer(text)]


def _extract_ledger(text: str) -> str | None:
    """Return a newline-joined block of ``[TAG]`` ledger lines, or ``None``."""
    lines = [m.group(0) for m in _LEDGER_LINE_PATTERN.finditer(text)]
    return "\n".join(lines) if lines else None


# ---------------------------------------------------------------------------
# Engine call
# ---------------------------------------------------------------------------


def call_engine(
    messages: list[dict],
    system: str,
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int = 1024,
) -> EngineResponse:
    """Invoke the Anthropic API once and return a structured :class:`EngineResponse`.

    Args:
        messages:   The messages list from :func:`assemble_prompt`.
        system:     The system prompt string passed as the ``system`` parameter.
        client:     An :class:`anthropic.Anthropic` instance.
        model:      Model identifier string (e.g. ``"claude-sonnet-4-5"``).
        max_tokens: Maximum tokens to generate (default 1024).

    Returns:
        :class:`EngineResponse` with all fields populated.

    Raises:
        anthropic.APIStatusError: On 4xx / 5xx responses (not retried here;
                                  use :func:`call_engine_with_retry` instead).
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    # Join all text content blocks into a single string
    raw_text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )

    return EngineResponse(
        raw_text=raw_text,
        ledger_block=_extract_ledger(raw_text),
        options=_extract_options(raw_text),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------


def call_engine_with_retry(
    messages: list[dict],
    system: str,
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int = 1024,
    max_retries: int = 3,
) -> EngineResponse:
    """Call the engine with exponential-backoff retry on rate-limit errors.

    Retries on :class:`anthropic.APIStatusError` (status 429 / 529) up to
    *max_retries* attempts.  The wait between attempts follows ``2^attempt``
    seconds: 1 s, 2 s, 4 s, …

    Non-:class:`anthropic.APIStatusError` exceptions are re-raised immediately
    without retrying.

    Args:
        messages:    The messages list from :func:`assemble_prompt`.
        system:      The system prompt string.
        client:      An :class:`anthropic.Anthropic` instance.
        model:       Model identifier string.
        max_tokens:  Maximum tokens to generate (default 1024).
        max_retries: Total number of attempts (default 3).  Must be ≥ 1.

    Returns:
        :class:`EngineResponse` from the first successful attempt.

    Raises:
        anthropic.APIStatusError: After all *max_retries* attempts fail.
        Any other exception:      Immediately, without retrying.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    last_error: anthropic.APIStatusError | None = None

    for attempt in range(max_retries):
        try:
            return call_engine(
                messages, system, client=client, model=model, max_tokens=max_tokens
            )
        except anthropic.APIStatusError as exc:
            last_error = exc
            if attempt < max_retries - 1:
                wait_seconds = 2**attempt  # 1, 2, 4, …
                time.sleep(wait_seconds)

    # All attempts exhausted
    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def make_client(api_key: str | None = None) -> anthropic.Anthropic:
    """Create and return an :class:`anthropic.Anthropic` client.

    Args:
        api_key: API key to use.  If ``None``, the SDK reads the
                 ``ANTHROPIC_API_KEY`` environment variable automatically.

    Returns:
        A configured :class:`anthropic.Anthropic` instance.
    """
    if api_key is not None:
        return anthropic.Anthropic(api_key=api_key)
    return anthropic.Anthropic()
