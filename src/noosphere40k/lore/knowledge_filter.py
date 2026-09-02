"""Character knowledge filtering (LORE_CONTENT_SPEC §6; D-05).

Separates what the PLAYER may read in the encyclopedia from what the
CHARACTER knows in-world. Encyclopedia unlocks never change character
knowledge; character knowledge never unlocks encyclopedia content.
"""

from __future__ import annotations

from noosphere40k.domain.models import KnowledgeRecord
from noosphere40k.lore.schemas import LoreFact

# Character knowledge statuses, strongest first.
KNOWLEDGE_STRENGTH = {
    "knows": 4,
    "believes": 3,
    "doubts": 2,
    "heard_rumor": 1,
    "unknown": 0,
}


def character_knows_entity(character_id: str, subject_id: str, records: dict[str, KnowledgeRecord]) -> bool:
    key = f"{character_id}:{subject_id}"
    record = records.get(key)
    if record is None:
        return False
    return KNOWLEDGE_STRENGTH.get(record.status, 0) >= 2  # believes or knows


def filter_facts_for_character(
    character_id: str,
    facts: list[LoreFact],
    records: dict[str, KnowledgeRecord],
    *,
    knowledge_threshold: int = 2,
) -> list[LoreFact]:
    """Return only facts the character believes/knows (threshold 2+) or that
    reference entities the character knows about."""
    allowed: list[LoreFact] = []
    for fact in facts:
        # A fact is character-visible if its status is high enough,
        # or if all its entities are known to the character.
        subject_status = KNOWLEDGE_STRENGTH.get(
            records.get(f"{character_id}:{fact.fact_id}", KnowledgeRecord(
                owner_character_id=character_id, subject_id=fact.fact_id, status="unknown"
            )).status, 0,
        )
        if subject_status >= knowledge_threshold:
            allowed.append(fact)
            continue
        entities_known = all(
            character_knows_entity(character_id, eid, records) for eid in fact.entity_ids
        )
        if entities_known:
            allowed.append(fact)
    return allowed


def encyclopedia_unlock_does_not_change_knowledge(
    records: dict[str, KnowledgeRecord],
    unlock_subject: str,
) -> dict[str, KnowledgeRecord]:
    """Encyclopedia unlocks are player-layer only; return records unchanged."""
    return records