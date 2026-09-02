"""Lore Coverage Gate (LORE_CONTENT_SPEC §7; D-04).

Seven verdicts:
    ALLOW_CANON, ALLOW_PERSPECTIVE, ALLOW_ORIGINAL, ALLOW_DECORATIVE,
    RETRY_CONSTRAINED, BLOCK_UNCOVERED, BLOCK_CONFLICT

A hard requirement that cannot be satisfied blocks the branch BEFORE any
narrator call. Optional gaps fall back to approved templates only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from noosphere40k.content.schemas import LoreRequirement, LoreRequirementSet
from noosphere40k.lore.retrieval import LoreRepository


class CoverageVerdict(StrEnum):
    ALLOW_CANON = "allow_canon"
    ALLOW_PERSPECTIVE = "allow_perspective"
    ALLOW_ORIGINAL = "allow_original"
    ALLOW_DECORATIVE = "allow_decorative"
    RETRY_CONSTRAINED = "retry_constrained"
    BLOCK_UNCOVERED = "block_uncovered"
    BLOCK_CONFLICT = "block_conflict"


@dataclass
class CoverageDecision:
    verdict: CoverageVerdict
    requirement_id: str = ""
    reason: str = ""
    allowed_fact_ids: list[str] = field(default_factory=list)
    allowed_original_ids: list[str] = field(default_factory=list)
    forbidden_topics: set[str] = field(default_factory=set)
    hard_blocked: bool = False


class CoverageGate:
    def __init__(self, lore: LoreRepository) -> None:
        self.lore = lore

    def resolve(self, requirements: LoreRequirementSet, *, era_ids: list[str] | None = None) -> CoverageDecision:
        """Resolve a scene's lore requirements against the approved repository."""
        allowed_facts: list[str] = []
        forbidden = set(requirements.forbidden_topics)

        for req in requirements.hard:
            decision = self._resolve_requirement(req, era_ids=era_ids)
            if decision.verdict != CoverageVerdict.ALLOW_CANON:
                if req.fact_id:
                    return CoverageDecision(
                        verdict=CoverageVerdict.BLOCK_UNCOVERED,
                        requirement_id=req.requirement_id,
                        reason=f"hard lore requirement not satisfiable: {req.fact_id}",
                        forbidden_topics=forbidden,
                        hard_blocked=True,
                    )
                return CoverageDecision(
                    verdict=CoverageVerdict.BLOCK_UNCOVERED,
                    requirement_id=req.requirement_id,
                    reason="hard lore requirement has no approved fact",
                    forbidden_topics=forbidden,
                    hard_blocked=True,
                )
            if req.fact_id:
                allowed_facts.append(req.fact_id)

        for req in requirements.optional:
            decision = self._resolve_requirement(req, era_ids=era_ids)
            if decision.verdict == CoverageVerdict.ALLOW_CANON and req.fact_id:
                allowed_facts.append(req.fact_id)

        if allowed_facts:
            return CoverageDecision(
                verdict=CoverageVerdict.ALLOW_CANON,
                allowed_fact_ids=allowed_facts,
                forbidden_topics=forbidden,
            )
        return CoverageDecision(
            verdict=CoverageVerdict.ALLOW_DECORATIVE,
            forbidden_topics=forbidden,
        )

    def _resolve_requirement(self, req: LoreRequirement, *, era_ids: list[str] | None) -> CoverageDecision:
        if req.fact_id is None:
            return CoverageDecision(
                verdict=CoverageVerdict.BLOCK_UNCOVERED,
                requirement_id=req.requirement_id,
                reason="requirement has no fact_id",
            )
        fact = self.lore.get_fact(req.fact_id)
        if fact is None:
            return CoverageDecision(
                verdict=CoverageVerdict.BLOCK_UNCOVERED,
                requirement_id=req.requirement_id,
                reason=f"fact not approved/absent: {req.fact_id}",
            )
        if fact.confidence.value == "disputed":
            return CoverageDecision(
                verdict=CoverageVerdict.BLOCK_CONFLICT,
                requirement_id=req.requirement_id,
                reason=f"fact is disputed: {req.fact_id}",
            )
        if era_ids and fact.valid_time:
            overlapping = any(era in fact.valid_time for era in era_ids)
            if not overlapping:
                return CoverageDecision(
                    verdict=CoverageVerdict.BLOCK_CONFLICT,
                    requirement_id=req.requirement_id,
                    reason=f"fact valid time does not overlap scene era: {req.fact_id}",
                )
        return CoverageDecision(
            verdict=CoverageVerdict.ALLOW_CANON,
            requirement_id=req.requirement_id,
            reason="approved fact available",
            allowed_fact_ids=[req.fact_id],
        )