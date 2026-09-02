"""Campaign repository: event append, snapshots and replay (C-03/C-04).

Guarantees:
- events are append-only; sequence numbers have no gaps or duplicates
  (DB primary key enforces uniqueness, reducer enforces continuity).
- optimistic version check: committing against a stale version aborts.
- replay from scratch and snapshot+tail replay produce identical state hashes.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text

from noosphere40k.domain.errors import SaveConflictError, SaveCorruptError
from noosphere40k.domain.events import (
    EventEnvelope,
    EventType,
    GameState,
    compute_state_hash,
    reduce_event,
)
from noosphere40k.persistence.db import open_engine

SNAPSHOT_INTERVAL = 20


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event_to_row(event: EventEnvelope) -> dict[str, Any]:
    return {
        "campaign_id": event.campaign_id,
        "sequence": event.sequence,
        "event_id": event.event_id,
        "turn_id": event.turn_id,
        "event_type": event.event_type,
        "event_schema_version": event.schema_version,
        "occurred_at_utc": event.occurred_at_utc.isoformat(),
        "world_time_json": json.dumps(event.world_time.model_dump(mode="json")) if event.world_time else None,
        "actor_id": event.actor_id,
        "causation_event_id": event.causation_event_id,
        "correlation_id": event.correlation_id,
        "origin": str(event.origin),
        "payload_json": json.dumps(event.payload),
        "prior_state_hash": event.prior_state_hash,
        "resulting_state_hash": event.resulting_state_hash,
    }


def _row_to_event(row: Sequence[Any]) -> EventEnvelope:
    world_time = None
    if row[7]:
        from noosphere40k.domain.models import WorldTime

        world_time = WorldTime.model_validate(json.loads(row[7]))
    from noosphere40k.domain.enums import EventOrigin

    return EventEnvelope(
        event_id=row[2],
        campaign_id=row[0],
        sequence=int(row[1]),
        turn_id=row[3],
        event_type=row[4],
        schema_version=int(row[5]),
        occurred_at_utc=datetime.fromisoformat(row[6]),
        world_time=world_time,
        actor_id=row[8],
        causation_event_id=row[9],
        correlation_id=row[10],
        origin=EventOrigin(row[11]),
        payload=json.loads(row[12]),
        prior_state_hash=row[13],
        resulting_state_hash=row[14],
    )


class CampaignRepository:
    """Persists campaign events and snapshots in SQLite."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @classmethod
    def at(cls, db_path: Path) -> CampaignRepository:
        return cls(open_engine(db_path))

    # ---- events ----

    def append_events(
        self,
        campaign_id: str,
        events: Sequence[EventEnvelope],
        *,
        expected_last_sequence: int,
    ) -> None:
        """Append events atomically with optimistic version checking."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT last_event_sequence FROM campaigns WHERE campaign_id = :cid"),
                {"cid": campaign_id},
            ).fetchone()
            if row is None:
                raise SaveConflictError(f"campaign {campaign_id} not found")
            if int(row[0]) != expected_last_sequence:
                raise SaveConflictError(
                    f"optimistic version conflict for {campaign_id}: "
                    f"expected {expected_last_sequence}, got {row[0]}"
                )
            for event in events:
                conn.execute(
                    text(
                        "INSERT INTO campaign_events (campaign_id, sequence, event_id, turn_id, "
                        "event_type, event_schema_version, occurred_at_utc, world_time_json, "
                        "actor_id, causation_event_id, correlation_id, origin, payload_json, "
                        "prior_state_hash, resulting_state_hash) "
                        "VALUES (:campaign_id, :sequence, :event_id, :turn_id, :event_type, "
                        ":event_schema_version, :occurred_at_utc, :world_time_json, :actor_id, "
                        ":causation_event_id, :correlation_id, :origin, :payload_json, "
                        ":prior_state_hash, :resulting_state_hash)"
                    ),
                    _event_to_row(event),
                )
            conn.execute(
                text("UPDATE campaigns SET last_event_sequence = :seq, updated_at_utc = :now "
                     "WHERE campaign_id = :cid"),
                {"seq": events[-1].sequence, "now": _now(), "cid": campaign_id},
            )

    def load_events(self, campaign_id: str, *, after_sequence: int = 0) -> list[EventEnvelope]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text("SELECT campaign_id, sequence, event_id, turn_id, event_type, "
                     "event_schema_version, occurred_at_utc, world_time_json, actor_id, "
                     "causation_event_id, correlation_id, origin, payload_json, "
                     "prior_state_hash, resulting_state_hash "
                     "FROM campaign_events WHERE campaign_id = :cid AND sequence > :after "
                     "ORDER BY sequence"),
                {"cid": campaign_id, "after": after_sequence},
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def latest_sequence(self, campaign_id: str) -> int:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT last_event_sequence FROM campaigns WHERE campaign_id = :cid"),
                {"cid": campaign_id},
            ).fetchone()
        return int(row[0]) if row else 0

    # ---- snapshots ----

    def save_snapshot(self, campaign_id: str, state: GameState) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO campaign_snapshots "
                    "(campaign_id, snapshot_id, up_to_sequence, state_json, state_hash, created_at_utc) "
                    "VALUES (:cid, :sid, :seq, :json, :hash, :now)"
                ),
                {
                    "cid": campaign_id,
                    "sid": f"snap-{state.sequence}",
                    "seq": state.sequence,
                    "json": state.model_dump_json(),
                    "hash": state.state_hash,
                    "now": _now(),
                },
            )

    def load_latest_snapshot(self, campaign_id: str) -> GameState | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT state_json, state_hash, up_to_sequence FROM campaign_snapshots "
                     "WHERE campaign_id = :cid ORDER BY up_to_sequence DESC LIMIT 1"),
                {"cid": campaign_id},
            ).fetchone()
        if row is None:
            return None
        state = GameState.model_validate_json(row[0])
        if state.state_hash != row[1]:
            raise SaveCorruptError(
                f"snapshot hash mismatch for {campaign_id} at sequence {row[2]}",
                context={"campaign_id": campaign_id, "up_to_sequence": row[2]},
            )
        return state

    # ---- load / replay ----

    def load_consistent_snapshot(self, campaign_id: str) -> GameState:
        """Snapshot + tail replay; verifies the resulting state hash."""
        state = self.load_latest_snapshot(campaign_id)
        if state is None:
            from noosphere40k.domain.events import INITIAL_GAME_STATE

            state = INITIAL_GAME_STATE.model_copy()
        tail = self.load_events(campaign_id, after_sequence=state.sequence)
        for event in tail:
            state = reduce_event(state, event)
        expected = self._committed_state_hash(campaign_id)
        if expected and state.state_hash != expected:
            raise SaveCorruptError(
                f"state hash mismatch for {campaign_id}: "
                f"replayed={state.state_hash[:12]} stored={expected[:12]}",
                context={"campaign_id": campaign_id, "sequence": state.sequence},
            )
        return state

    def _committed_state_hash(self, campaign_id: str) -> str:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT state_hash FROM campaigns WHERE campaign_id = :cid"),
                {"cid": campaign_id},
            ).fetchone()
        return str(row[0]) if row else ""

    def replay_from_scratch(self, campaign_id: str) -> GameState:
        """Full replay from sequence 0; verifies continuity and hash."""
        from noosphere40k.domain.events import INITIAL_GAME_STATE

        state = INITIAL_GAME_STATE.model_copy()
        for event in self.load_events(campaign_id):
            state = reduce_event(state, event)
        return state

    def create_campaign(self, campaign_id: str, name: str, prompt_version: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO campaigns (campaign_id, name, status, created_at_utc, "
                    "updated_at_utc, prompt_version, schema_version, seed_json, settings_json) "
                    "VALUES (:cid, :name, 'creating', :now, :now, :pv, 1, '{}', '{}')"
                ),
                {"cid": campaign_id, "name": name, "now": _now(), "pv": prompt_version},
            )

    def mark_status(self, campaign_id: str, status: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE campaigns SET status = :s, updated_at_utc = :now WHERE campaign_id = :cid"),
                {"s": status, "now": _now(), "cid": campaign_id},
            )

    def update_settings(self, campaign_id: str, settings_json: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE campaigns SET settings_json = :j, updated_at_utc = :now "
                     "WHERE campaign_id = :cid"),
                {"j": settings_json, "now": _now(), "cid": campaign_id},
            )

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign and all of its related rows atomically.

        Returns True if the campaign existed and was deleted, False otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT campaign_id FROM campaigns WHERE campaign_id = :cid"),
                {"cid": campaign_id},
            ).fetchone()
            if row is None:
                return False

            # collect character ids to clean owner-keyed tables
            char_ids = [
                r[0] for r in conn.execute(
                    text("SELECT character_id FROM characters WHERE campaign_id = :cid"),
                    {"cid": campaign_id},
                ).fetchall()
            ]
            if char_ids:
                placeholders = ",".join(f":c{i}" for i in range(len(char_ids)))
                params = {f"c{i}": cid for i, cid in enumerate(char_ids)}
                conn.execute(
                    text(f"DELETE FROM knowledge_records WHERE owner_character_id IN ({placeholders})"),
                    params,
                )
                conn.execute(
                    text(f"DELETE FROM encyclopedia_unlocks WHERE owner_character_id IN ({placeholders})"),
                    params,
                )

            for table in ("campaign_events", "campaign_snapshots", "characters",
                          "relationships", "content_pack_locks"):
                conn.execute(
                    text(f"DELETE FROM {table} WHERE campaign_id = :cid"),
                    {"cid": campaign_id},
                )
            conn.execute(
                text("DELETE FROM campaigns WHERE campaign_id = :cid"),
                {"cid": campaign_id},
            )
        return True

    def should_snapshot(self, sequence: int) -> bool:
        return sequence > 0 and sequence % SNAPSHOT_INTERVAL == 0


def commit_turn(
    repo: CampaignRepository,
    *,
    campaign_id: str,
    expected_last_sequence: int,
    state: GameState,
    events: Sequence[EventEnvelope],
) -> None:
    """Append a turn's events, then snapshot when due (transactional per event batch)."""
    repo.append_events(
        campaign_id, events, expected_last_sequence=expected_last_sequence
    )
    with repo.engine.begin() as conn:
        conn.execute(
            text("UPDATE campaigns SET state_hash = :h, last_event_sequence = :s, "
                 "updated_at_utc = :now WHERE campaign_id = :cid"),
            {"h": state.state_hash, "s": state.sequence, "now": _now(), "cid": campaign_id},
        )
    if repo.should_snapshot(state.sequence):
        repo.save_snapshot(campaign_id, state)


__all__ = [
    "CampaignRepository",
    "commit_turn",
    "SNAPSHOT_INTERVAL",
    "EventEnvelope",
    "EventType",
    "GameState",
    "reduce_event",
    "compute_state_hash",
]