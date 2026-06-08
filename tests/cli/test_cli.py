"""Tests for aurpg.cli.main — offline, no LLM calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. build_parser subcommands exist
# ---------------------------------------------------------------------------

def test_build_parser_subcommands():
    from aurpg.cli.main import build_parser

    parser = build_parser()
    # Each valid subcommand should parse without error
    for subcmd in ("new", "list"):
        args = parser.parse_args([subcmd])
        assert args.command == subcmd

    for subcmd in ("play", "resume"):
        args = parser.parse_args([subcmd, "some-uuid"])
        assert args.command == subcmd
        assert args.session_id == "some-uuid"


# ---------------------------------------------------------------------------
# 2. Default values
# ---------------------------------------------------------------------------

def test_build_parser_defaults():
    from aurpg.cli.main import build_parser

    args = build_parser().parse_args(["list"])
    assert args.model == "claude-haiku-4-5-20251001"
    assert args.saves_dir is None
    assert args.prompt is None


# ---------------------------------------------------------------------------
# 3. Global flags forwarded to subcommand
# ---------------------------------------------------------------------------

def test_build_parser_global_flags():
    from aurpg.cli.main import build_parser

    args = build_parser().parse_args(
        ["--saves-dir", "/tmp/saves", "--model", "claude-opus-4-8", "list"]
    )
    assert args.model == "claude-opus-4-8"
    assert args.saves_dir == "/tmp/saves"


# ---------------------------------------------------------------------------
# 4. _resolve_saves_dir — default
# ---------------------------------------------------------------------------

def test_resolve_saves_dir_default():
    from aurpg.cli.main import _resolve_saves_dir

    args = SimpleNamespace(saves_dir=None)
    result = _resolve_saves_dir(args)
    assert isinstance(result, Path)
    assert str(result).endswith(str(Path(".aurpg") / "saves"))


# ---------------------------------------------------------------------------
# 5. _resolve_saves_dir — explicit
# ---------------------------------------------------------------------------

def test_resolve_saves_dir_explicit():
    from aurpg.cli.main import _resolve_saves_dir

    args = SimpleNamespace(saves_dir="/tmp/test")
    result = _resolve_saves_dir(args)
    assert result == Path("/tmp/test")


# ---------------------------------------------------------------------------
# 6. _resolve_prompt_path — default points to bundled XML
# ---------------------------------------------------------------------------

def test_resolve_prompt_path_default():
    from aurpg.cli.main import _resolve_prompt_path

    args = SimpleNamespace(prompt=None)
    result = _resolve_prompt_path(args)
    assert isinstance(result, Path)
    assert result.name == "aurpg_system_prompt_prototype.xml"


# ---------------------------------------------------------------------------
# 7. _resolve_prompt_path — explicit
# ---------------------------------------------------------------------------

def test_resolve_prompt_path_explicit():
    from aurpg.cli.main import _resolve_prompt_path

    args = SimpleNamespace(prompt="/tmp/my.xml")
    result = _resolve_prompt_path(args)
    assert result == Path("/tmp/my.xml")


# ---------------------------------------------------------------------------
# 8. cmd_list — saves_dir doesn't exist
# ---------------------------------------------------------------------------

def test_cmd_list_empty_dir(tmp_path, capsys):
    from aurpg.cli.main import cmd_list

    non_existent = tmp_path / "no_saves_here"
    args = SimpleNamespace(saves_dir=str(non_existent))
    cmd_list(args)

    captured = capsys.readouterr()
    assert "No saved sessions found." in captured.out


# ---------------------------------------------------------------------------
# 9. cmd_list — sessions with meta.json
# ---------------------------------------------------------------------------

def test_cmd_list_sessions(tmp_path, capsys):
    from aurpg.cli.main import cmd_list

    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()

    # Create two session dirs with meta.json
    for i, session_id in enumerate(["aaa-111", "bbb-222"]):
        session_dir = saves_dir / session_id
        session_dir.mkdir()
        meta = {"model": f"claude-test-{i}", "session_id": session_id}
        (session_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    args = SimpleNamespace(saves_dir=str(saves_dir))
    cmd_list(args)

    captured = capsys.readouterr()
    assert "aaa-111" in captured.out
    assert "bbb-222" in captured.out
    assert "claude-test-0" in captured.out
    assert "claude-test-1" in captured.out


# ---------------------------------------------------------------------------
# 10. cmd_list — subdir has no meta.json (bare name printed, no crash)
# ---------------------------------------------------------------------------

def test_cmd_list_no_meta(tmp_path, capsys):
    from aurpg.cli.main import cmd_list

    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    session_dir = saves_dir / "bare-session-id"
    session_dir.mkdir()
    # No meta.json

    args = SimpleNamespace(saves_dir=str(saves_dir))
    cmd_list(args)  # must not raise

    captured = capsys.readouterr()
    assert "bare-session-id" in captured.out


# ---------------------------------------------------------------------------
# 11. main() with no subcommand prints help
# ---------------------------------------------------------------------------

def test_main_no_subcommand_prints_help():
    from aurpg.cli import main as main_module

    with patch.object(sys, "argv", ["aurpg"]):
        with patch.object(main_module, "build_parser") as mock_build:
            mock_parser = MagicMock()
            mock_build.return_value = mock_parser
            # parse_args returns a namespace with no 'command' attribute
            mock_parser.parse_args.return_value = SimpleNamespace()
            main_module.main()
            mock_parser.print_help.assert_called_once()


# ---------------------------------------------------------------------------
# 12. main() with "list" dispatches cmd_list
# ---------------------------------------------------------------------------

def test_main_dispatches_list(tmp_path):
    from aurpg.cli import main as main_module

    non_existent = tmp_path / "no_sessions"
    with patch.object(sys, "argv", ["aurpg", "--saves-dir", str(non_existent), "list"]):
        with patch.object(main_module, "cmd_list") as mock_cmd_list:
            main_module.main()
            mock_cmd_list.assert_called_once()
