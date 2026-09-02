"""Lore repository with FTS5 search (D-03).

Query layer NEVER returns unapproved facts: every read path filters
``review_status = 'approved'`` at the SQL level, not in the caller.
Only approved facts are indexed into the FTS5 table.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text

from noosphere40k.domain.models import KnowledgeRecord
from noosphere40k.lore.schemas import (
    GlossaryEntry,
    LoreEntity,
    LoreFact,
    SourceRecord,
)


class LoreRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # ---- writes (pack import) ----

    def store_knowledge(self, record: KnowledgeRecord) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO knowledge_records "
                    "(owner_character_id, subject_id, status, reliability_basis_points, "
                    "learned_at_event_id, learned_from_character_id, source_viewpoint, "
                    "superseded_by_event_id) VALUES "
                    "(:o, :s, :st, :r, :l, :lf, :sv, :sup)"
                ),
                {
                    "o": record.owner_character_id,
                    "s": record.subject_id,
                    "st": record.status,
                    "r": record.reliability_basis_points,
                    "l": record.learned_at_event_id,
                    "lf": record.learned_from_character_id,
                    "sv": record.source_viewpoint,
                    "sup": record.superseded_by_event_id,
                },
            )

    def store_source(self, source: SourceRecord) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO lore_sources "
                    "(source_id, title, publisher, source_class, edition, publication_date, "
                    "language, locator, access_type, canon_scope_json, viewpoint, rights_profile, "
                    "review_status, reviewed_by, reviewed_at_utc) "
                    "VALUES (:id, :title, :pub, :cls, :ed, :pub_date, :lang, :loc, :access, "
                    ":scope, :viewpoint, :rights, :status, :by, :at)"
                ),
                {
                    "id": source.source_id,
                    "title": source.title,
                    "pub": source.publisher,
                    "cls": str(source.source_class.value),
                    "ed": source.edition,
                    "pub_date": source.publication_date.isoformat() if source.publication_date else None,
                    "lang": source.language,
                    "loc": source.locator,
                    "access": source.access_type,
                    "scope": json.dumps(source.canon_scope),
                    "viewpoint": str(source.viewpoint.value),
                    "rights": source.rights_profile,
                    "status": str(source.review_status.value),
                    "by": source.reviewed_by,
                    "at": source.reviewed_at.isoformat() if source.reviewed_at else None,
                },
            )

    def store_entity(self, entity: LoreEntity) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO lore_entities "
                    "(entity_id, canonical_name, entity_type, aliases_json, parent_entity_ids_json, "
                    "origin, valid_time_json, source_refs_json, review_status, pack_id) "
                    "VALUES (:id, :name, :type, :aliases, :parents, :origin, :valid_time, "
                    ":refs, :status, :pack)"
                ),
                {
                    "id": entity.entity_id,
                    "name": entity.canonical_name,
                    "type": entity.entity_type,
                    "aliases": json.dumps([a.model_dump() for a in entity.aliases], ensure_ascii=False),
                    "parents": json.dumps(entity.parent_entity_ids),
                    "origin": str(entity.origin.value),
                    "valid_time": json.dumps(entity.valid_time),
                    "refs": json.dumps(entity.source_refs),
                    "status": str(entity.review_status.value),
                    "pack": "primer.galaxy.core",
                },
            )

    def store_fact(self, fact: LoreFact) -> None:
        alias_terms = self._entity_alias_text(fact.entity_ids)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO lore_facts "
                    "(fact_id, claim, fact_type, entity_ids_json, relation_ids_json, "
                    "valid_time_json, valid_regions_json, source_refs_json, confidence, "
                    "conflicts_with_json, spoiler_level, review_status, pack_id, pack_version) "
                    "VALUES (:id, :claim, :type, :entities, :relations, :valid_time, :regions, "
                    ":refs, :confidence, :conflicts, :spoiler, :status, :pack, :pack_ver)"
                ),
                {
                    "id": fact.fact_id,
                    "claim": fact.claim,
                    "type": fact.fact_type,
                    "entities": json.dumps(fact.entity_ids),
                    "relations": json.dumps(fact.relation_ids),
                    "valid_time": json.dumps(fact.valid_time),
                    "regions": json.dumps(fact.valid_regions),
                    "refs": json.dumps(fact.source_refs),
                    "confidence": str(fact.confidence.value),
                    "conflicts": json.dumps(fact.conflicts_with),
                    "spoiler": fact.spoiler_level,
                    "status": str(fact.review_status.value),
                    "pack": fact.pack_id,
                    "pack_ver": fact.pack_version,
                },
            )
            self._sync_fts_fact(conn, fact, alias_terms)

    def _sync_fts_fact(self, conn: Any, fact: LoreFact, alias_terms: str) -> None:
        conn.execute(
            text("DELETE FROM lore_facts_fts WHERE fact_id = :id"),
            {"id": fact.fact_id},
        )
        if str(fact.review_status.value) == "approved":
            conn.execute(
                text("INSERT INTO lore_facts_fts (fact_id, claim, entity_aliases, pack_id) "
                     "VALUES (:id, :claim, :aliases, :pack)"),
                {"id": fact.fact_id, "claim": fact.claim, "aliases": alias_terms, "pack": fact.pack_id},
            )

    def _entity_alias_text(self, entity_ids: list[str]) -> str:
        if not entity_ids:
            return ""
        placeholders = ",".join(f":e{i}" for i in range(len(entity_ids)))
        params = {f"e{i}": eid for i, eid in enumerate(entity_ids)}
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT aliases_json FROM lore_entities WHERE entity_id IN ({placeholders})"
                ),
                params,
            ).fetchall()
        parts: list[str] = []
        for row in rows:
            aliases = json.loads(row[0]) if row[0] else []
            for alias in aliases:
                text_value = alias.get("text", "") if isinstance(alias, dict) else str(alias)
                if text_value:
                    parts.append(text_value)
        return " ".join(parts)

    # ---- reads (approved only) ----

    def get_fact(self, fact_id: str) -> LoreFact | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT fact_id, claim, fact_type, entity_ids_json, relation_ids_json, "
                     "valid_time_json, valid_regions_json, source_refs_json, confidence, "
                     "conflicts_with_json, spoiler_level, review_status, pack_id, pack_version "
                     "FROM lore_facts WHERE fact_id = :id AND review_status = 'approved'"),
                {"id": fact_id},
            ).fetchone()
        return self._fact_from_row(row) if row else None

    def get_entity(self, entity_id: str) -> LoreEntity | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT entity_id, canonical_name, entity_type, aliases_json, "
                     "parent_entity_ids_json, origin, valid_time_json, source_refs_json, "
                     "review_status FROM lore_entities "
                     "WHERE entity_id = :id AND review_status = 'approved'"),
                {"id": entity_id},
            ).fetchone()
        if row is None:
            return None
        return LoreEntity(
            entity_id=row[0],
            canonical_name=row[1],
            entity_type=row[2],
            aliases=json.loads(row[3]),
            parent_entity_ids=json.loads(row[4]),
            origin=row[5],
            valid_time=json.loads(row[6]),
            source_refs=json.loads(row[7]),
            review_status=row[8],
        )

    def get_source(self, source_id: str) -> SourceRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT source_id, title, publisher, source_class, edition, publication_date, "
                     "language, locator, access_type, canon_scope_json, viewpoint, rights_profile, "
                     "review_status, reviewed_by, reviewed_at_utc FROM lore_sources "
                     "WHERE source_id = :id"),
                {"id": source_id},
            ).fetchone()
        if row is None:
            return None
        from noosphere40k.domain.enums import ReviewStatus, SourceClass, SourceViewpoint

        return SourceRecord(
            source_id=row[0],
            title=row[1],
            publisher=row[2],
            source_class=SourceClass(row[3]),
            edition=row[4],
            publication_date=row[5],
            language=row[6],
            locator=row[7],
            access_type=row[8],
            canon_scope=json.loads(row[9]),
            viewpoint=SourceViewpoint(row[10]),
            rights_profile=row[11],
            review_status=ReviewStatus(row[12]),
            reviewed_by=row[13],
            reviewed_at=None,
        )

    def get_glossary(self, term_id: str) -> GlossaryEntry | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT term_id, entity_id, english_name, standard_zh_cn, aliases_zh_cn_json, "
                     "deprecated_translations_json, child_explanation, beginner_explanation, "
                     "deep_explanation, viewpoint_warning, spoiler_level, source_refs_json "
                     "FROM glossary_entries WHERE term_id = :id"),
                {"id": term_id},
            ).fetchone()
        if row is None:
            return None
        return GlossaryEntry(
            term_id=row[0],
            entity_id=row[1],
            english_name=row[2],
            standard_zh_cn=row[3],
            aliases_zh_cn=json.loads(row[4]),
            deprecated_translations=json.loads(row[5]),
            child_explanation=row[6],
            beginner_explanation=row[7],
            deep_explanation=row[8],
            viewpoint_warning=row[9],
            spoiler_level=row[10],
            source_refs=json.loads(row[11]),
        )

    def get_character_knowledge(self, owner_character_id: str, subject_id: str) -> KnowledgeRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT owner_character_id, subject_id, status, reliability_basis_points, "
                     "learned_at_event_id, learned_from_character_id, source_viewpoint, "
                     "superseded_by_event_id FROM knowledge_records "
                     "WHERE owner_character_id = :o AND subject_id = :s"),
                {"o": owner_character_id, "s": subject_id},
            ).fetchone()
        if row is None:
            return None
        return KnowledgeRecord(
            owner_character_id=row[0],
            subject_id=row[1],
            status=row[2],
            reliability_basis_points=row[3],
            learned_at_event_id=row[4],
            learned_from_character_id=row[5],
            source_viewpoint=row[6],
            superseded_by_event_id=row[7],
        )

    def search(self, query: str, *, limit: int = 10) -> list[LoreFact]:
        """FTS5 full-text search restricted to approved facts."""
        if not query.strip():
            return []
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT f.fact_id, f.claim, f.fact_type, f.entity_ids_json, "
                    "f.relation_ids_json, f.valid_time_json, f.valid_regions_json, "
                    "f.source_refs_json, f.confidence, f.conflicts_with_json, f.spoiler_level, "
                    "f.review_status, f.pack_id, f.pack_version "
                    "FROM lore_facts_fts idx JOIN lore_facts f ON idx.fact_id = f.fact_id "
                    "WHERE lore_facts_fts MATCH :q AND f.review_status = 'approved' "
                    "ORDER BY rank LIMIT :lim"
                ),
                {"q": query, "lim": limit},
            ).fetchall()
        return [self._fact_from_row(row) for row in rows]

    def search_by_alias(self, alias: str, *, limit: int = 10) -> list[LoreFact]:
        """Find facts whose entities carry a matching alias (CJK-safe LIKE fallback)."""
        pattern = f"%{alias}%"
        with self.engine.connect() as conn:
            # find entities whose alias text contains the query
            entity_rows = conn.execute(
                text("SELECT entity_id FROM lore_entities WHERE aliases_json LIKE :p"),
                {"p": pattern},
            ).fetchall()
            entity_ids = [row[0] for row in entity_rows]
            if not entity_ids:
                return []
            results: list[LoreFact] = []
            for eid in entity_ids:
                rows = conn.execute(
                    text(
                        "SELECT fact_id, claim, fact_type, entity_ids_json, relation_ids_json, "
                        "valid_time_json, valid_regions_json, source_refs_json, confidence, "
                        "conflicts_with_json, spoiler_level, review_status, pack_id, pack_version "
                        "FROM lore_facts WHERE entity_ids_json LIKE :e AND review_status = 'approved' "
                        "LIMIT :lim"
                    ),
                    {"e": f"%{eid}%", "lim": limit},
                ).fetchall()
                results.extend(self._fact_from_row(row) for row in rows)
                if len(results) >= limit:
                    break
        return results[:limit]

    @staticmethod
    def _fact_from_row(row: Any) -> LoreFact:
        from noosphere40k.domain.enums import ConfidenceLevel, ReviewStatus

        return LoreFact(
            fact_id=row[0],
            claim=row[1],
            fact_type=row[2],
            entity_ids=json.loads(row[3]),
            relation_ids=json.loads(row[4]),
            valid_time=json.loads(row[5]),
            valid_regions=json.loads(row[6]),
            source_refs=json.loads(row[7]),
            confidence=ConfidenceLevel(row[8]),
            conflicts_with=json.loads(row[9]),
            spoiler_level=row[10],
            review_status=ReviewStatus(row[11]),
            pack_id=row[12],
            pack_version=row[13],
        )

    # ---- review workflow reads/writes (D-08) ----

    def get_fact_any(self, fact_id: str) -> LoreFact | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT fact_id, claim, fact_type, entity_ids_json, relation_ids_json, "
                     "valid_time_json, valid_regions_json, source_refs_json, confidence, "
                     "conflicts_with_json, spoiler_level, review_status, pack_id, pack_version "
                     "FROM lore_facts WHERE fact_id = :id"),
                {"id": fact_id},
            ).fetchone()
        return self._fact_from_row(row) if row else None

    def get_entity_any(self, entity_id: str) -> LoreEntity | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT entity_id, canonical_name, entity_type, aliases_json, "
                     "parent_entity_ids_json, origin, valid_time_json, source_refs_json, "
                     "review_status FROM lore_entities WHERE entity_id = :id"),
                {"id": entity_id},
            ).fetchone()
        if row is None:
            return None
        return LoreEntity(
            entity_id=row[0],
            canonical_name=row[1],
            entity_type=row[2],
            aliases=json.loads(row[3]),
            parent_entity_ids=json.loads(row[4]),
            origin=row[5],
            valid_time=json.loads(row[6]),
            source_refs=json.loads(row[7]),
            review_status=row[8],
        )

    def get_source_any(self, source_id: str) -> SourceRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT source_id, title, publisher, source_class, edition, publication_date, "
                     "language, locator, access_type, canon_scope_json, viewpoint, rights_profile, "
                     "review_status, reviewed_by, reviewed_at_utc FROM lore_sources "
                     "WHERE source_id = :id"),
                {"id": source_id},
            ).fetchone()
        if row is None:
            return None
        from noosphere40k.domain.enums import ReviewStatus, SourceClass, SourceViewpoint

        return SourceRecord(
            source_id=row[0],
            title=row[1],
            publisher=row[2],
            source_class=SourceClass(row[3]),
            edition=row[4],
            publication_date=row[5],
            language=row[6],
            locator=row[7],
            access_type=row[8],
            canon_scope=json.loads(row[9]),
            viewpoint=SourceViewpoint(row[10]),
            rights_profile=row[11],
            review_status=ReviewStatus(row[12]),
            reviewed_by=row[13],
            reviewed_at=None,
        )

    def update_fact_review(self, fact_id: str, status: str, reviewer: str) -> None:
        from datetime import UTC, datetime

        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE lore_facts SET review_status = :s, reviewed_by = :r, "
                     "reviewed_at_utc = :t WHERE fact_id = :id"),
                {"s": status, "r": reviewer, "t": datetime.now(UTC).isoformat(), "id": fact_id},
            )
            fact = self.get_fact_any(fact_id)
            if fact is not None:
                self._sync_fts_fact(conn, fact, self._entity_alias_text(fact.entity_ids))

    def update_entity_review(self, entity_id: str, status: str, reviewer: str) -> None:
        from datetime import UTC, datetime

        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE lore_entities SET review_status = :s, reviewed_by = :r, "
                     "reviewed_at_utc = :t WHERE entity_id = :id"),
                {"s": status, "r": reviewer, "t": datetime.now(UTC).isoformat(), "id": entity_id},
            )

    def update_source_review(self, source_id: str, status: str, reviewer: str) -> None:
        from datetime import UTC, datetime

        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE lore_sources SET review_status = :s, reviewed_by = :r, "
                     "reviewed_at_utc = :t WHERE source_id = :id"),
                {"s": status, "r": reviewer, "t": datetime.now(UTC).isoformat(), "id": source_id},
            )


__all__ = ["LoreRepository"]