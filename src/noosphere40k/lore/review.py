"""Human review workflow (LORE_CONTENT_SPEC §3, §9; D-08).

Candidates can never become ``approved`` by themselves. A review action with
an explicit reviewer identity and timestamp is required. Every transition is
audited. Rejection and supersede are also recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from noosphere40k.domain.errors import LoreConflictError
from noosphere40k.lore.retrieval import LoreRepository

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "candidate": {"approved", "rejected", "superseded"},
    "approved": {"superseded", "rejected"},
    "rejected": {"candidate"},
    "superseded": {"rejected"},
}


@dataclass(frozen=True)
class ReviewDecision:
    action: str  # approve | reject | supersede | reopen
    reviewer: str
    reviewed_at: str


class ReviewService:
    def __init__(self, repo: LoreRepository) -> None:
        self.repo = repo
        self._audit: list[ReviewDecision] = []

    def audit_trail(self) -> list[ReviewDecision]:
        return list(self._audit)

    def review_source(self, source_id: str, *, approve: bool, reviewer: str) -> ReviewDecision:
        source = self.repo.get_source_any(source_id)
        if source is None:
            raise LoreConflictError(f"source not found: {source_id}")
        self._transition(source.review_status.value, "approved" if approve else "rejected")
        new_status = "approved" if approve else "rejected"
        self.repo.update_source_review(source_id, new_status, reviewer)
        return self._record(approve, reviewer)

    def review_fact(self, fact_id: str, *, approve: bool, reviewer: str) -> ReviewDecision:
        fact = self.repo.get_fact_any(fact_id)
        if fact is None:
            raise LoreConflictError(f"fact not found: {fact_id}")
        self._transition(fact.review_status.value, "approved" if approve else "rejected")
        new_status = "approved" if approve else "rejected"
        self.repo.update_fact_review(fact_id, new_status, reviewer)
        return self._record(approve, reviewer)

    def review_entity(self, entity_id: str, *, approve: bool, reviewer: str) -> ReviewDecision:
        entity = self.repo.get_entity_any(entity_id)
        if entity is None:
            raise LoreConflictError(f"entity not found: {entity_id}")
        self._transition(entity.review_status.value, "approved" if approve else "rejected")
        new_status = "approved" if approve else "rejected"
        self.repo.update_entity_review(entity_id, new_status, reviewer)
        return self._record(approve, reviewer)

    # ---- transition rules ----

    def _transition(self, current: str, target: str) -> None:
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise LoreConflictError(
                f"illegal review transition {current} -> {target}",
                context={"from": current, "to": target},
            )

    def _record(self, approve: bool, reviewer: str) -> ReviewDecision:
        decision = ReviewDecision(
            action="approve" if approve else "reject",
            reviewer=reviewer,
            reviewed_at=datetime.now(UTC).isoformat(),
        )
        self._audit.append(decision)
        return decision


__all__ = ["ReviewService", "ReviewDecision", "ALLOWED_TRANSITIONS"]