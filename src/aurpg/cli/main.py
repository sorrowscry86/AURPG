"""AURPG command-line interface."""
from __future__ import annotations

import argparse
import importlib.resources
import json
import os
import tempfile
from pathlib import Path

from aurpg.cli.game_loop import play_session
from aurpg.llm import make_client
from aurpg.session import load_session, new_session
from aurpg.wizard import config_to_state_xml, run_wizard

__all__ = ["build_parser", "main"]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _default_saves_dir() -> Path:
    return Path.home() / ".aurpg" / "saves"


def _default_prompt_path() -> Path:
    return Path(
        str(
            importlib.resources.files("aurpg")
            .joinpath("prompts")
            .joinpath("aurpg_system_prompt_prototype.xml")
        )
    )


def _resolve_saves_dir(args) -> Path:
    if args.saves_dir is not None:
        return Path(args.saves_dir)
    return _default_saves_dir()


def _resolve_prompt_path(args) -> Path:
    if args.prompt is not None:
        return Path(args.prompt)
    return _default_prompt_path()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aurpg",
        description="Amalgamated Ultimate RPG System — text RPG powered by Claude.",
    )

    # Global optional arguments
    parser.add_argument(
        "--saves-dir",
        default=None,
        help="Root directory for saves (default: ~/.aurpg/saves)",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Path to system prompt XML (default: bundled aurpg_system_prompt_prototype.xml)",
    )
    _default_model = (
        "openrouter/auto" if os.environ.get("OPENROUTER_API_KEY") else "claude-haiku-4-5-20251001"
    )
    parser.add_argument(
        "--model",
        default=_default_model,
        help="Model ID (default: openrouter/auto when OPENROUTER_API_KEY is set, else claude-haiku-4-5-20251001)",
    )

    subparsers = parser.add_subparsers(dest="command")

    # new
    subparsers.add_parser("new", help="Start a new campaign (runs wizard, then game loop)")

    # play
    play_parser = subparsers.add_parser("play", help="Play an existing saved session")
    play_parser.add_argument("session_id", help="The session UUID to load")

    # resume (alias for play)
    resume_parser = subparsers.add_parser("resume", help="Resume a saved session (alias for play)")
    resume_parser.add_argument("session_id", help="The session UUID to load")

    # list
    subparsers.add_parser("list", help="List all saved sessions")

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_new(args) -> None:
    saves_dir = _resolve_saves_dir(args)
    prompt_path = _resolve_prompt_path(args)

    config = run_wizard()
    xml_str = config_to_state_xml(config)

    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".xml", delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(xml_str)
            tmp_file = Path(tmp.name)

        session = new_session(tmp_file, prompt_path, model=args.model)
        client = make_client()
        play_session(session, save_dir=saves_dir, client=client)
    finally:
        if tmp_file is not None and tmp_file.exists():
            tmp_file.unlink()


def cmd_play(args) -> None:
    saves_dir = _resolve_saves_dir(args)
    prompt_path = _resolve_prompt_path(args)

    session = load_session(
        saves_dir,
        args.session_id,
        system_prompt_path=prompt_path if args.prompt else None,
    )
    client = make_client()
    play_session(session, save_dir=saves_dir, client=client)


def cmd_list(args) -> None:
    saves_dir = _resolve_saves_dir(args)

    if not saves_dir.exists():
        print("No saved sessions found.")
        return

    subdirs = sorted(p for p in saves_dir.iterdir() if p.is_dir())
    if not subdirs:
        print("No saved sessions found.")
        return

    for session_dir in subdirs:
        session_id = session_dir.name
        meta_path = session_dir / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                saved = meta.get("last_saved", "")
                # Trim to date+time without microseconds or timezone suffix
                saved_display = saved[:16].replace("T", " ") if saved else "unknown"
                print(f"{session_id}  saved: {saved_display}  model: {meta['model']}")
            except Exception:
                print(session_id)
        else:
            print(session_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _get_handler(command: str):
    """Return the handler function for *command*, looked up at call-time so
    that monkeypatching the module-level names works in tests."""
    import aurpg.cli.main as _self  # noqa: PLC0415

    return {
        "new": _self.cmd_new,
        "play": _self.cmd_play,
        "resume": _self.cmd_play,
        "list": _self.cmd_list,
    }.get(command)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        command = args.command
    except AttributeError:
        parser.print_help()
        return

    if command is None:
        parser.print_help()
        return

    handler = _get_handler(command)
    if handler is None:
        parser.print_help()
    else:
        handler(args)


if __name__ == "__main__":
    main()
