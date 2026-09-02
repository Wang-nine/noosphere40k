"""Source importer framework (D-07).

Importers propose candidate SourceRecord / LoreFact / LoreEntity entries from
sanitized text. Candidates are ALWAYS created as ``review_status=candidate``;
nothing is auto-approved here. Injection-warning documents are rejected
upfront.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from noosphere40k.lore.importers.cleaner import sanitize_plain_text
from noosphere40k.lore.schemas import LoreEntity, LoreFact, SourceRecord


@dataclass
class CandidateBatch:
    sources: list[SourceRecord] = field(default_factory=list)
    facts: list[LoreFact] = field(default_factory=list)
    entities: list[LoreEntity] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)


class SourceImporter(Protocol):
    """Importers sanitize input, propose candidates, and never auto-approve."""

    def ingest(self, raw_text: str) -> CandidateBatch: ...


class PlainTextImporter:
    """Reference importer: split sanitized text into candidate facts."""

    def __init__(
        self,
        *,
        pack_id: str,
        pack_version: str,
        source_id: str,
        source_title: str,
        publisher: str,
        source_class: str = "B",
        access_type: str = "public_web",
        rights_profile: str = "redistributable_metadata_only",
        reviewer: str | None = None,
    ) -> None:
        self.pack_id = pack_id
        self.pack_version = pack_version
        self.source_id = source_id
        self.source_title = source_title
        self.publisher = publisher
        self.source_class = source_class
        self.access_type = access_type
        self.rights_profile = rights_profile
        self.reviewer = reviewer

    def ingest(self, raw_text: str) -> CandidateBatch:
        doc = sanitize_plain_text(raw_text)
        if doc.injection_warnings:
            return CandidateBatch(rejected_reasons=doc.injection_warnings)

        batch = CandidateBatch()
        batch.sources.append(
            SourceRecord(
                source_id=self.source_id,
                title=self.source_title,
                publisher=self.publisher,
                source_class=self.source_class,
                locator="imported",
                access_type=self.access_type,
                rights_profile=self.rights_profile,
                review_status="candidate",
            )
        )
        for index, claim in enumerate(self._split_sentences(doc.text), start=1):
            batch.facts.append(
                LoreFact(
                    fact_id=f"{self.pack_id}.candidate.{index:04d}",
                    claim=claim,
                    fact_type="canon_editorial",
                    source_refs=[self.source_id],
                    review_status="candidate",
                    pack_id=self.pack_id,
                    pack_version=self.pack_version,
                )
            )
        return batch

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts: list[str] = []
        for chunk in text.split("。"):
            chunk = chunk.strip()
            if chunk and len(chunk) >= 4:
                parts.append(chunk)
        return parts


__all__ = ["CandidateBatch", "PlainTextImporter", "SourceImporter"]