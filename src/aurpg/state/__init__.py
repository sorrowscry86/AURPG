"""Canonical Python dataclass model for AURPG session state.

These types mirror the XML schema defined in aurpg_system_prompt_prototype.xml
and serve as the reference for any future parser or runtime struct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PlayMode(str, Enum):
    SOLO = "solo"
    SQUAD = "squad"


class OrchestrationMode(str, Enum):
    STRICT_MANUAL = "strict_manual"
    COLLABORATIVE_CONSULT = "collaborative_consult"
    GENERATIVE_SYNTHESIS = "generative_synthesis"


class Position(str, Enum):
    CONTROLLED = "controlled"
    RISKY = "risky"
    DESPERATE = "desperate"


class Effect(str, Enum):
    LIMITED = "limited"
    STANDARD = "standard"
    GREAT = "great"


class ClockType(str, Enum):
    STANDARD = "standard"
    DANGER = "danger"
    RACING = "racing"
    LINKED = "linked"
    MISSION = "mission"


class TrackRank(str, Enum):
    TROUBLESOME = "troublesome"
    DANGEROUS = "dangerous"
    FORMIDABLE = "formidable"
    EXTREME = "extreme"
    EPIC = "epic"


class ContentStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class HarmLevel(str, Enum):
    NONE = "none"
    BRUISED = "bruised"          # -1 to relevant rolls when fiction applies
    WOUNDED = "wounded"          # -2; requires care or a specific recovery move
    INCAPACITATED = "incapacitated"  # unable to act without help; mission-critical impact


class LoadState(str, Enum):
    LIGHT = "light"    # 0-3 items carried
    NORMAL = "normal"  # 4-5 items
    HEAVY = "heavy"    # 6+ items or bulk gear; some moves penalised


# ---------------------------------------------------------------------------
# Session state containers
# ---------------------------------------------------------------------------


@dataclass
class CampaignMeta:
    id: str
    title: str
    genre: str
    tone: str
    canon_mode: str
    orchestration_mode: OrchestrationMode


@dataclass
class PlayState:
    mode: PlayMode
    scene_id: str
    location: str
    objective: str
    time_marker: str


@dataclass
class PlayerState:
    character_name: str
    deep_pov: bool
    stress: int        # 0-10; at 10 the character breaks (trauma/consequence)
    momentum: int      # -6 to +10; positive can cancel challenge dice
    harm: HarmLevel
    load: LoadState


@dataclass
class ResolutionState:
    position: Position
    effect: Effect
    move_trigger: str  # active move name or "none"
    stakes: str


@dataclass
class SafetyState:
    hard_stop: bool
    pause: bool
    intensity_check: str  # "none" or a pending description


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

# Canonical attributes and their narrative domain:
#   edge   — speed, precision, quick thinking, perception under pressure
#   heart  — will, empathy, resolve, connection, morale in the face of loss
#   iron   — strength, endurance, direct confrontation, physical tenacity
#   shadow — stealth, deception, manipulation, covert action, reading people
#   wits   — knowledge, planning, preparation, technical skill, adaptation
CANONICAL_ATTRIBUTES = ("edge", "heart", "iron", "shadow", "wits")


@dataclass
class Attribute:
    name: str   # one of CANONICAL_ATTRIBUTES
    value: int  # 1-4 (starting range); 0 is not playable without fiction justification


@dataclass
class Bonus:
    source: str
    value: int


@dataclass
class Relationship:
    npc: str
    status: str
    clock_ref: str = ""


@dataclass
class InventoryItem:
    name: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Resources:
    attributes: list[Attribute] = field(default_factory=list)
    bonuses: list[Bonus] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    inventory: list[InventoryItem] = field(default_factory=list)

    def attribute(self, name: str) -> int:
        for a in self.attributes:
            if a.name == name:
                return a.value
        return 0

    def total_bonus(self) -> int:
        return sum(b.value for b in self.bonuses)


# ---------------------------------------------------------------------------
# State machines
# ---------------------------------------------------------------------------


@dataclass
class Clock:
    id: str
    name: str
    type: ClockType
    segments: int   # must be 4, 6, or 8
    filled: int
    linked_to: str = ""

    @property
    def is_complete(self) -> bool:
        return self.filled >= self.segments

    @property
    def remaining(self) -> int:
        return max(0, self.segments - self.filled)

    def tick(self, n: int = 1) -> None:
        self.filled = max(0, min(self.segments, self.filled + n))


# Boxes per success by rank
_BOXES_PER_SUCCESS: dict[TrackRank, int] = {
    TrackRank.TROUBLESOME: 3,
    TrackRank.DANGEROUS: 2,
    TrackRank.FORMIDABLE: 1,
}
# Extra ticks per success (for extreme/epic ranks)
_TICKS_PER_SUCCESS: dict[TrackRank, int] = {
    TrackRank.EXTREME: 2,
    TrackRank.EPIC: 1,
}

TRACK_BOXES = 10
TICKS_PER_BOX = 4


@dataclass
class ProgressTrack:
    id: str
    name: str
    rank: TrackRank
    boxes_filled: int          # 0-10
    ticks_in_current_box: int  # 0-3

    @property
    def total_ticks(self) -> int:
        return self.boxes_filled * TICKS_PER_BOX + self.ticks_in_current_box

    @property
    def progress_score(self) -> int:
        """Score used when rolling a progress move (number of completed boxes)."""
        return self.boxes_filled

    def advance_success(self) -> None:
        """Mark progress for one success, scaled to rank."""
        ticks_to_add = 0
        if self.rank in _BOXES_PER_SUCCESS:
            ticks_to_add = _BOXES_PER_SUCCESS[self.rank] * TICKS_PER_BOX
        elif self.rank in _TICKS_PER_SUCCESS:
            ticks_to_add = _TICKS_PER_SUCCESS[self.rank]

        total = min(TRACK_BOXES * TICKS_PER_BOX, self.total_ticks + ticks_to_add)
        self.boxes_filled = total // TICKS_PER_BOX
        self.ticks_in_current_box = total % TICKS_PER_BOX


@dataclass
class StateMachines:
    clocks: list[Clock] = field(default_factory=list)
    progress_tracks: list[ProgressTrack] = field(default_factory=list)

    def clock(self, clock_id: str) -> Clock | None:
        return next((c for c in self.clocks if c.id == clock_id), None)

    def track(self, track_id: str) -> ProgressTrack | None:
        return next((t for t in self.progress_tracks if t.id == track_id), None)


# ---------------------------------------------------------------------------
# Safety profile
# ---------------------------------------------------------------------------


@dataclass
class ContentCategory:
    name: str
    status: ContentStatus
    guidance: str


@dataclass
class SafetyProfile:
    categories: list[ContentCategory] = field(default_factory=list)

    def status(self, category: str) -> ContentStatus | None:
        for c in self.categories:
            if c.name == category:
                return c.status
        return None


# ---------------------------------------------------------------------------
# Top-level session
# ---------------------------------------------------------------------------


@dataclass
class SessionState:
    """Complete runtime state for one AURPG session."""

    campaign: CampaignMeta
    play_state: PlayState
    player_state: PlayerState
    resolution_state: ResolutionState
    safety_state: SafetyState
    resources: Resources = field(default_factory=Resources)
    state_machines: StateMachines = field(default_factory=StateMachines)
    safety_profile: SafetyProfile = field(default_factory=SafetyProfile)
