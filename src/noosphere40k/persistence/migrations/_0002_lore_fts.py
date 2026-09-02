"""Migration 0002: FTS5 search index for approved lore facts (D-03)."""

from __future__ import annotations

from noosphere40k.persistence.db import Migration

_STATEMENTS: tuple[str, ...] = (
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS lore_facts_fts USING fts5(
        fact_id UNINDEXED,
        claim,
        entity_aliases,
        pack_id UNINDEXED,
        tokenize='trigram'
    )
    """,
)

MIGRATION_0002 = Migration(version=2, name="lore_fts5", statements=_STATEMENTS)