"""D-01: lore schema contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from noosphere40k.domain.models import KnowledgeRecord
from noosphere40k.lore.schemas import (
    EncyclopediaUnlock,
    GlossaryEntry,
    LoreEntity,
    LoreFact,
    SourceRecord,
)


def _source() -> SourceRecord:
    return SourceRecord(
        source_id="GW-COVER-SAMPLE-001",
        title="Sample: The Setting",
        publisher="Games Workshop",
        source_class="A1",
        locator="p. 12",
        access_type="public_web",
        rights_profile="redistributable_metadata_only",
        review_status="approved",
        reviewed_by="reviewer-1",
    )


def test_source_roundtrip() -> None:
    source = _source()
    dumped = source.model_dump(mode="json")
    assert dumped["source_class"] == "A1"
    assert dumped["viewpoint"] == "editorial"
    assert SourceRecord.model_validate(dumped) == source


def test_source_unknown_class_rejected() -> None:
    data = _source().model_dump(mode="json")
    data["source_class"] = "F1"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(data)


def test_fact_requires_pack_identity() -> None:
    fact = LoreFact(
        fact_id="fact.imperium.sample_001",
        claim="The Imperium is vast.",
        fact_type="canon_editorial",
        source_refs=["GW-COVER-SAMPLE-001"],
        confidence="confirmed",
        pack_id="primer.galaxy.core",
        pack_version="1.0.0",
    )
    assert fact.pack_version == "1.0.0"


def test_fact_missing_pack_id_rejected() -> None:
    with pytest.raises(ValidationError):
        LoreFact(
            fact_id="fact.x",
            claim="x",
            fact_type="canon_editorial",
            pack_version="1.0.0",
        )


def test_entity_roundtrip_aliases() -> None:
    entity = LoreEntity(
        entity_id="game_original.system_001",
        canonical_name="Sample System",
        entity_type="system",
        aliases=[{"language": "zh-CN", "text": "样例星系", "alias_type": "common"}],
        origin="game_original",
    )
    assert entity.model_dump(mode="json")["aliases"][0]["text"] == "样例星系"


def test_glossary_requires_three_explanations() -> None:
    entry = GlossaryEntry(
        term_id="term.adeptus_mechanicus",
        english_name="Adeptus Mechanicus",
        standard_zh_cn="机械教",
        child_explanation="红袍人负责机器。",
        beginner_explanation="机械教是维护技术的帝国机构。",
        deep_explanation="详细层级说明。",
        spoiler_level=1,
    )
    assert entry.beginner_explanation


def test_glossary_missing_child_explanation_rejected() -> None:
    with pytest.raises(ValidationError):
        GlossaryEntry(
            term_id="term.x",
            english_name="X",
            standard_zh_cn="x",
            beginner_explanation="x",
            deep_explanation="x",
        )


def test_knowledge_record_and_unlock_models() -> None:
    record = KnowledgeRecord(
        owner_character_id="character.pc.01",
        subject_id="fact.imperium.sample_001",
        status="knows",
    )
    unlock = EncyclopediaUnlock(
        owner_character_id="character.pc.01",
        term_id="term.adeptus_mechanicus",
        visibility="unlocked",
        unlocked_at_event_id="event001",
    )
    assert record.subject_id == "fact.imperium.sample_001"
    assert unlock.visibility == "unlocked"


def test_extra_fields_strictly_forbidden() -> None:
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(_source().model_dump(mode="json") | {"extra": 1})


def test_viewpoint_unknown_rejected() -> None:
    data = _source().model_dump(mode="json")
    data["viewpoint"] = "omniscient"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(data)