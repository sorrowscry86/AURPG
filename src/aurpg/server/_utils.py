"""Shared helpers for route handlers."""

from __future__ import annotations

from aurpg.session import Session
from aurpg.server.schemas import ClockSnapshot, StateSnapshot


def state_snapshot(session: Session) -> StateSnapshot:
    """Extract a :class:`StateSnapshot` from a live session."""
    ps = session.state.session_state.get("player_state", {})
    return StateSnapshot(
        stress=int(ps.get("stress", 0)),
        momentum=int(ps.get("momentum", 2)),
        harm=ps.get("harm", "none"),
        clocks=[
            ClockSnapshot(
                id=c.get("id", ""),
                label=c.get("label", ""),
                clock_type=c.get("clock_type", "standard"),
                segments=int(c.get("segments", 4)),
                filled=int(c.get("filled", 0)),
            )
            for c in session.state.clocks
        ],
    )
