"""AURPG CLI renderer — pure formatting functions, no side effects."""
from __future__ import annotations

from aurpg.state.manager import CampaignState

__all__ = [
    "render_ledger",
    "render_character_sheet",
    "render_safety_banner",
    "render_options",
]

_SEP = "─" * 60


def render_ledger(state: CampaignState) -> str:
    """Return a formatted state ledger string for display before each turn."""
    ps = state.session_state.get("player_state", {})
    rs = state.session_state.get("resolution_state", {})

    stress = ps.get("stress", "?")
    momentum = ps.get("momentum", "?")
    harm = ps.get("harm", "none")
    position = rs.get("position", "?")
    effect = rs.get("effect", "?")

    lines: list[str] = [
        _SEP,
        f"  STRESS {stress}/10  |  MOMENTUM {momentum:>3}  |  HARM: {harm}",
        f"  Position: {position}  |  Effect: {effect}",
    ]

    if state.clocks:
        lines.append("  Clocks:")
        for c in state.clocks:
            filled = int(c.get("filled", 0))
            segments = int(c.get("segments", 4))
            bar = "█" * filled + "░" * (segments - filled)
            lines.append(f"    [{bar}] {c.get('id', '?')} ({filled}/{segments})")

    if state.progress_tracks:
        lines.append("  Tracks:")
        for t in state.progress_tracks:
            ticks = int(t.get("ticks", 0))
            lines.append(f"    {t.get('id', '?')}: {ticks}/40 ticks")

    lines.append(_SEP)
    return "\n".join(lines)


def render_character_sheet(state: CampaignState) -> str:
    """Return a formatted character sheet string."""
    ps = state.session_state.get("player_state", {})
    name = ps.get("character_name", "Unknown")
    load = ps.get("load", "?")
    res = state.resources

    lines: list[str] = [
        _SEP,
        f"  CHARACTER: {name}   Load: {load}",
        "  Attributes:",
    ]
    for a in res.get("attributes", []):
        lines.append(f"    {a.get('name', '?')}: {a.get('value', '?')}")

    bonuses = res.get("bonuses", [])
    if bonuses:
        lines.append("  Bonuses:")
        for b in bonuses:
            lines.append(f"    +{b.get('value', '?')} from {b.get('source', '?')}")

    rels = res.get("relationships", [])
    if rels:
        lines.append("  Relationships:")
        for r in rels:
            lines.append(f"    {r.get('npc', '?')}: {r.get('status', '?')}")

    inv = res.get("inventory", [])
    if inv:
        lines.append("  Inventory:")
        for i in inv:
            lines.append(f"    {i.get('name', '?')}  [{i.get('tags', '')}]")

    lines.append(_SEP)
    return "\n".join(lines)


def render_safety_banner(state: CampaignState) -> str:
    """Return an OOC safety banner, or empty string when no safety is active."""
    ss = state.session_state.get("safety_state", {})
    hard_stop = ss.get("hard_stop", "false") == "true"
    paused = ss.get("pause", "false") == "true"

    if hard_stop:
        return "\n".join([
            "╔" + "═" * 58 + "╗",
            "║  ⚠  HARD STOP — FULLY OUT OF FICTION                    ║",
            "║  Your wellbeing comes first. Take all the time you need. ║",
            "╚" + "═" * 58 + "╝",
        ])
    if paused:
        return "\n".join([
            "┌" + "─" * 58 + "┐",
            "│  [OOC] SESSION PAUSED — out-of-character space active    │",
            "│  Type anything to resume, or !enforce_hard_stop to stop. │",
            "└" + "─" * 58 + "┘",
        ])
    return ""


def render_options(options: list[str]) -> str:
    """Return a formatted numbered options string."""
    if not options:
        return "  (no options — type your action freely)"
    lines = ["  What do you do?"]
    for i, opt in enumerate(options, 1):
        lines.append(f"  {i}) {opt}")
    lines.append("  (or type freely)")
    return "\n".join(lines)
