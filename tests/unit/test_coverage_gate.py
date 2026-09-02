"""D-04: lore coverage gate seven-verdict behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.content.schemas import LoreRequirement, LoreRequirementSet
from noosphere40k.lore.coverage_gate import CoverageGate, CoverageVerdict
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreFact
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


@pytest.fixture
def gate(tmp_path: Path) -> CoverageGate:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    repo = LoreRepository(engine)
    repo.store_fact(LoreFact(
        fact_id="fact.approved.001",
        claim="帝国行政体系庞大",
        fact_type="canon_editorial",
        review_status="approved",
        pack_id="primer.galaxy.core",
        pack_version="1.0.0",
        valid_time=["era_indomitus_bounded"],
    ))
    repo.store_fact(LoreFact(
        fact_id="fact.disputed.001",
        claim="有争议事实",
        fact_type="disputed",
        confidence="disputed",
        review_status="approved",
        pack_id="primer.galaxy.core",
        pack_version="1.0.0",
        valid_time=["era_indomitus_bounded"],
    ))
    return CoverageGate(repo)


def _req(fact_id: str | None, *, hard: bool = False) -> LoreRequirement:
    return LoreRequirement(requirement_id="r1", fact_id=fact_id, hard=hard)


def test_allow_canon_when_approved_fact(gate: CoverageGate) -> None:
    decision = gate.resolve(LoreRequirementSet(hard=[_req("fact.approved.001", hard=True)]))
    assert decision.verdict == CoverageVerdict.ALLOW_CANON
    assert "fact.approved.001" in decision.allowed_fact_ids


def test_block_uncovered_for_missing_fact(gate: CoverageGate) -> None:
    decision = gate.resolve(LoreRequirementSet(hard=[_req("fact.nope.001", hard=True)]))
    assert decision.verdict == CoverageVerdict.BLOCK_UNCOVERED
    assert decision.hard_blocked is True


def test_block_conflict_for_disputed(gate: CoverageGate) -> None:
    decision = gate.resolve(LoreRequirementSet(hard=[_req("fact.disputed.001", hard=True)]))
    assert decision.verdict == CoverageVerdict.BLOCK_UNCOVERED
    assert decision.hard_blocked is True


def test_allow_decorative_when_no_hard_requirements(gate: CoverageGate) -> None:
    decision = gate.resolve(LoreRequirementSet(hard=[], optional=[]))
    assert decision.verdict == CoverageVerdict.ALLOW_DECORATIVE


def test_era_mismatch_blocks(gate: CoverageGate) -> None:
    decision = gate.resolve(
        LoreRequirementSet(hard=[_req("fact.approved.001", hard=True)]),
        era_ids=["era_30k"],
    )
    assert decision.verdict == CoverageVerdict.BLOCK_UNCOVERED


def test_optional_gap_allows_decorative(gate: CoverageGate) -> None:
    decision = gate.resolve(
        LoreRequirementSet(optional=[_req("fact.missing.optional")])
    )
    assert decision.verdict in (CoverageVerdict.ALLOW_DECORATIVE, CoverageVerdict.ALLOW_CANON)