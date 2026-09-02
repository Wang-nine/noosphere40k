"""C-02: SQLite migration tests: fresh apply, idempotency, rollback safety."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from noosphere40k.domain.errors import MigrationFailedError
from noosphere40k.persistence.db import Migration, db_metadata, open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS


def test_fresh_database_auto_migrates(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "test.db")
    applied = run_migrations(engine, MIGRATIONS)
    assert [m.version for m in applied] == [1, 2]
    with engine.connect() as conn:
        tables = {row[0] for row in conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).fetchall()}
    assert {"campaigns", "campaign_events", "campaign_snapshots", "lore_facts",
            "schema_migrations"} <= tables
    assert db_metadata(engine)["schema_version"] == 1


def test_migrations_idempotent(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    assert run_migrations(engine, MIGRATIONS) == []


def test_event_sequence_unique_constraint(tmp_path: Path) -> None:
    from sqlalchemy.exc import IntegrityError

    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    insert = (
        "INSERT INTO campaign_events (campaign_id, sequence, event_id, turn_id, event_type, "
        "event_schema_version, occurred_at_utc, correlation_id, origin, payload_json) "
        "VALUES ('c', 1, 'e', 't', 'X', 1, '2026-01-01', 'r', 'system', '{}')"
    )
    with engine.begin() as conn:
        conn.execute(text(insert))
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text(insert.replace("'e'", "'e2'")))


def test_migration_failure_rolls_back_and_keeps_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = open_engine(db_path)
    run_migrations(engine, MIGRATIONS)

    bad = Migration(version=99, name="bad", statements=("SELECT * FROM does_not_exist",))
    with pytest.raises(MigrationFailedError):
        run_migrations(engine, [*MIGRATIONS, bad])

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar()
    assert count == len(MIGRATIONS)
    assert db_path.exists()


def test_foreign_keys_enabled(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    with engine.connect() as conn:
        value = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert value == 1