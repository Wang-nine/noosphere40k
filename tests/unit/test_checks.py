"""B-01/B-03: attribute/skill/modifier models and d100 resolution."""

from __future__ import annotations

import pytest

from noosphere40k.domain.errors import RuleInvalidActionError
from noosphere40k.rules.checks import (
    TARGET_CLAMP_MAX,
    TARGET_CLAMP_MIN,
    CheckRequest,
    Modifier,
    compute_target,
    resolve_attribute_check,
    resolve_check,
    skill_bonus,
    validate_attribute_value,
    validate_difficulty_tier,
)


def _request(**overrides) -> CheckRequest:
    data = {
        "check_id": "c1",
        "actor_id": "pc",
        "attribute_id": "awareness",
        "risk": "standard",
    }
    data.update(overrides)
    return CheckRequest(**data)


def test_attribute_range_validation() -> None:
    assert validate_attribute_value(25) == 25
    with pytest.raises(RuleInvalidActionError):
        validate_attribute_value(0)
    with pytest.raises(RuleInvalidActionError):
        validate_attribute_value(101)


def test_difficulty_tiers_are_stable() -> None:
    assert validate_difficulty_tier(-30) == -30
    assert validate_difficulty_tier(30) == 30
    with pytest.raises(RuleInvalidActionError):
        validate_difficulty_tier(-15)


def test_skill_bonus_table() -> None:
    assert skill_bonus(None) == 0
    assert skill_bonus("untrained") == 0
    assert skill_bonus("trained") == 10
    assert skill_bonus("specialist") == 20
    assert skill_bonus("master") == 30
    with pytest.raises(RuleInvalidActionError):
        skill_bonus("legendary")


def test_target_clamping() -> None:
    req = _request()
    assert compute_target(req, 1, None) == TARGET_CLAMP_MIN
    assert compute_target(req, 100, None) == TARGET_CLAMP_MAX


def test_target_combines_attribute_skill_difficulty() -> None:
    req = _request(difficulty_modifier=+10)
    assert compute_target(req, 30, "trained") == 50


def test_resolve_success_and_margin() -> None:
    result = resolve_check(_request(difficulty_modifier=0), 30, attribute_value=40, rank=None)
    assert result.success is True
    assert result.margin_degrees == 2  # floor(|40-30|/10)+1


def test_resolve_failure() -> None:
    result = resolve_check(_request(), 60, attribute_value=40, rank=None)
    assert result.success is False
    assert result.margin_degrees == 3


def test_special_01_and_100() -> None:
    assert resolve_check(_request(), 1, attribute_value=40, rank=None).special == "critical_success"
    assert resolve_check(_request(), 100, attribute_value=40, rank=None).special == "critical_failure"


def test_duplicate_modifier_source_rejected() -> None:
    mod = Modifier(
        modifier_id="m1", value=5, source_type="item", source_id="lasgun", display_reason="x"
    )
    req = _request(situation_modifiers=[mod, mod.model_copy(update={"modifier_id": "m2"})])
    with pytest.raises(RuleInvalidActionError):
        resolve_check(req, 50, attribute_value=40, rank=None)


def test_modifier_without_source_rejected() -> None:
    mod = Modifier(modifier_id="m1", value=5, source_type="rule", source_id="", display_reason="x")
    req = _request(situation_modifiers=[mod])
    with pytest.raises(RuleInvalidActionError):
        resolve_check(req, 50, attribute_value=40, rank=None)


def test_unknown_attribute_rejected() -> None:
    req = _request(attribute_id="charisma")
    with pytest.raises(RuleInvalidActionError):
        resolve_attribute_check(req, 50, attributes={"awareness": 40}, skills={})


def test_unknown_skill_rejected() -> None:
    req = _request(skill_id="melee_art")
    with pytest.raises(RuleInvalidActionError):
        resolve_attribute_check(
            req, 50, attributes={"awareness": 40},
            skills={"driving": {"rank": "trained"}},
        )


def test_roll_out_of_range_rejected() -> None:
    with pytest.raises(RuleInvalidActionError):
        resolve_check(_request(), 0, attribute_value=40, rank=None)


def test_skill_rank_bonus_in_resolve() -> None:
    req = _request(skill_id="survival")
    result = resolve_attribute_check(
        req, 40,
        attributes={"awareness": 40},
        skills={"survival": {"rank": "trained"}},
    )
    assert result.target == 50
    assert result.success is True