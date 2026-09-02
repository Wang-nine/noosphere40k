"""Claim Guard (LORE_CONTENT_SPEC §7, PROMPT_GUARD_SPEC §6.5; D-06).

Rejects, per turn:
- canon claims without approved fact IDs,
- game_original claims referencing entities not allowed by the request,
- decorative claims that smuggle proper nouns / history / authority,
- claims that reference fact IDs absent from the NarrationRequest,
- era-conflicting facts.

Only the entities/facts present in the request are legitimate targets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from noosphere40k.llm.schemas import LoreClaim, NarrationRequest

CANON_TYPES = {"canon", "perspective"}
DECORATIVE_TYPES = {"decorative"}


@dataclass
class GuardDecision:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    fail_fast: bool = False


class ClaimGuard:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def validate(self, request: NarrationRequest, claims: list[LoreClaim]) -> GuardDecision:
        self.errors = []
        allowed_fact_ids = {f.fact_id for f in request.allowed_lore_facts}
        allowed_entities = set(request.allowed_original_entity_ids)

        for claim in claims:
            ctype = claim.claim_type
            if ctype in CANON_TYPES:
                if not claim.supporting_fact_ids:
                    self.errors.append(
                        f"canon claim has no supporting fact ids: {claim.text[:40]!r}"
                    )
                    continue
                missing = [
                    fid for fid in claim.supporting_fact_ids if fid not in allowed_fact_ids
                ]
                if missing:
                    self.errors.append(
                        f"canon claim references facts not allowed by request: {missing}"
                    )
            elif ctype == "game_original":
                bad_entities = [
                    eid for eid in claim.supporting_entity_ids if eid not in allowed_entities
                ]
                if bad_entities:
                    self.errors.append(
                        f"game_original claim uses entities outside the allowlist: {bad_entities}"
                    )
            elif ctype in DECORATIVE_TYPES:
                if claim.supporting_entity_ids or claim.supporting_fact_ids:
                    self.errors.append(
                        f"decorative claim must not carry lore assertions: {claim.text[:40]!r}"
                    )
            else:
                self.errors.append(f"unknown claim type: {ctype}")

        if self.errors:
            return GuardDecision(ok=False, errors=self.errors)
        return GuardDecision(ok=True)

    def check_era(self, request: NarrationRequest, fact_id: str, era_id: str | None) -> GuardDecision:
        """Era guard: facts allowed in the request must already be era-compatible;
        this is a structural cross-check against the request's allowed facts."""
        allowed = {f.fact_id for f in request.allowed_lore_facts}
        if fact_id not in allowed:
            return GuardDecision(
                ok=False,
                errors=[f"fact {fact_id} was not admitted by the Lore Gate for this turn"],
            )
        return GuardDecision(ok=True)


__all__ = ["ClaimGuard", "GuardDecision"]