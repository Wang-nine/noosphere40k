"""Life content pack schema + loader (F-03…F-07).

Structured, reviewable content for the full lifepath: three childhood
origins, the adolescence chapter, four young-adult vocation routes, the
adulthood convergence (Ashen Register) and the late-life endings.

All local world facts are ``game_original`` placeholders and must never be
presented as approved official 40K lore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from noosphere40k.domain.errors import ContentMissingError
from noosphere40k.domain.models import StrictModel


class LifeEvent(StrictModel):
    event_id: str
    title: str
    kind: str  # required | optional | life_event
    description: str
    content_tags: set[str] = Field(default_factory=set)


class OriginTemplate(StrictModel):
    origin_id: str
    display_name: str
    start_location_id: str
    core_relations: list[str] = Field(default_factory=list)
    early_systems: list[str] = Field(default_factory=list)
    required_events: list[LifeEvent] = Field(default_factory=list)
    optional_events: list[LifeEvent] = Field(default_factory=list)
    life_events: list[LifeEvent] = Field(default_factory=list)


class VocationRoute(StrictModel):
    route_id: str
    display_name: str
    scenes: list[LifeEvent] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    non_combat_options: list[str] = Field(default_factory=list)
    blind_spot: str = ""


class Stance(StrictModel):
    stance_id: str
    display_name: str
    evidence_route_ids: list[str] = Field(default_factory=list)
    requires_single_roll: bool = False


class EndingType(StrictModel):
    ending_id: str
    display_name: str
    condition: str


class LifeContentPack(StrictModel):
    pack_id: str
    version: str
    schema_version: int = 1
    origins: dict[str, OriginTemplate] = Field(default_factory=dict)
    adolescence_scenes: list[LifeEvent] = Field(default_factory=list)
    routes: dict[str, VocationRoute] = Field(default_factory=dict)
    convergence_stances: list[Stance] = Field(default_factory=list)
    ending_types: list[EndingType] = Field(default_factory=list)
    childhood_echo_scene_id: str | None = None


def load_life_content_pack(path: Path) -> LifeContentPack:
    if not path.exists():
        raise ContentMissingError(f"life content pack not found: {path}", context={"path": str(path)})
    try:
        with path.open("r", encoding="utf-8") as fh:
            data: Any = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as exc:
        raise ContentMissingError(
            f"invalid life content YAML: {path}", context={"path": str(path)}
        ) from exc
    if not isinstance(data, dict):
        raise ContentMissingError("life content pack root must be a mapping")
    pack = LifeContentPack.model_validate(data)
    validate_life_content(pack)
    return pack


def validate_life_content(pack: LifeContentPack) -> None:
    """Structural validation per F-03..F-07 acceptance criteria."""
    if pack.schema_version != 1:
        raise ContentMissingError(f"unknown life content schema: {pack.schema_version}")

    # F-03: each origin must have >=5 required, >=8 optional, >=3 life events.
    for origin_id, origin in pack.origins.items():
        if len(origin.required_events) < 5:
            raise ContentMissingError(
                f"origin {origin_id} needs >=5 required events, got {len(origin.required_events)}"
            )
        if len(origin.optional_events) < 8:
            raise ContentMissingError(
                f"origin {origin_id} needs >=8 optional events, got {len(origin.optional_events)}"
            )
        if len(origin.life_events) < 3:
            raise ContentMissingError(
                f"origin {origin_id} needs >=3 life events, got {len(origin.life_events)}"
            )
        _check_childhood_safety(origin, origin_id)

    # F-05: each route needs >=5 scenes, >=3 evidence, >=2 non-combat options.
    for route_id, route in pack.routes.items():
        if len(route.scenes) < 5:
            raise ContentMissingError(
                f"route {route_id} needs >=5 scenes, got {len(route.scenes)}"
            )
        if len(route.evidence) < 3:
            raise ContentMissingError(
                f"route {route_id} needs >=3 evidence, got {len(route.evidence)}"
            )
        if len(route.non_combat_options) < 2:
            raise ContentMissingError(
                f"route {route_id} needs >=2 non-combat options, got {len(route.non_combat_options)}"
            )

    # F-06: every stance must be reachable from >=2 routes and no single-roll gating.
    for stance in pack.convergence_stances:
        if len(stance.evidence_route_ids) < 2:
            raise ContentMissingError(
                f"stance {stance.stance_id} must be reachable from >=2 routes"
            )
        if stance.requires_single_roll:
            raise ContentMissingError(
                f"stance {stance.stance_id} must not depend on a single roll (F-06)"
            )

    # F-07: at least 6 ending types and a childhood echo.
    if len(pack.ending_types) < 6:
        raise ContentMissingError(f"need >=6 ending types, got {len(pack.ending_types)}")
    if pack.childhood_echo_scene_id is None:
        raise ContentMissingError("late-life must include a childhood echo scene (F-07)")


def _check_childhood_safety(origin: OriginTemplate, origin_id: str) -> None:
    forbidden = {"erotic", "sexual", "adult_relationship", "graphic_violence_strong"}
    for group_name, group in (
        ("required", origin.required_events),
        ("optional", origin.optional_events),
        ("life", origin.life_events),
    ):
        for event in group:
            bad = event.content_tags & forbidden
            if bad:
                raise ContentMissingError(
                    f"origin {origin_id} {group_name} event {event.event_id} has "
                    f"forbidden childhood tags: {sorted(bad)}"
                )


__all__ = [
    "LifeContentPack",
    "OriginTemplate",
    "VocationRoute",
    "Stance",
    "EndingType",
    "LifeEvent",
    "load_life_content_pack",
    "validate_life_content",
]