"""D-05: character knowledge filtering."""

from __future__ import annotations

from noosphere40k.domain.models import KnowledgeRecord
from noosphere40k.lore.knowledge_filter import (
    character_knows_entity,
    encyclopedia_unlock_does_not_change_knowledge,
    filter_facts_for_character,
)
from noosphere40k.lore.schemas import LoreFact


def _fact(fact_id: str, entities=None) -> LoreFact:
    return LoreFact(
        fact_id=fact_id,
        claim="x",
        fact_type="canon_editorial",
        entity_ids=entities or [],
        review_status="approved",
        pack_id="p",
        pack_version="1.0.0",
    )


def test_knows_entity_threshold() -> None:
    records = {
        "pc:ent.1": KnowledgeRecord(owner_character_id="pc", subject_id="ent.1", status="knows"),
        "pc:ent.2": KnowledgeRecord(owner_character_id="pc", subject_id="ent.2", status="heard_rumor"),
    }
    assert character_knows_entity("pc", "ent.1", records) is True
    assert character_knows_entity("pc", "ent.2", records) is False


def test_filter_only_known_entity_facts() -> None:
    records = {
        "pc:ent.1": KnowledgeRecord(owner_character_id="pc", subject_id="ent.1", status="knows"),
    }
    facts = [_fact("f.known", entities=["ent.1"]), _fact("f.unknown", entities=["ent.9"])]
    allowed = filter_facts_for_character("pc", facts, records)
    assert [f.fact_id for f in allowed] == ["f.known"]


def test_direct_knowledge_of_fact_wins() -> None:
    records = {
        "pc:f.1": KnowledgeRecord(owner_character_id="pc", subject_id="f.1", status="believes"),
    }
    facts = [_fact("f.1", entities=["ent.99"])]
    allowed = filter_facts_for_character("pc", facts, records)
    assert [f.fact_id for f in allowed] == ["f.1"]


def test_encyclopedia_unlock_never_changes_knowledge() -> None:
    records = {
        "pc:ent.1": KnowledgeRecord(owner_character_id="pc", subject_id="ent.1", status="unknown"),
    }
    after = encyclopedia_unlock_does_not_change_knowledge(records, "term.mechanicus")
    assert after == records
    assert records["pc:ent.1"].status == "unknown"