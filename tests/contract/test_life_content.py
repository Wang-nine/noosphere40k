"""F-03..F-07: life content pack validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.content.life_content import load_life_content_pack
from noosphere40k.domain.errors import ContentMissingError

LIFE_PACK = Path(__file__).resolve().parents[2] / "content" / "life_content" / "pack.yaml"


def test_life_content_pack_loads_and_validates() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    assert pack.pack_id == "lifepath.content.imperium_frontier"
    assert len(pack.origins) == 3


def test_f03_origins_have_required_event_counts() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    for origin_id, origin in pack.origins.items():
        assert len(origin.required_events) >= 5, origin_id
        assert len(origin.optional_events) >= 8, origin_id
        assert len(origin.life_events) >= 3, origin_id


def test_f03_childhood_safety() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    forbidden = {"erotic", "sexual", "adult_relationship", "graphic_violence_strong"}
    for origin in pack.origins.values():
        all_events = origin.required_events + origin.optional_events + origin.life_events
        for event in all_events:
            assert not (event.content_tags & forbidden), event.event_id


def test_f05_routes_have_counts() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    assert len(pack.routes) == 4
    for route_id, route in pack.routes.items():
        assert len(route.scenes) >= 5, route_id
        assert len(route.evidence) >= 3, route_id
        assert len(route.non_combat_options) >= 2, route_id


def test_f06_stances_no_single_roll_and_reachable() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    assert len(pack.convergence_stances) >= 6
    for stance in pack.convergence_stances:
        assert stance.requires_single_roll is False
        assert len(stance.evidence_route_ids) >= 2


def test_f07_endings_and_childhood_echo() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    assert len(pack.ending_types) >= 6
    assert pack.childhood_echo_scene_id is not None


def test_f06_four_routes_can_reach_all_stances() -> None:
    pack = load_life_content_pack(LIFE_PACK)
    route_ids = set(pack.routes.keys())
    reachable = set()
    for stance in pack.convergence_stances:
        reachable.update(stance.evidence_route_ids)
    assert reachable == route_ids  # every route leads to a stance


def test_validator_rejects_missing_events(tmp_path: Path) -> None:
    from noosphere40k.content.life_content import LifeContentPack, validate_life_content

    bad = LifeContentPack(
        pack_id="x",
        version="1.0.0",
        origins={
            "origin.a": {
                "origin_id": "origin.a",
                "display_name": "A",
                "start_location_id": "loc",
                "required_events": [],
                "optional_events": [],
                "life_events": [],
            }
        },
    )
    with pytest.raises(ContentMissingError):
        validate_life_content(bad)