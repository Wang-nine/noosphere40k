"""G-03/G-04: encyclopedia/knowledge/sources layers and roll details."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.application.encyclopedia_service import EncyclopediaService
from noosphere40k.domain.errors import LoreUncoveredError
from noosphere40k.domain.models import KnowledgeRecord
from noosphere40k.lore.retrieval import LoreRepository
from noosphere40k.lore.schemas import LoreFact, SourceRecord
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


@pytest.fixture
def service(tmp_path: Path) -> EncyclopediaService:
    engine = open_engine(tmp_path / "lore.db")
    run_migrations(engine, MIGRATIONS)
    repo = LoreRepository(engine)
    repo.store_source(SourceRecord(
        source_id="GW-WEB-001",
        title="The Setting",
        publisher="Games Workshop",
        source_class="A1",
        locator="p.3",
        access_type="public_web",
        rights_profile="redistributable_metadata_only",
        review_status="approved",
    ))
    # store glossary directly via SQL for this test
    with engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(text(
            "INSERT INTO glossary_entries (term_id, english_name, standard_zh_cn, "
            "child_explanation, beginner_explanation, deep_explanation, source_refs_json) "
            "VALUES ('term.mechanicus', 'Adeptus Mechanicus', '机械教', "
            "'红袍人负责机器。', '机械教是维护技术的帝国机构。', '深层说明。', '[\"GW-WEB-001\"]')"
        ))
    repo.store_fact(LoreFact(
        fact_id="fact.mech.001",
        claim="机械教维护技术",
        fact_type="canon_editorial",
        source_refs=["GW-WEB-001"],
        review_status="approved",
        pack_id="p",
        pack_version="1.0.0",
    ))
    repo.store_knowledge(KnowledgeRecord(
        owner_character_id="pc", subject_id="term.mechanicus", status="heard_rumor"
    ))
    return EncyclopediaService(repo)


def test_encyclopedia_term_player_layer(service: EncyclopediaService) -> None:
    text = service.encyclopedia_term("term.mechanicus")
    assert "机械教是维护技术的帝国机构" in text
    assert "来源：GW-WEB-001" in text


def test_encyclopedia_unknown_term(service: EncyclopediaService) -> None:
    with pytest.raises(LoreUncoveredError):
        service.encyclopedia_term("term.nope")


def test_character_knowledge_distinct_from_encyclopedia(service: EncyclopediaService) -> None:
    result = service.character_knowledge("pc", "term.mechanicus")
    assert "听过传言" in result
    assert "维护技术" not in result  # character only knows rumor, not the full fact


def test_sources_for_fact(service: EncyclopediaService) -> None:
    text = service.sources_for("fact.mech.001")
    assert "The Setting" in text
    assert "Games Workshop" in text
    assert "p.3" in text


def test_sources_unknown_fact(service: EncyclopediaService) -> None:
    with pytest.raises(LoreUncoveredError):
        service.sources_for("fact.nope")