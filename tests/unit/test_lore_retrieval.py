"""D-03: lore repository, FTS5 search, approved-only reads."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreEntity, LoreFact, SourceRecord
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


@pytest.fixture
def repo(tmp_path: Path) -> LoreRepository:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    return LoreRepository(engine)


def _fact(fact_id: str, claim: str, *, status: str = "approved", entity_ids=None) -> LoreFact:
    return LoreFact(
        fact_id=fact_id,
        claim=claim,
        fact_type="canon_editorial",
        entity_ids=entity_ids or [],
        review_status=status,
        pack_id="primer.galaxy.core",
        pack_version="1.0.0",
    )


def test_approved_fact_retrievable(repo: LoreRepository) -> None:
    repo.store_fact(_fact("fact.imperium.001", "帝国由帝皇统治"))
    fact = repo.get_fact("fact.imperium.001")
    assert fact is not None
    assert "帝皇" in fact.claim


def test_candidate_fact_not_retrievable(repo: LoreRepository) -> None:
    repo.store_fact(_fact("fact.candidate.001", "候选内容", status="candidate"))
    assert repo.get_fact("fact.candidate.001") is None


def test_search_returns_only_approved(repo: LoreRepository) -> None:
    repo.store_fact(_fact("fact.ok.001", "阿斯塔特是帝国战士"))
    repo.store_fact(_fact("fact.no.001", "阿斯塔特是机器", status="candidate"))
    results = repo.search("阿斯塔特")
    ids = {f.fact_id for f in results}
    assert "fact.ok.001" in ids
    assert "fact.no.001" not in ids


def test_store_source_and_get(repo: LoreRepository) -> None:
    source = SourceRecord(
        source_id="GW-01",
        title="The Setting",
        publisher="GW",
        source_class="A1",
        locator="p.1",
        access_type="public_web",
        rights_profile="redistributable_metadata_only",
        review_status="approved",
    )
    repo.store_source(source)
    loaded = repo.get_source("GW-01")
    assert loaded is not None
    assert loaded.publisher == "GW"


def test_entity_with_alias(repo: LoreRepository) -> None:
    entity = LoreEntity(
        entity_id="entity.adeptus_mechanicus",
        canonical_name="Adeptus Mechanicus",
        entity_type="org",
        aliases=[{"language": "zh-CN", "text": "机械教", "alias_type": "common"}],
        origin="canon",
        review_status="approved",
    )
    repo.store_entity(entity)
    loaded = repo.get_entity("entity.adeptus_mechanicus")
    assert loaded is not None
    assert loaded.aliases[0].text == "机械教"


def test_search_by_alias_fallback(repo: LoreRepository) -> None:
    entity = LoreEntity(
        entity_id="entity.adeptus_mechanicus",
        canonical_name="Adeptus Mechanicus",
        entity_type="org",
        aliases=[{"language": "zh-CN", "text": "机械教", "alias_type": "common"}],
        origin="canon",
        review_status="approved",
    )
    repo.store_entity(entity)
    repo.store_fact(_fact(
        "fact.mech.001", "机械教维护技术",
        entity_ids=["entity.adeptus_mechanicus"],
    ))
    results = repo.search_by_alias("机械教")
    assert any(f.fact_id == "fact.mech.001" for f in results)


def test_empty_search_returns_nothing(repo: LoreRepository) -> None:
    assert repo.search("") == []