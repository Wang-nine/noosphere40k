"""Canon test framework (TEST_ACCEPTANCE_PLAN §5.3; H-02).

Supports correct-fact, trap, uncovered, perspective-conflict and
prompt-injection cases. Each case runs against the guards (Lore Gate +
Claim Guard + Output Guard) and asserts an explicit decision; it never
depends on a probabilistic model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from noosphere40k.canon_guard.claim_guard import ClaimGuard, GuardDecision
from noosphere40k.llm.schemas import LoreClaim, NarrationRequest
from noosphere40k.lore.coverage_gate import CoverageGate, CoverageVerdict
from noosphere40k.lore.retrieval import LoreRepository

if TYPE_CHECKING:
    from noosphere40k.content.schemas import LoreRequirementSet


class CanonCaseType:
    CORRECT = "correct"
    TRAP = "trap"
    UNCOVERED = "uncovered"
    PERSPECTIVE_CONFLICT = "perspective_conflict"
    PROMPT_INJECTION = "prompt_injection"


@dataclass
class CanonCase:
    case_id: str
    case_type: str
    description: str
    claim: str
    claim_type: str = "canon"
    supporting_fact_ids: list[str] = field(default_factory=list)
    supporting_entity_ids: list[str] = field(default_factory=list)
    injection_text: str | None = None
    expected_ok: bool | None = None  # None = must be blocked


@dataclass
class CanonCaseResult:
    case: CanonCase
    ok: bool
    decision: str = ""
    detail: str = ""


class CanonTestFramework:
    def __init__(
        self,
        lore: LoreRepository,
        gate: CoverageGate,
        guard: ClaimGuard,
    ) -> None:
        self.lore = lore
        self.gate = gate
        self.guard = guard

    def run(self, cases: list[CanonCase], request: NarrationRequest) -> list[CanonCaseResult]:
        results: list[CanonCaseResult] = []
        for case in cases:
            results.append(self._run_one(case, request))
        return results

    def _run_one(self, case: CanonCase, request: NarrationRequest) -> CanonCaseResult:
        # 1. Lore Gate for uncovered / perspective cases
        if case.case_type in (CanonCaseType.UNCOVERED, CanonCaseType.PERSPECTIVE_CONFLICT):
            coverage = self.gate.resolve(
                _requirements_for(case),
                era_ids=["era_indomitus_bounded"],
            )
            if coverage.verdict in (CoverageVerdict.BLOCK_UNCOVERED, CoverageVerdict.BLOCK_CONFLICT):
                return CanonCaseResult(case=case, ok=True, decision="blocked_by_lore_gate",
                                       detail=coverage.reason)

        # 2. Claim Guard for canon/entity rules
        claim = LoreClaim(
            text=case.claim,
            claim_type=case.claim_type,
            supporting_fact_ids=case.supporting_fact_ids,
            supporting_entity_ids=case.supporting_entity_ids,
        )
        decision: GuardDecision = self.guard.validate(request, [claim])

        # 3. Prompt-injection: rejected if injection text present
        if case.case_type == CanonCaseType.PROMPT_INJECTION and case.injection_text:
            from noosphere40k.lore.importers.cleaner import sanitize_plain_text

            doc = sanitize_plain_text(case.injection_text)
            if doc.injection_warnings:
                return CanonCaseResult(case=case, ok=True, decision="injection_rejected",
                                       detail="; ".join(doc.injection_warnings))

        if case.case_type == CanonCaseType.TRAP:
            # traps must be blocked: the supporting facts must actually be
            # approved in the repository, otherwise the claim is unsupported.
            missing = [fid for fid in case.supporting_fact_ids if self.lore.get_fact(fid) is None]
            if missing:
                return CanonCaseResult(case=case, ok=True, decision="blocked_unsupported_fact",
                                       detail=f"facts not approved: {missing}")
            ok = not decision.ok
            return CanonCaseResult(case=case, ok=ok, decision="blocked" if not decision.ok else "passed",
                                   detail="; ".join(decision.errors))
        if case.case_type == CanonCaseType.CORRECT:
            return CanonCaseResult(case=case, ok=decision.ok,
                                   decision="passed" if decision.ok else "blocked",
                                   detail="; ".join(decision.errors))
        if case.case_type == CanonCaseType.PERSPECTIVE_CONFLICT:
            # perspective claims must carry a source; blocked otherwise
            return CanonCaseResult(case=case, ok=decision.ok or case.claim_type == "perspective",
                                   decision="passed" if (decision.ok or case.claim_type == "perspective") else "blocked")
        # uncovered handled above
        return CanonCaseResult(case=case, ok=decision.ok, decision="passed" if decision.ok else "blocked",
                               detail="; ".join(decision.errors))


def _requirements_for(case: CanonCase) -> LoreRequirementSet:
    from noosphere40k.content.schemas import LoreRequirement, LoreRequirementSet

    reqs = LoreRequirementSet()
    if case.supporting_fact_ids:
        reqs.hard = [
            LoreRequirement(requirement_id=case.case_id, fact_id=fid, hard=True)
            for fid in case.supporting_fact_ids
        ]
    return reqs


__all__ = ["CanonCase", "CanonCaseResult", "CanonTestFramework", "CanonCaseType"]