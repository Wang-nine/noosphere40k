"""Migration 0003: add reviewer audit columns to lore tables (D-08)."""

from __future__ import annotations

from noosphere40k.persistence.db import Migration

_STATEMENTS: tuple[str, ...] = (
    """
    ALTER TABLE lore_facts ADD COLUMN reviewed_by TEXT
    """,
    """
    ALTER TABLE lore_facts ADD COLUMN reviewed_at_utc TEXT
    """,
    """
    ALTER TABLE lore_entities ADD COLUMN reviewed_by TEXT
    """,
    """
    ALTER TABLE lore_entities ADD COLUMN reviewed_at_utc TEXT
    """,
)

MIGRATION_0003 = Migration(version=3, name="lore_review_audit", statements=_STATEMENTS)