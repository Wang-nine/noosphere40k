"""Age and life-stage transitions (TECHNICAL_SPEC §5.2, §7.4; B-04).

Stage changes are ONLY accepted as LifeTransitionProposal handled by the rule
engine; the LLM can suggest a time jump but can never change age directly.
A transition is always previewable before it is settled; cancelling a preview
must produce zero events. Settling is deterministic given an injected RNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field

from noosphere40k.domain.errors import RuleInvalidActionError
from noosphere40k.domain.models import PlayerCharacter, StrictModel
from noosphere40k.rules.rng import RngService

# Reference age ranges (content packs may override per world/class).
STAGE_AGE_RANGES: dict[str, tuple[int, int]] = {
    "childhood": (6, 11),
    "adolescence": (12, 16),
    "youth": (17, 25),
    "adulthood": (26, 45),
    "late_life": (46, 120),
}

# Deterministic attribute growth by stage (identity + focus bonus).
STAGE_GROWTH: dict[str, dict[str, int]] = {
    "childhood": {"body": 2, "agility": 2, "awareness": 2, "intellect": 2},
    "adolescence": {"body": 3, "agility": 3, "intellect": 3, "presence": 2},
    "youth": {"body": 3, "agility": 3, "intellect": 3, "willpower": 2},
    "adulthood": {"body": 1, "intellect": 2, "willpower": 2, "presence": 2},
    "late_life": {"intellect": 1, "presence": 1, "body": -2, "agility": -2},
}

# Focus tag -> which attributes grow faster.
FOCUS_ATTRIBUTE_BONUS: dict[str, str] = {
    "labor": "body",
    "scholarship": "intellect",
    "faith": "willpower",
    "social": "presence",
    "hunting": "awareness",
    "martial": "ranged",
}


def age_to_days(years: int) -> int:
    return years * 365


def days_to_years(days: int) -> float:
    return days / 365.0


def stage_for_age(years: float) -> str:
    """Return the stage a character of this age belongs to (first match)."""
    for stage, (lo, hi) in STAGE_AGE_RANGES.items():
        if lo <= years <= hi:
            return stage
    return "late_life" if years > 120 else "childhood"


def is_valid_stage_transition(from_stage: str, to_stage: str) -> bool:
    """Stages may only advance forward (or straight to terminal)."""
    if to_stage == "terminal":
        return True
    order = list(STAGE_AGE_RANGES.keys())
    if from_stage not in order or to_stage not in order:
        return False
    return order.index(to_stage) > order.index(from_stage)


class LifeTransitionProposal(StrictModel):
    transition_id: str
    from_stage: str
    to_stage: str
    time_span_days: int
    aging_ruleset_id: str = "age_ruleset.standard"
    focus_tags: list[str] = Field(default_factory=list)
    relationship_focus: str | None = None
    avoided_risk: str | None = None
    confirmation_required: bool = True


@dataclass
class AgingEffect:
    attribute_deltas: dict[str, int] = field(default_factory=dict)
    skill_progress: dict[str, int] = field(default_factory=dict)
    health_note: str | None = None
    relationship_note: str | None = None
    summary: str = ""


@dataclass
class TransitionPreview:
    proposal: LifeTransitionProposal
    effects: AgingEffect
    irreversible_notes: list[str] = field(default_factory=list)

    def to_display(self) -> list[str]:
        lines = [
            f"时间跳跃：{self.proposal.time_span_days} 天",
            f"阶段：{self.proposal.from_stage} → {self.proposal.to_stage}",
            "属性变化：" + (", ".join(
                f"{k} {v:+d}" for k, v in self.effects.attribute_deltas.items()
            ) or "无"),
        ]
        if self.effects.skill_progress:
            lines.append("技能进度：" + ", ".join(
                f"{k} +{v}" for k, v in self.effects.skill_progress.items()
            ))
        if self.effects.health_note:
            lines.append(f"健康：{self.effects.health_note}")
        lines.extend(self.irreversible_notes)
        return lines


class LifeTransitionService:
    def __init__(self, rng: RngService | None = None) -> None:
        self.rng = rng or RngService(seed=42)

    def preview(self, proposal: LifeTransitionProposal, character: PlayerCharacter) -> TransitionPreview:
        self._validate(proposal, character)
        effects = self._compute_effects(proposal, character)
        irreversible: list[str] = []
        if proposal.from_stage == "childhood" and proposal.time_span_days > 365:
            irreversible.append("跨年会改变家庭与同伴关系")
        if any("body" in (k,) and v < 0 for k, v in effects.attribute_deltas.items()):
            irreversible.append("部分身体属性会永久下降")
        return TransitionPreview(proposal=proposal, effects=effects, irreversible_notes=irreversible)

    def settle(
        self,
        proposal: LifeTransitionProposal,
        character: PlayerCharacter,
    ) -> dict[str, object]:
        """Return the deterministic state changes as a flat mapping.

        The caller converts this into EventEnvelopes (AttributeChanged,
        SkillProgressed, TimeAdvanced, LifeStageChanged). Pure + deterministic.
        """
        self._validate(proposal, character)
        effects = self._compute_effects(proposal, character)
        new_age_days = character.chronological_age_days + proposal.time_span_days
        new_stage = stage_for_age(days_to_years(new_age_days))
        return {
            "new_chronological_age_days": new_age_days,
            "new_stage": new_stage,
            "attribute_deltas": effects.attribute_deltas,
            "skill_progress": effects.skill_progress,
            "health_note": effects.health_note,
            "relationship_note": effects.relationship_note,
        }

    # ---- internals ----

    def _validate(self, proposal: LifeTransitionProposal, character: PlayerCharacter) -> None:
        if proposal.aging_ruleset_id != "age_ruleset.standard":
            raise RuleInvalidActionError(
                f"unknown aging ruleset: {proposal.aging_ruleset_id}",
                context={"transition_id": proposal.transition_id},
            )
        if proposal.time_span_days <= 0:
            raise RuleInvalidActionError("time jump must be positive", context={"transition_id": proposal.transition_id})
        if proposal.from_stage != character.life_stage:
            raise RuleInvalidActionError(
                f"transition from_stage {proposal.from_stage} does not match current stage {character.life_stage}",
                context={"transition_id": proposal.transition_id},
            )
        if not is_valid_stage_transition(proposal.from_stage, proposal.to_stage):
            raise RuleInvalidActionError(
                f"illegal stage transition {proposal.from_stage} -> {proposal.to_stage}",
                context={"transition_id": proposal.transition_id},
            )

    def _compute_effects(self, proposal: LifeTransitionProposal, character: PlayerCharacter) -> AgingEffect:
        deltas: dict[str, int] = {}
        base = STAGE_GROWTH.get(proposal.from_stage, {})
        for attr, growth in base.items():
            deltas[attr] = growth
        for tag in proposal.focus_tags:
            bonus_attr = FOCUS_ATTRIBUTE_BONUS.get(tag)
            if bonus_attr:
                deltas[bonus_attr] = deltas.get(bonus_attr, 0) + 2
        # age-based declines late in life
        new_years = days_to_years(character.chronological_age_days + proposal.time_span_days)
        if new_years >= 55:
            deltas["body"] = deltas.get("body", 0) - 2
            deltas["agility"] = deltas.get("agility", 0) - 2
        # clamp attributes to 1..100
        for attr in list(deltas):
            current = character.attributes.get(attr, 25)
            deltas[attr] = max(-current + 1, min(100 - current, deltas[attr]))

        skill_progress: dict[str, int] = {}
        for tag in proposal.focus_tags:
            if tag in {"labor", "scholarship", "faith", "social", "hunting", "martial"}:
                skill_progress[tag] = skill_progress.get(tag, 0) + 10

        summary = f"经历 {proposal.time_span_days} 天，从 {proposal.from_stage} 成长为 {proposal.to_stage}。"
        return AgingEffect(
            attribute_deltas=deltas,
            skill_progress=skill_progress,
            health_note="自然衰老，" if new_years >= 55 else None,
            summary=summary,
        )


__all__ = [
    "STAGE_AGE_RANGES",
    "stage_for_age",
    "is_valid_stage_transition",
    "days_to_years",
    "age_to_days",
    "LifeTransitionProposal",
    "LifeTransitionService",
    "TransitionPreview",
]