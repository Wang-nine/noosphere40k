"""Content pack validation (F-01).

A validated pack must reject:
- unknown schema version,
- scene without fallback template,
- hard LoreRequirement without a fact,
- childhood scene with adult/erotic tags or forced graphic violence,
- duplicate IDs,
- template variables outside the safe allowlist,
- non-existent fallback template references.
"""

from __future__ import annotations

from noosphere40k.content.schemas import (
    SAFE_TEMPLATE_VARIABLES,
    LoreRequirement,
    SceneDefinition,
    ScenePack,
)
from noosphere40k.domain.errors import ContentMissingError

CHILDHOOD_FORBIDDEN_TAGS: frozenset[str] = frozenset(
    {"erotic", "sexual", "adult_relationship", "graphic_violence_strong"}
)


def validate_pack(pack: ScenePack) -> None:
    if pack.schema_version != 1:
        raise ContentMissingError(
            f"unknown schema version {pack.schema_version}",
            context={"pack_id": pack.pack_id},
        )

    scene_ids: set[str] = set()
    template_ids = {t.template_id for t in pack.templates}
    for scene in pack.scenes:
        _validate_scene(pack, scene, scene_ids, template_ids)
    _validate_transition_targets(pack, scene_ids)


def _validate_scene(
    pack: ScenePack,
    scene: SceneDefinition,
    scene_ids: set[str],
    template_ids: set[str],
) -> None:
    if scene.scene_id in scene_ids:
        raise ContentMissingError(
            f"duplicate scene id: {scene.scene_id}",
            context={"pack_id": pack.pack_id},
        )
    scene_ids.add(scene.scene_id)

    if scene.fallback_narration_template_id not in template_ids:
        raise ContentMissingError(
            f"scene {scene.scene_id} references missing fallback template "
            f"{scene.fallback_narration_template_id}",
            context={"pack_id": pack.pack_id},
        )

    if "childhood" in scene.allowed_life_stages:
        forbidden = scene.content_tags & CHILDHOOD_FORBIDDEN_TAGS
        if forbidden:
            raise ContentMissingError(
                f"childhood scene {scene.scene_id} has forbidden tags: {sorted(forbidden)}",
                context={"pack_id": pack.pack_id},
            )

    for req in scene.lore_requirements.hard:
        _validate_hard_requirement(req)


def _validate_hard_requirement(req: LoreRequirement) -> None:
    if req.hard and not req.fact_id:
        raise ContentMissingError(
            f"hard lore requirement {req.requirement_id} has no fact_id",
            context={"requirement_id": req.requirement_id},
        )


def _validate_transition_targets(pack: ScenePack, scene_ids: set[str]) -> None:
    for scene in pack.scenes:
        for rule in scene.next_scene_rules:
            if rule.next_scene_id is not None and rule.next_scene_id not in scene_ids:
                raise ContentMissingError(
                    f"scene {scene.scene_id} points to missing next scene {rule.next_scene_id}",
                    context={"pack_id": pack.pack_id},
                )
    for transition in pack.transitions:
        if transition.aging_ruleset_id not in {"age_ruleset.standard"}:
            raise ContentMissingError(
                f"transition {transition.transition_id} uses unknown aging ruleset "
                f"{transition.aging_ruleset_id}",
                context={"pack_id": pack.pack_id},
            )


def validate_template_variables(pack: ScenePack) -> None:
    """Ensure template variables stay within the safe allowlist."""
    for template in pack.templates:
        unknown = template.variables - SAFE_TEMPLATE_VARIABLES
        if unknown:
            raise ContentMissingError(
                f"template {template.template_id} uses disallowed variables: {sorted(unknown)}",
                context={"pack_id": pack.pack_id},
            )


__all__ = ["validate_pack", "validate_template_variables"]