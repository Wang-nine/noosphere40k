"""D-09/D-10: coverage reporting and hard-requirement satisfaction."""

from __future__ import annotations

from pathlib import Path

from noosphere40k.lore.coverage_report import (
    GALAXY_PRIMER_DOMAINS,
    build_campaign_coverage,
    build_primer_report,
    hard_requirement_satisfaction_rate,
)
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreFact
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


def _mk_repo(tmp_path: Path) -> LoreRepository:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    return LoreRepository(engine)


def test_primer_report_lists_twelve_domains(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    repo.store_fact(LoreFact(
        fact_id="fact.gp01.001",
        claim="帝国很庞大",
        fact_type="canon_editorial",
        entity_ids=["GP-01"],
        review_status="approved",
        pack_id="primer.galaxy.core",
        pack_version="1.0.0",
    ))
    report = build_primer_report(repo.engine, pack_id="primer.galaxy.core")
    assert len(report.domains) == 12
    assert report.approved_facts_total >= 1
    assert len(report.missing_domains) == 11  # only GP-01 covered
    assert "GP-01" in [d.domain_id for d in report.domains]


def test_hard_requirement_satisfaction_zero_when_missing(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    repo.store_fact(LoreFact(
        fact_id="fact.approved.1",
        claim="x",
        fact_type="canon_editorial",
        review_status="candidate",
        pack_id="campaign.imperium_lifepath_frontier",
        pack_version="1.0.0",
    ))
    rate = hard_requirement_satisfaction_rate(
        repo.engine,
        {"req1": ["fact.approved.1"]},
    )
    assert rate == 0.0  # candidate does not satisfy hard requirement


def test_hard_requirement_satisfaction_full_when_approved(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    repo.store_fact(LoreFact(
        fact_id="fact.approved.1",
        claim="x",
        fact_type="canon_editorial",
        review_status="approved",
        pack_id="campaign.imperium_lifepath_frontier",
        pack_version="1.0.0",
    ))
    rate = hard_requirement_satisfaction_rate(
        repo.engine,
        {"req1": ["fact.approved.1"], "req2": ["fact.approved.1"]},
    )
    assert rate == 1.0


def test_campaign_coverage_reports_missing(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    report = build_campaign_coverage(
        repo.engine,
        pack_id="campaign.imperium_lifepath_frontier",
        hard_requirements={"req1": ["fact.nope"]},
    )
    assert "req1" in report.missing_domains


def test_domain_coverage_rate() -> None:
    from noosphere40k.lore.coverage_report import DomainCoverage

    domain = DomainCoverage(domain_id="GP-01", total_facts=10, approved_facts=10, covered=True)
    assert domain.rate == 1.0
    empty = DomainCoverage(domain_id="GP-02", total_facts=0, approved_facts=0, covered=False)
    assert empty.rate == 0.0


def test_primer_domains_stable() -> None:
    assert len(GALAXY_PRIMER_DOMAINS) == 12
    assert GALAXY_PRIMER_DOMAINS[0] == "GP-01 world_basics"