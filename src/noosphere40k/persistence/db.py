"""SQLite database plumbing (TECHNICAL_SPEC §11; C-02).

WAL mode, foreign keys on, numbered migrations recorded in schema_migrations.
Each migration runs inside its own transaction; failure rolls back and leaves
the database file as it was before the failed step.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, text

from noosphere40k.domain.errors import MigrationFailedError

SCHEMA_VERSION = 1


def _pragma_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _pragma_journal_mode(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def open_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    from sqlalchemy import event

    event.listen(engine, "connect", _pragma_foreign_keys)
    event.listen(engine, "connect", _pragma_journal_mode)
    return engine


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = "\n".join(self.statements).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def run_migrations(engine: Engine, migrations: Sequence[Migration]) -> list[Migration]:
    """Apply unapplied migrations in version order, each in its own transaction."""
    pending: list[Migration] = []
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations ("
                          "version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                          "checksum TEXT NOT NULL, applied_at_utc TEXT NOT NULL)"))
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}
    for migration in sorted(migrations, key=lambda m: m.version):
        if migration.version in applied:
            continue
        try:
            with engine.begin() as conn:
                for statement in migration.statements:
                    conn.execute(text(statement))
                conn.execute(
                    text("INSERT INTO schema_migrations (version, name, checksum, applied_at_utc) "
                         "VALUES (:v, :n, :c, :a)"),
                    {
                        "v": migration.version,
                        "n": migration.name,
                        "c": migration.checksum,
                        "a": datetime.now(UTC).isoformat(),
                    },
                )
        except Exception as exc:
            raise MigrationFailedError(
                f"migration {migration.version}-{migration.name} failed",
                context={"version": migration.version, "name": migration.name},
            ) from exc
        pending.append(migration)
    return pending


def db_metadata(engine: Engine) -> dict[str, object]:
    """Report schema version and applied migrations (doctor / verify)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT version, name, checksum, applied_at_utc "
                 "FROM schema_migrations ORDER BY version")
        ).fetchall()
    return {
        "schema_version": SCHEMA_VERSION,
        "applied": [
            {"version": r[0], "name": r[1], "checksum": r[2], "applied_at_utc": r[3]}
            for r in rows
        ],
    }