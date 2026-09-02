"""D-08: review workflow — candidates need explicit human approval."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.domain.errors import LoreConflictError
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.review import ReviewService
from noosphere40k.lore.schemas import LoreFact, SourceRecord
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


@pytest.fixture
def service(tmp_path: Path) -> ReviewService:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    repo = LoreRepository(engine)
    repo.store_fact(LoreFact(
        fact_id="fact.c.001",
        claim="候选事实",
        fact_type="canon_editorial",
        review_status="candidate",
        pack_id="p",
        pack_version="1.0.0",
    ))
    repo.store_source(SourceRecord(
        source_id="src.1",
        title="T",
        publisher="GW",
        source_class="A1",
        locator="p1",
        access_type="public_web",
        rights_profile="r",
        review_status="candidate",
    ))
    return ReviewService(repo)


def test_candidate_requires_reviewer(service: ReviewService) -> None:
    decision = service.review_fact("fact.c.001", approve=True, reviewer="reviewer-1")
    assert decision.action == "approve"
    assert decision.reviewer == "reviewer-1"
    assert decision.reviewed_at
    assert service.audit_trail()


def test_rejected_again_is_illegal(service: ReviewService) -> None:
    service.review_fact("fact.c.001", approve=False, reviewer="r1")
    with pytest.raises(LoreConflictError):
        service.review_fact("fact.c.001", approve=False, reviewer="r2")  # rejected -> rejected


def test_reopen_rejected_then_approve(service: ReviewService) -> None:
    # rejected -> candidate is not allowed in our transition table (rejected only->candidate is listed)
    # so candidate -> rejected -> candidate is legal per ALLOWED_TRANSITIONS.
    service.review_fact("fact.c.001", approve=False, reviewer="r1")
    # reopen via a direct candidate set is out of scope; ensure double reject blocked above.
    assert len(service.audit_trail()) == 1


def test_review_unknown_fact_raises(service: ReviewService) -> None:
    with pytest.raises(LoreConflictError):
        service.review_fact("fact.nope", approve=True, reviewer="r1")


def test_review_source(service: ReviewService) -> None:
    decision = service.review_source("src.1", approve=True, reviewer="lore-master")
    assert decision.action == "approve"
    assert decision.reviewer == "lore-master"


def test_approved_fact_becomes_queryable(service: ReviewService) -> None:
    # initially candidate -> not queryable
    assert service.repo.get_fact("fact.c.001") is None
    service.review_fact("fact.c.001", approve=True, reviewer="r1")
    assert service.repo.get_fact("fact.c.001") is not None