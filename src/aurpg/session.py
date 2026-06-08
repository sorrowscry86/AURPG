"""AURPG session manager.

Orchestrates the AURPG turn loop by tying together the LLM layer, safety module,
and campaign state.  Sessions are the primary unit of game continuity: they hold
the live campaign state, the loaded system prompt, and per-session configuration.

Typical usage::

    session = new_session(state_path, system_prompt_path, model="claude-sonnet-4-5")
    client  = make_client()

    while True:
        player_input = input("> ")
        session, response = run_turn(session, player_input, client=client)
        print(response.raw_text)
        if needs_recap(session):
            print("[recap context injected on next turn]")

    save_dir = save_session(session, Path("saves"))
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from aurpg.llm import EngineResponse, assemble_prompt, call_engine_with_retry
from aurpg.safety import SafetyCommand, build_ooc_response, detect_safety_command
from aurpg.state.manager import (
    CampaignState,
    StateError,
    append_turn,
    apply_safety,
    load_state,
    save_state,
    state_to_xml,
)

__all__ = [
    "Session",
    "build_recap_context",
    "load_session",
    "needs_recap",
    "new_session",
    "run_turn",
    "save_session",
]

# Maximum number of recent turns included in a recap context block.
_RECAP_WINDOW: int = 5


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    """Live game session pairing a campaign state with LLM configuration.

    Attributes:
        id:               UUID string identifying this session.
        state:            The live campaign state (immutable-update style).
        system_prompt:    Full text of the XML system prompt loaded at session start.
        model:            Anthropic model ID (e.g. ``"claude-sonnet-4-5"``).
        max_tokens:       Maximum tokens to request per LLM turn (default 1024).
        recap_threshold:  Number of turns in history that triggers recap injection
                          (default 20).
    """

    id: str
    state: CampaignState
    system_prompt: str
    model: str
    max_tokens: int = 1024
    recap_threshold: int = 20
    system_prompt_path: str | None = None   # persisted in meta.json for CLI resume


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------


def new_session(
    state_path: Path,
    system_prompt_path: Path,
    *,
    model: str,
    session_id: str | None = None,
) -> Session:
    """Create a new :class:`Session` from files on disk.

    Args:
        state_path:         Path to a campaign state XML file (validated on load).
        system_prompt_path: Path to the system prompt XML file (read as plain text).
        model:              Anthropic model identifier string.
        session_id:         Optional UUID string.  A new UUID v4 is generated when
                            ``None`` (the default).

    Returns:
        A fully initialised :class:`Session` with default max_tokens and
        recap_threshold values.

    Raises:
        StateError: If the campaign state file fails validation or cannot be parsed.
        OSError:    If either file cannot be read.
    """
    state = load_state(state_path)
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    sid = session_id if session_id is not None else str(uuid.uuid4())
    return Session(
        id=sid,
        state=state,
        system_prompt=system_prompt,
        model=model,
        system_prompt_path=str(system_prompt_path),
    )


# ---------------------------------------------------------------------------
# Turn execution
# ---------------------------------------------------------------------------


def run_turn(
    session: Session,
    player_input: str,
    *,
    client,
) -> tuple[Session, EngineResponse]:
    """Execute one game turn and return the updated session and engine response.

    Safety commands (``[X-Card]``, ``[Rewind]``, ``[Pause]``, ``[Fast-Forward]``,
    ``!enforce_hard_stop``) are intercepted before reaching the LLM.  When a
    safety command is detected the function returns immediately with an OOC
    acknowledgement and an updated safety state — no LLM call is made.

    For normal turns the assembled prompt is sent to the LLM via
    :func:`~aurpg.llm.call_engine_with_retry`, the response is recorded in the
    session's turn history, and the updated session is returned.

    Note: the input *session* is never mutated; all mutations return new objects.

    Args:
        session:      The current session (immutable source).
        player_input: Raw text from the player for this turn.
        client:       An :class:`anthropic.Anthropic` client instance.

    Returns:
        A ``(new_session, engine_response)`` tuple where *new_session* reflects
        any state changes from this turn.

    Raises:
        anthropic.APIStatusError: Re-raised after all retries exhausted.
        Exception: Any other exception from the LLM client propagates immediately.
        The session state is unchanged if an exception is raised.
    """
    # --- Safety gate --------------------------------------------------------
    command: SafetyCommand | None = detect_safety_command(player_input)
    if command is not None:
        ooc_text = build_ooc_response(command, player_note=player_input)
        new_state = apply_safety(session.state, command)
        synthetic_response = EngineResponse(
            raw_text=ooc_text,
            ledger_block=None,
            options=[],
            input_tokens=0,
            output_tokens=0,
        )
        new_session = Session(
            id=session.id,
            state=new_state,
            system_prompt=session.system_prompt,
            model=session.model,
            max_tokens=session.max_tokens,
            recap_threshold=session.recap_threshold,
            system_prompt_path=session.system_prompt_path,
        )
        return new_session, synthetic_response

    # --- Normal LLM turn ----------------------------------------------------
    campaign_state_xml = state_to_xml(session.state)

    messages = assemble_prompt(campaign_state_xml, player_input)
    engine_response = call_engine_with_retry(
        messages,
        session.system_prompt,
        client=client,
        model=session.model,
        max_tokens=session.max_tokens,
    )

    turn_record: dict = {
        "player_input": player_input,
        "raw_response": engine_response.raw_text,
        "options": engine_response.options,
        "ledger_block": engine_response.ledger_block,
        "input_tokens": engine_response.input_tokens,
        "output_tokens": engine_response.output_tokens,
    }
    new_state = append_turn(session.state, turn_record)
    new_session = Session(
        id=session.id,
        state=new_state,
        system_prompt=session.system_prompt,
        model=session.model,
        max_tokens=session.max_tokens,
        recap_threshold=session.recap_threshold,
        system_prompt_path=session.system_prompt_path,
    )
    return new_session, engine_response


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_session(session: Session, save_dir: Path) -> Path:
    """Persist a session to disk.

    Creates ``save_dir / session.id /`` and writes:

    * ``state.xml`` — serialised campaign state via :func:`~aurpg.state.manager.save_state`.
    * ``meta.json`` — session metadata (id, model, max_tokens, recap_threshold).

    Parent directories are created automatically.

    Args:
        session:  Session to persist.
        save_dir: Root directory for saves.

    Returns:
        The session directory path (``save_dir / session.id``).
    """
    session_dir = save_dir / session.id
    session_dir.mkdir(parents=True, exist_ok=True)

    state_path = session_dir / "state.xml"
    save_state(session.state, state_path)

    meta = {
        "id": session.id,
        "model": session.model,
        "max_tokens": session.max_tokens,
        "recap_threshold": session.recap_threshold,
        "system_prompt_path": session.system_prompt_path,
    }
    (session_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    turns_path = session_dir / "turns.jsonl"
    with turns_path.open("w", encoding="utf-8") as f:
        for turn in session.state.turn_history:
            f.write(json.dumps(turn) + "\n")

    return session_dir


def load_session(
    save_dir: Path,
    session_id: str,
    system_prompt_path: Path | None = None,
) -> Session:
    """Reconstruct a :class:`Session` from a previously saved directory.

    Reads ``meta.json`` for configuration, ``state.xml`` for the campaign
    state, and ``turns.jsonl`` (if present) to restore turn history.

    The system prompt path is resolved in priority order:
    1. The explicit *system_prompt_path* argument (if provided).
    2. The ``"system_prompt_path"`` key stored in ``meta.json``.
    3. Raises :exc:`OSError` if neither is available.

    Args:
        save_dir:           Root directory used when saving (same as for :func:`save_session`).
        session_id:         The session UUID used when saving.
        system_prompt_path: Optional override path to the system prompt XML file.

    Returns:
        A reconstructed :class:`Session` with turn history restored.

    Raises:
        OSError:    If the session directory or required files are missing, or if
                    the system prompt path cannot be resolved.
        StateError: If the saved ``state.xml`` fails validation.
        KeyError:   If ``meta.json`` is missing expected fields.
    """
    session_dir = save_dir / session_id

    meta = json.loads((session_dir / "meta.json").read_text(encoding="utf-8"))

    # Resolve system prompt path: explicit arg > meta.json > error
    if system_prompt_path is None:
        stored = meta.get("system_prompt_path")
        if not stored:
            raise OSError(
                f"system_prompt_path not in meta.json for session {session_id!r}; "
                "pass it explicitly"
            )
        system_prompt_path = Path(stored)

    state = load_state(session_dir / "state.xml")

    turns_path = session_dir / "turns.jsonl"
    turn_history: list[dict] = []
    if turns_path.exists():
        for line in turns_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    turn_history.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise StateError(
                        f"Malformed JSON in {turns_path} (line {line[:60]!r}): {exc}"
                    ) from exc
    state.turn_history = turn_history

    return Session(
        id=meta["id"],
        state=state,
        system_prompt=system_prompt_path.read_text(encoding="utf-8"),
        model=meta["model"],
        max_tokens=meta["max_tokens"],
        recap_threshold=meta["recap_threshold"],
        system_prompt_path=str(system_prompt_path),
    )


# ---------------------------------------------------------------------------
# Recap helpers
# ---------------------------------------------------------------------------


def needs_recap(session: Session) -> bool:
    """Return ``True`` if the session's turn history has reached the recap threshold.

    When ``True`` the caller should inject :func:`build_recap_context` output
    into the next LLM turn to help the model maintain narrative continuity over
    long sessions.

    Args:
        session: The current session.

    Returns:
        ``True`` when ``len(session.state.turn_history) >= session.recap_threshold``.

    Note: returns True on every call once the threshold is reached; callers are
    responsible for acting on it.
    """
    return len(session.state.turn_history) >= session.recap_threshold


def build_recap_context(session: Session) -> str:
    """Build a plain-text summary of the last :data:`_RECAP_WINDOW` turns.

    Each turn dict is serialised as a single JSON line.  The result is suitable
    for injecting into an LLM prompt as a lightweight context window.

    Full LLM-based summarisation is deferred to Phase 3+.

    Args:
        session: The current session.

    Returns:
        A newline-joined string of JSON lines (one per recent turn), or an empty
        string if there are no turns in history.
    """
    recent = session.state.turn_history[-_RECAP_WINDOW:]
    if not recent:
        return ""
    return "\n".join(json.dumps(turn) for turn in recent)
