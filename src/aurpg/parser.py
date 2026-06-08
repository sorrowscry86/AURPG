"""Parse AURPG campaign-state XML into SessionState dataclasses and back.

Round-trip guarantee: ``dump_state(parse_state(xml)) == parse_state(dump_state(parse_state(xml)))``
All validation is delegated to ``aurpg.validator``; the parser trusts well-formed, valid input.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from aurpg.state import (
    CANONICAL_ATTRIBUTES,
    Attribute,
    Bonus,
    CampaignMeta,
    Clock,
    ClockType,
    ContentCategory,
    ContentStatus,
    Effect,
    HarmLevel,
    InventoryItem,
    LoadState,
    OrchestrationMode,
    PlayMode,
    PlayState,
    PlayerState,
    Position,
    ProgressTrack,
    Relationship,
    ResolutionState,
    Resources,
    SafetyProfile,
    SafetyState,
    SessionState,
    StateMachines,
    TrackRank,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_state(path: Path) -> SessionState:
    """Load and parse a campaign-state XML file."""
    tree = ET.parse(path)
    return _parse_root(tree.getroot())


def parse_state(xml_string: str) -> SessionState:
    """Parse a campaign-state XML string."""
    root = ET.fromstring(xml_string)
    return _parse_root(root)


def dump_state(state: SessionState, *, version: str = "0.2-prototype") -> str:
    """Serialise a SessionState back to a campaign-state XML string."""
    root = ET.Element("aurpg_campaign_state", version=version)

    # session_state
    ss = ET.SubElement(root, "session_state")
    ET.SubElement(ss, "campaign",
                  id=state.campaign.id,
                  title=state.campaign.title,
                  genre=state.campaign.genre,
                  tone=state.campaign.tone,
                  canon_mode=state.campaign.canon_mode,
                  orchestration_mode=state.campaign.orchestration_mode.value)
    ET.SubElement(ss, "play_state",
                  mode=state.play_state.mode.value,
                  scene_id=state.play_state.scene_id,
                  location=state.play_state.location,
                  objective=state.play_state.objective,
                  time_marker=state.play_state.time_marker)
    ET.SubElement(ss, "player_state",
                  character_name=state.player_state.character_name,
                  deep_pov=str(state.player_state.deep_pov).lower(),
                  stress=str(state.player_state.stress),
                  momentum=str(state.player_state.momentum),
                  harm=state.player_state.harm.value,
                  load=state.player_state.load.value)
    ET.SubElement(ss, "resolution_state",
                  position=state.resolution_state.position.value,
                  effect=state.resolution_state.effect.value,
                  move_trigger=state.resolution_state.move_trigger,
                  stakes=state.resolution_state.stakes)
    ET.SubElement(ss, "safety_state",
                  hard_stop=str(state.safety_state.hard_stop).lower(),
                  pause=str(state.safety_state.pause).lower(),
                  intensity_check=state.safety_state.intensity_check)

    # resources
    res = ET.SubElement(root, "resources")
    attrs_elem = ET.SubElement(res, "attributes")
    for a in state.resources.attributes:
        ET.SubElement(attrs_elem, "attribute", name=a.name, value=str(a.value))
    bonuses_elem = ET.SubElement(res, "bonuses")
    for b in state.resources.bonuses:
        ET.SubElement(bonuses_elem, "bonus", source=b.source, value=str(b.value))
    rels_elem = ET.SubElement(res, "relationships")
    for r in state.resources.relationships:
        ET.SubElement(rels_elem, "relationship", npc=r.npc, status=r.status,
                      clock_ref=r.clock_ref)
    inv_elem = ET.SubElement(res, "inventory")
    for item in state.resources.inventory:
        ET.SubElement(inv_elem, "item", name=item.name, tags=",".join(item.tags))

    # state_machines
    machines = ET.SubElement(root, "state_machines")
    clocks_elem = ET.SubElement(machines, "clocks")
    for c in state.state_machines.clocks:
        ET.SubElement(clocks_elem, "clock",
                      id=c.id, name=c.name, type=c.type.value,
                      segments=str(c.segments), filled=str(c.filled),
                      linked_to=c.linked_to)
    tracks_elem = ET.SubElement(machines, "progress_tracks")
    for t in state.state_machines.progress_tracks:
        ET.SubElement(tracks_elem, "track",
                      id=t.id, name=t.name, rank=t.rank.value,
                      boxes_filled=str(t.boxes_filled),
                      ticks_in_current_box=str(t.ticks_in_current_box))

    # safety_profile
    profile_elem = ET.SubElement(root, "safety_profile")
    for cat in state.safety_profile.categories:
        ET.SubElement(profile_elem, "content_category",
                      name=cat.name, status=cat.status.value, guidance=cat.guidance)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require(elem: Element, tag: str) -> Element:
    child = elem.find(tag)
    if child is None:
        raise ValueError(f"Missing required element <{tag}> inside <{elem.tag}>")
    return child


def _attr(elem: Element, name: str) -> str:
    val = elem.get(name)
    if val is None:
        raise ValueError(f"<{elem.tag}> missing required attribute '{name}'")
    return val


def _parse_root(root: Element) -> SessionState:
    session_elem = _require(root, "session_state")
    resources_elem = root.find("resources")
    machines_elem = root.find("state_machines")
    profile_elem = root.find("safety_profile")

    return SessionState(
        campaign=_parse_campaign(_require(session_elem, "campaign")),
        play_state=_parse_play_state(_require(session_elem, "play_state")),
        player_state=_parse_player_state(_require(session_elem, "player_state")),
        resolution_state=_parse_resolution_state(_require(session_elem, "resolution_state")),
        safety_state=_parse_safety_state(_require(session_elem, "safety_state")),
        resources=_parse_resources(resources_elem) if resources_elem is not None else Resources(),
        state_machines=_parse_machines(machines_elem) if machines_elem is not None else StateMachines(),
        safety_profile=_parse_profile(profile_elem) if profile_elem is not None else SafetyProfile(),
    )


def _parse_campaign(elem: Element) -> CampaignMeta:
    return CampaignMeta(
        id=_attr(elem, "id"),
        title=_attr(elem, "title"),
        genre=_attr(elem, "genre"),
        tone=_attr(elem, "tone"),
        canon_mode=_attr(elem, "canon_mode"),
        orchestration_mode=OrchestrationMode(_attr(elem, "orchestration_mode")),
    )


def _parse_play_state(elem: Element) -> PlayState:
    return PlayState(
        mode=PlayMode(_attr(elem, "mode")),
        scene_id=_attr(elem, "scene_id"),
        location=_attr(elem, "location"),
        objective=_attr(elem, "objective"),
        time_marker=_attr(elem, "time_marker"),
    )


def _parse_player_state(elem: Element) -> PlayerState:
    return PlayerState(
        character_name=_attr(elem, "character_name"),
        deep_pov=_attr(elem, "deep_pov").lower() == "true",
        stress=int(_attr(elem, "stress")),
        momentum=int(_attr(elem, "momentum")),
        harm=HarmLevel(_attr(elem, "harm")),
        load=LoadState(_attr(elem, "load")),
    )


def _parse_resolution_state(elem: Element) -> ResolutionState:
    return ResolutionState(
        position=Position(_attr(elem, "position")),
        effect=Effect(_attr(elem, "effect")),
        move_trigger=_attr(elem, "move_trigger"),
        stakes=_attr(elem, "stakes"),
    )


def _parse_safety_state(elem: Element) -> SafetyState:
    return SafetyState(
        hard_stop=_attr(elem, "hard_stop").lower() == "true",
        pause=_attr(elem, "pause").lower() == "true",
        intensity_check=_attr(elem, "intensity_check"),
    )


def _parse_resources(elem: Element) -> Resources:
    resources = Resources()

    attrs_elem = elem.find("attributes")
    if attrs_elem is not None:
        for a in attrs_elem.findall("attribute"):
            name = _attr(a, "name")
            if name in CANONICAL_ATTRIBUTES:
                resources.attributes.append(Attribute(name=name, value=int(_attr(a, "value"))))

    bonuses_elem = elem.find("bonuses")
    if bonuses_elem is not None:
        for b in bonuses_elem.findall("bonus"):
            resources.bonuses.append(Bonus(source=_attr(b, "source"), value=int(_attr(b, "value"))))

    rels_elem = elem.find("relationships")
    if rels_elem is not None:
        for r in rels_elem.findall("relationship"):
            resources.relationships.append(
                Relationship(
                    npc=_attr(r, "npc"),
                    status=_attr(r, "status"),
                    clock_ref=r.get("clock_ref", ""),
                )
            )

    inv_elem = elem.find("inventory")
    if inv_elem is not None:
        for item in inv_elem.findall("item"):
            tags_raw = item.get("tags", "")
            resources.inventory.append(
                InventoryItem(
                    name=_attr(item, "name"),
                    tags=[t.strip() for t in tags_raw.split(",") if t.strip()],
                )
            )

    return resources


def _parse_machines(elem: Element) -> StateMachines:
    machines = StateMachines()

    clocks_elem = elem.find("clocks")
    if clocks_elem is not None:
        for c in clocks_elem.findall("clock"):
            machines.clocks.append(
                Clock(
                    id=_attr(c, "id"),
                    name=_attr(c, "name"),
                    type=ClockType(_attr(c, "type")),
                    segments=int(_attr(c, "segments")),
                    filled=int(_attr(c, "filled")),
                    linked_to=c.get("linked_to", ""),
                )
            )

    tracks_elem = elem.find("progress_tracks")
    if tracks_elem is not None:
        for t in tracks_elem.findall("track"):
            machines.progress_tracks.append(
                ProgressTrack(
                    id=_attr(t, "id"),
                    name=_attr(t, "name"),
                    rank=TrackRank(_attr(t, "rank")),
                    boxes_filled=int(_attr(t, "boxes_filled")),
                    ticks_in_current_box=int(_attr(t, "ticks_in_current_box")),
                )
            )

    return machines


def _parse_profile(elem: Element) -> SafetyProfile:
    profile = SafetyProfile()
    for cat in elem.findall("content_category"):
        profile.categories.append(
            ContentCategory(
                name=_attr(cat, "name"),
                status=ContentStatus(_attr(cat, "status")),
                guidance=cat.get("guidance", ""),
            )
        )
    return profile
