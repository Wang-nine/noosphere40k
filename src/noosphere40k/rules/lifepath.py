"""Growth and vocation system (TECHNICAL_SPEC §7.6; B-05).

Skills come from experienced events (SkillProgressed carries a
learned_from_event_id). Vocation routes check age, prerequisite skill ranks,
relationships and installed content packs; they cannot be claimed freely.
"""

from __future__ import annotations

from dataclasses import dataclass

from noosphere40k.domain.models import PlayerCharacter, StrictModel
from noosphere40k.rules.checks import SKILL_BONUS_BY_RANK

MIN_RANK_BY_AGE = {"trained": 12, "specialist": 16, "master": 25}


class VocationDefinition(StrictModel):
    vocation_id: str
    display_name: str
    min_age_years: int = 12
    requires_skill: str | None = None
    requires_skill_rank: str = "trained"
    requires_relation: str | None = None
    requires_content_pack: str | None = None


@dataclass
class Eligibility:
    eligible: bool
    reasons: list[str]


def skill_rank_for_progress(progress: int) -> str:
    if progress >= 60:
        return "master"
    if progress >= 35:
        return "specialist"
    if progress >= 10:
        return "trained"
    return "untrained"


def check_vocation_eligibility(
    character: PlayerCharacter,
    vocation: VocationDefinition,
    *,
    installed_packs: set[str] | None = None,
    relationships: dict[str, object] | None = None,
) -> Eligibility:
    reasons: list[str] = []
    age_years = character.chronological_age_days / 365.0

    if age_years < vocation.min_age_years:
        reasons.append(f"年龄不足：需要 {vocation.min_age_years} 岁，当前约 {int(age_years)} 岁")

    if vocation.requires_content_pack and (
        not installed_packs or vocation.requires_content_pack not in installed_packs
    ):
        reasons.append(f"缺少内容包：{vocation.requires_content_pack}")

    if vocation.requires_skill:
        skill = character.skills.get(vocation.requires_skill, {})
        rank = str(skill.get("rank", "untrained"))
        required_index = list(SKILL_BONUS_BY_RANK.keys()).index(vocation.requires_skill_rank)
        actual_index = list(SKILL_BONUS_BY_RANK.keys()).index(rank)
        if actual_index < required_index:
            reasons.append(
                f"前置技能不足：{vocation.requires_skill} 需要 {vocation.requires_skill_rank}，"
                f"当前 {rank}"
            )

    if vocation.requires_relation and relationships is not None and vocation.requires_relation not in relationships:
        reasons.append(f"缺少前置关系：{vocation.requires_relation}")

    return Eligibility(eligible=not reasons, reasons=reasons)


def apply_vocation_start(
    character: PlayerCharacter,
    vocation: VocationDefinition,
    *,
    organization_id: str | None = None,
) -> dict[str, object]:
    """Return the events/state payload for starting a vocation (VocationStarted)."""
    return {
        "vocation_id": vocation.vocation_id,
        "organization_id": organization_id or vocation.display_name,
    }


def derive_attribute_aging_delta(character: PlayerCharacter, stage: str, years_passed: int) -> dict[str, int]:
    """Deterministic small attribute deltas from aging alone (used by lifepath)."""
    from noosphere40k.rules.aging import STAGE_GROWTH

    deltas: dict[str, int] = {}
    base = STAGE_GROWTH.get(stage, {})
    for attr, growth in base.items():
        deltas[attr] = max(-2, min(2, growth))
    return deltas


__all__ = [
    "VocationDefinition",
    "Eligibility",
    "check_vocation_eligibility",
    "apply_vocation_start",
    "skill_rank_for_progress",
    "derive_attribute_aging_delta",
]