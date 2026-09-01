"""Lore schemas (DATA_PROTOCOL_SPEC §6; D-01).

Source, fact, entity, glossary and knowledge contract models.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from noosphere40k.domain.enums import (
    ConfidenceLevel,
    EntityOrigin,
    ReviewStatus,
    SourceClass,
    SourceViewpoint,
)
from noosphere40k.domain.models import KnowledgeRecord, LocalizedAlias, StrictModel


class SourceRecord(StrictModel):
    source_id: str
    title: str
    publisher: str
    source_class: SourceClass
    edition: str | None = None
    publication_date: date | None = None
    language: str = "en"
    locator: str
    access_type: str
    canon_scope: list[str] = Field(default_factory=list)
    viewpoint: SourceViewpoint = SourceViewpoint.EDITORIAL
    rights_profile: str
    review_status: ReviewStatus = ReviewStatus.CANDIDATE
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class LoreFact(StrictModel):
    fact_id: str
    claim: str
    fact_type: str
    entity_ids: list[str] = Field(default_factory=list)
    relation_ids: list[str] = Field(default_factory=list)
    valid_time: list[str] = Field(default_factory=list)
    valid_regions: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.CONFIRMED
    conflicts_with: list[str] = Field(default_factory=list)
    spoiler_level: int = 0
    review_status: ReviewStatus = ReviewStatus.CANDIDATE
    pack_id: str
    pack_version: str


class LoreEntity(StrictModel):
    entity_id: str
    canonical_name: str
    entity_type: str
    aliases: list[LocalizedAlias] = Field(default_factory=list)
    parent_entity_ids: list[str] = Field(default_factory=list)
    origin: EntityOrigin = EntityOrigin.GAME_ORIGINAL
    valid_time: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.CANDIDATE


class GlossaryEntry(StrictModel):
    term_id: str
    entity_id: str | None = None
    english_name: str
    standard_zh_cn: str
    aliases_zh_cn: list[str] = Field(default_factory=list)
    deprecated_translations: list[str] = Field(default_factory=list)
    child_explanation: str
    beginner_explanation: str
    deep_explanation: str
    viewpoint_warning: str | None = None
    spoiler_level: int = 0
    source_refs: list[str] = Field(default_factory=list)


class EncyclopediaUnlock(StrictModel):
    owner_character_id: str
    term_id: str
    visibility: str
    unlocked_at_event_id: str
    source_viewpoint: str | None = None


__all__ = [
    "SourceRecord",
    "LoreFact",
    "LoreEntity",
    "GlossaryEntry",
    "EncyclopediaUnlock",
    "KnowledgeRecord",
    "LocalizedAlias",
]