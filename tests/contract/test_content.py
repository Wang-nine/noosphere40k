"""F-01: content schema and validator tests."""

from __future__ import annotations

import pytest

from noosphere40k.content.loader import load_pack_json
from noosphere40k.content.schemas import (
    LoreRequirement,
    NarrationTemplate,
    SceneDefinition,
    ScenePack,
)
from noosphere40k.content.validator import validate_pack
from noosphere40k.domain.errors import ContentMissingError


def _minimal_scene(**overrides) -> SceneDefinition:
    data = {
        "scene_id": "scene.a",
        "pack_id": "pack.a",
        "title": "A",
        "location_id": "loc.1",
        "fallback_narration_template_id": "tpl.a",
    }
    data.update(overrides)
    return SceneDefinition(**data)


def _pack(scenes, templates=None) -> ScenePack:
    return ScenePack(
        pack_id="pack.a",
        version="1.0.0",
        scenes=scenes,
        templates=templates or [
            NarrationTemplate(template_id="tpl.a", pack_id="pack.a", text="hello", variables=set())
        ],
    )


def test_valid_pack_passes() -> None:
    pack = _pack([_minimal_scene()])
    validate_pack(pack)  # should not raise


def test_duplicate_scene_id_rejected() -> None:
    pack = _pack([_minimal_scene(), _minimal_scene()])
    with pytest.raises(ContentMissingError):
        validate_pack(pack)


def test_missing_fallback_template_rejected() -> None:
    scene = _minimal_scene(fallback_narration_template_id="tpl.missing")
    with pytest.raises(ContentMissingError):
        validate_pack(_pack([scene]))


def test_hard_requirement_without_fact_rejected() -> None:
    scene = _minimal_scene()
    scene.lore_requirements.hard.append(
        LoreRequirement(requirement_id="r1", hard=True, fact_id=None)
    )
    with pytest.raises(ContentMissingError):
        validate_pack(_pack([scene]))


def test_childhood_scene_forbids_adult_tags() -> None:
    scene = _minimal_scene(allowed_life_stages={"childhood"}, content_tags={"erotic"})
    with pytest.raises(ContentMissingError):
        validate_pack(_pack([scene]))


def test_transition_to_missing_scene_rejected() -> None:
    from noosphere40k.content.schemas import TransitionRule

    scene = _minimal_scene()
    scene.next_scene_rules.append(
        TransitionRule(priority=1, next_scene_id="scene.nope", predicates=[])
    )
    with pytest.raises(ContentMissingError):
        validate_pack(_pack([scene]))


def test_unknown_schema_version_rejected() -> None:
    pack = ScenePack(pack_id="p", version="1", schema_version=99, scenes=[])
    with pytest.raises(ContentMissingError):
        validate_pack(pack)


def test_loader_rejects_missing_file(tmp_path) -> None:
    from noosphere40k.content.loader import load_pack_json

    with pytest.raises(ContentMissingError):
        load_pack_json(tmp_path / "nope.json")


def test_tutorial_pack_loads_and_validates() -> None:
    from noosphere40k.application.campaign_service import TUTORIAL_PACK_PATH

    pack = load_pack_json(TUTORIAL_PACK_PATH)
    assert pack.pack_id == "scenario.tutorial_hive_worker"
    assert len(pack.scenes) == 3
    assert len(pack.templates) == 3
    assert all(not t.variables - {"display_name"} for t in pack.templates)