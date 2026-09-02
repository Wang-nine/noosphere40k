"""B-05: growth & vocation eligibility."""

from __future__ import annotations

from noosphere40k.domain.models import PlayerCharacter, WorldTime
from noosphere40k.rules.lifepath import (
    VocationDefinition,
    check_vocation_eligibility,
    skill_rank_for_progress,
)


def _character(stage: str = "youth", age_days: int = 365 * 18, skills=None) -> PlayerCharacter:
    return PlayerCharacter(
        character_id="pc",
        display_name="Ada",
        birth_world_time=WorldTime(era_id="e", local_calendar_id="l", ordering_key=0, precision="era"),
        chronological_age_days=age_days,
        subjective_age_days=age_days,
        life_stage=stage,
        origin_id="origin.hive_worker_household",
        skills=skills or {},
    )


def test_skill_rank_from_progress() -> None:
    assert skill_rank_for_progress(0) == "untrained"
    assert skill_rank_for_progress(10) == "trained"
    assert skill_rank_for_progress(35) == "specialist"
    assert skill_rank_for_progress(60) == "master"


def test_vocation_eligible_when_requirements_met() -> None:
    vocation = VocationDefinition(
        vocation_id="admin_clerk",
        display_name="档案吏",
        min_age_years=16,
        requires_skill="literacy",
        requires_skill_rank="trained",
    )
    character = _character(skills={"literacy": {"rank": "trained", "progress": 15}})
    result = check_vocation_eligibility(character, vocation)
    assert result.eligible is True
    assert result.reasons == []


def test_vocation_rejects_young_age() -> None:
    vocation = VocationDefinition(vocation_id="admin_clerk", display_name="档案吏", min_age_years=16)
    character = _character(age_days=365 * 10)
    result = check_vocation_eligibility(character, vocation)
    assert result.eligible is False
    assert any("年龄" in r for r in result.reasons)


def test_vocation_rejects_missing_skill_rank() -> None:
    vocation = VocationDefinition(
        vocation_id="admin_clerk",
        display_name="档案吏",
        requires_skill="literacy",
        requires_skill_rank="trained",
    )
    character = _character(skills={"literacy": {"rank": "untrained", "progress": 3}})
    result = check_vocation_eligibility(character, vocation)
    assert result.eligible is False
    assert any("前置技能" in r for r in result.reasons)


def test_vocation_requires_content_pack() -> None:
    vocation = VocationDefinition(
        vocation_id="tech_adept",
        display_name="技术辅祭",
        requires_content_pack="campaign.tech_pack",
    )
    character = _character()
    result = check_vocation_eligibility(character, vocation, installed_packs=set())
    assert result.eligible is False
    assert any("内容包" in r for r in result.reasons)

    ok = check_vocation_eligibility(character, vocation, installed_packs={"campaign.tech_pack"})
    assert ok.eligible is True


def test_vocation_requires_relation() -> None:
    vocation = VocationDefinition(
        vocation_id="enforcer", display_name="执法者", requires_relation="npc.enforcer_master"
    )
    character = _character()
    result = check_vocation_eligibility(character, vocation, relationships={})
    assert result.eligible is False
    assert any("关系" in r for r in result.reasons)

    ok = check_vocation_eligibility(
        character, vocation, relationships={"npc.enforcer_master": {}}
    )
    assert ok.eligible is True