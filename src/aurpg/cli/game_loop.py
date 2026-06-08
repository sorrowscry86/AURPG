"""AURPG CLI interactive game loop."""
from __future__ import annotations

from pathlib import Path

from aurpg.cli.renderer import (
    render_character_sheet,
    render_ledger,
    render_options,
    render_safety_banner,
)
from aurpg.session import (
    Session,
    build_recap_context,
    needs_recap,
    run_turn,
    save_session,
)

__all__ = ["play_session"]

_HELP_TEXT = """
AURPG Commands
  /sheet    — show character sheet
  /recap    — show recent session summary
  /quit     — save and exit
  /help     — show this message

Safety Commands (type during play)
  [X-Card]           — freeze and remove flagged content
  [Rewind]           — go back to an earlier moment
  [Fast-Forward]     — skip ahead past difficult content
  [Pause]            — open out-of-character space
  !enforce_hard_stop — fully exit fiction
"""


def play_session(
    session: Session,
    *,
    save_dir: Path,
    client,
) -> None:
    """Run the interactive AURPG turn loop until the player quits or hard-stops.

    Each iteration:
    1. Show the state ledger.
    2. Show any active safety banner.
    3. Read player input.
    4. Handle meta-commands (/quit, /sheet, /help, /recap).
    5. Skip empty input.
    6. Prepend recap context when the session threshold is reached.
    7. Run the turn and display the response.
    8. Auto-save after every completed turn.

    Args:
        session:  The current Session (reassigned after each turn).
        save_dir: Root directory for saves.
        client:   An anthropic.Anthropic instance.
    """
    print("\nWelcome to AURPG. Type /help for commands.\n")

    while True:
        ss = session.state.session_state.get("safety_state", {})
        if ss.get("hard_stop", "false") == "true":
            print(render_safety_banner(session.state))
            print("\n[Session ended due to hard stop. Your progress is saved.]\n")
            save_session(session, save_dir)
            break

        print(render_ledger(session.state))

        banner = render_safety_banner(session.state)
        if banner:
            print(banner)

        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Interrupted — saving...]\n")
            save_session(session, save_dir)
            break

        if raw == "/quit":
            save_session(session, save_dir)
            print("[Session saved. Goodbye!]")
            break

        if raw == "/sheet":
            print(render_character_sheet(session.state))
            continue

        if raw == "/help":
            print(_HELP_TEXT)
            continue

        if raw == "/recap":
            ctx = build_recap_context(session)
            print(f"\n[Recap]\n{ctx}\n" if ctx else "\n[No turns recorded yet.]\n")
            continue

        if not raw:
            continue

        player_input = raw
        if needs_recap(session):
            ctx = build_recap_context(session)
            if ctx:
                player_input = f"[RECAP — recent session]\n{ctx}\n\n{raw}"

        session, response = run_turn(session, player_input, client=client)

        print(f"\n{response.raw_text}\n")
        if response.options:
            print(render_options(response.options))

        save_session(session, save_dir)
