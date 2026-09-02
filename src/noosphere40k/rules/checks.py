"""Attribute, skill and modifier models plus the generic d100 check (B-01/B-03).

Ruleset (TECHNICAL_SPEC §7):
- attributes are stored 1..100; typical starting humans 20..45.
- final target clamps to 5..95 by default.
- difficulty modifier tiers: -30, -20, -10, 0, +10, +20, +30.
- roll <= target succeeds; 01 is a special success, 100 a special failure.
- success/failure margin = floor(abs(target - roll) / 10) + 1.
"""

from __future__ import annotations

from pydantic import Field

from noosphere40k.domain.enums import ModifierSourceType, RiskLevel, RngVisibility
from noosphere40k.domain.errors import RuleInvalidActionError
from noosphere40k.domain.models import StrictModel

ATTRIBUTE_MIN = 1
ATTRIBUTE_MAX = 100
CREATION_ATTRIBUTE_MIN = 20
CREATION_ATTRIBUTE_MAX = 45

TARGET_CLAMP_MIN = 5
TARGET_CLAMP_MAX = 95

DIFFICULTY_TIERS: tuple[int, ...] = (-30, -20, -10, 0, 10, 20, 30)

# Skill rank bonus table (ruleset version "0.1.0").
SKILL_BONUS_BY_RANK: dict[str, int] = {
    "untrained": 0,
    "trained": 10,
    "specialist": 20,
    "master": 30,
}

RULESET_VERSION = "0.1.0"


class Modifier(StrictModel):
    modifier_id: str
    value: int
    source_type: ModifierSourceType
    source_id: str
    display_reason: str


class CheckRequest(StrictModel):
    check_id: str
    actor_id: str
    attribute_id: str
    skill_id: str | None = None
    difficulty_modifier: int = 0
    situation_modifiers: list[Modifier] = Field(default_factory=list)
    risk: RiskLevel = RiskLevel.STANDARD
    visibility: RngVisibility = RngVisibility.OPEN
    stakes: list[str] = Field(default_factory=list)


class CheckResult(StrictModel):
    check_id: str
    roll: int
    target: int
    success: bool
    margin_degrees: int
    special: str = "none"
    modifiers: list[Modifier] = Field(default_factory=list)
    rng_event_id: str | None = None


def validate_attribute_value(value: int) -> int:
    if not ATTRIBUTE_MIN <= value <= ATTRIBUTE_MAX:
        raise RuleInvalidActionError(
            f"attribute value {value} out of range [{ATTRIBUTE_MIN}, {ATTRIBUTE_MAX}]",
            context={"value": value},
        )
    return value


def validate_difficulty_tier(modifier: int) -> int:
    if modifier not in DIFFICULTY_TIERS:
        raise RuleInvalidActionError(
            f"difficulty modifier {modifier} not in allowed tiers {DIFFICULTY_TIERS}",
            context={"modifier": modifier},
        )
    return modifier


def validate_no_duplicate_modifier_sources(
    modifiers: list[Modifier], *, request: CheckRequest
) -> None:
    seen: set[tuple[str, str]] = set()
    for modifier in modifiers:
        key = (modifier.source_type.value, modifier.source_id)
        if key in seen:
            raise RuleInvalidActionError(
                f"duplicate modifier source: {key}",
                context={"check_id": request.check_id, "modifier_id": modifier.modifier_id},
            )
        if not modifier.source_id:
            raise RuleInvalidActionError(
                f"modifier {modifier.modifier_id} has no source id",
                context={"check_id": request.check_id},
            )
        seen.add(key)


def skill_bonus(rank: str | None) -> int:
    if rank is None:
        return 0
    if rank not in SKILL_BONUS_BY_RANK:
        raise RuleInvalidActionError(
            f"unknown skill rank: {rank}",
            context={"rank": rank},
        )
    return SKILL_BONUS_BY_RANK[rank]


def compute_target(request: CheckRequest, attribute_value: int, rank: str | None) -> int:
    validate_attribute_value(attribute_value)
    validate_difficulty_tier(request.difficulty_modifier)
    raw = attribute_value + skill_bonus(rank) + request.difficulty_modifier
    for modifier in request.situation_modifiers:
        raw += modifier.value
    return max(TARGET_CLAMP_MIN, min(TARGET_CLAMP_MAX, raw))


def resolve_check(request: CheckRequest, roll: int, *, attribute_value: int, rank: str | None, rng_event_id: str | None = None) -> CheckResult:
    """Resolve a d100 check against the request and attribute state."""
    validate_no_duplicate_modifier_sources(request.situation_modifiers, request=request)
    if not 1 <= roll <= 100:
        raise RuleInvalidActionError(
            f"roll {roll} out of 1..100",
            context={"check_id": request.check_id},
        )
    target = compute_target(request, attribute_value, rank)
    success = roll <= target
    margin = (abs(target - roll) // 10) + 1
    special = "none"
    if roll == 1:
        special = "critical_success"
    elif roll == 100:
        special = "critical_failure"
    return CheckResult(
        check_id=request.check_id,
        roll=roll,
        target=target,
        success=success,
        margin_degrees=margin,
        special=special,
        modifiers=list(request.situation_modifiers),
        rng_event_id=rng_event_id,
    )


def resolve_attribute_check(
    request: CheckRequest,
    roll: int,
    *,
    attributes: dict[str, int],
    skills: dict[str, dict[str, object]] | None = None,
    rng_event_id: str | None = None,
) -> CheckResult:
    """Resolve against a character's attribute/skill dictionaries."""
    if request.attribute_id not in attributes:
        raise RuleInvalidActionError(
            f"actor {request.actor_id} has no attribute {request.attribute_id}",
            context={"check_id": request.check_id, "attribute_id": request.attribute_id},
        )
    rank: str | None = None
    if request.skill_id is not None:
        skill = (skills or {}).get(request.skill_id)
        if skill is None:
            raise RuleInvalidActionError(
                f"actor {request.actor_id} has no skill {request.skill_id}",
                context={"check_id": request.check_id, "skill_id": request.skill_id},
            )
        rank = str(skill.get("rank", "untrained"))
    return resolve_check(
        request,
        roll,
        attribute_value=attributes[request.attribute_id],
        rank=rank,
        rng_event_id=rng_event_id,
    )