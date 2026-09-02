"""C-03/C-04: repository, snapshots, optimistic versioning, replay."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import pytest

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.errors import SaveConflictError, SaveCorruptError
from noosphere40k.domain.events import (
    INITIAL_GAME_STATE,
    EventEnvelope,
    EventType,
    GameState,
    reduce_event,
)
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS
from noosphere40k.persistence.repositories import CampaignRepository, commit_turn


def _mk_event(campaign_id: str, sequence: int, event_type: EventType, payload=None) -> EventEnvelope:
    from datetime import datetime

    return EventEnvelope(
        event_id=f"evt-{sequence}",
        campaign_id=campaign_id,
        sequence=sequence,
        turn_id=f"t-{sequence}",
        event_type=event_type.value,
        occurred_at_utc=datetime.now(UTC),
        correlation_id=f"trace-{sequence}",
        origin=EventOrigin.RULES,
        payload=payload or {},
    )


@pytest.fixture
def repo(tmp_path: Path) -> CampaignRepository:
    db_path = tmp_path / "test.db"
    engine = open_engine(db_path)
    run_migrations(engine, MIGRATIONS)
    repository = CampaignRepository(engine)
    repository.create_campaign("camp.001", "Test", "prompt-0.1.0")
    return repository


def _created_event(campaign_id: str, sequence: int = 1) -> EventEnvelope:
    return _mk_event(campaign_id, sequence, EventType.CAMPAIGN_CREATED, {
        "character_id": "pc.1",
        "display_name": "Ada",
        "chronological_age_days": 2920,
        "status": "active",
    })


def _apply_and_commit(repo: CampaignRepository, state, events) -> GameState:
    expected = state.sequence
    for i, event in enumerate(events):
        event = event.model_copy(update={"prior_state_hash": state.state_hash})
        state = reduce_event(state, event)
        events[i] = event.model_copy(update={"resulting_state_hash": state.state_hash})
    commit_turn(repo, campaign_id="camp.001", expected_last_sequence=expected, state=state, events=events)
    return state


def test_create_and_load_events(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    state = _apply_and_commit(repo, state, [_created_event("camp.001")])
    assert repo.latest_sequence("camp.001") == 1
    events = repo.load_events("camp.001")
    assert len(events) == 1
    assert events[0].event_type == "CampaignCreated"
    assert events[0].resulting_state_hash == state.state_hash


def test_optimistic_version_conflict(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    state = _apply_and_commit(repo, state, [_created_event("camp.001")])
    # simulate a stale writer
    with pytest.raises(SaveConflictError):
        repo.append_events("camp.001", [], expected_last_sequence=99)


def test_events_have_no_gaps_or_duplicates(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    events = [_created_event("camp.001")]
    state = _apply_and_commit(repo, state, events)
    for i in range(2, 6):
        ev = _mk_event("camp.001", i, EventType.SNAPSHOT_CREATED)
        state = _apply_and_commit(repo, state, [ev])
    seqs = [e.sequence for e in repo.load_events("camp.001")]
    assert seqs == list(range(1, 6))


def test_replay_from_scratch_matches_committed(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    state = _apply_and_commit(repo, state, [_created_event("camp.001")])
    attr = _mk_event("camp.001", 2, EventType.ATTRIBUTE_CHANGED, {
        "attribute_id": "intellect", "value": 30,
    })
    state = _apply_and_commit(repo, state, [attr])
    replay = repo.replay_from_scratch("camp.001")
    assert replay.state_hash == state.state_hash


def test_snapshot_and_tail_replay_identical(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    state = _apply_and_commit(repo, state, [_created_event("camp.001")])
    # force a snapshot at sequence 1
    repo.save_snapshot("camp.001", state)
    attr = _mk_event("camp.001", 2, EventType.ATTRIBUTE_CHANGED, {
        "attribute_id": "intellect", "value": 30,
    })
    state = _apply_and_commit(repo, state, [attr])
    loaded = repo.load_consistent_snapshot("camp.001")
    assert loaded.state_hash == state.state_hash
    assert loaded.character is not None and loaded.character.attributes["intellect"] == 30


def test_tampered_event_payload_causes_hash_mismatch(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    state = _apply_and_commit(repo, state, [_created_event("camp.001")])
    with repo.engine.begin() as conn:
        from sqlalchemy import text

        conn.execute(
            text("UPDATE campaign_events SET payload_json = :p WHERE sequence = :s"),
            {"p": '{"character_id":"evil","display_name":"Evil",'
                  '"chronological_age_days":9999,"status":"active"}',
             "s": 1},
        )
    with pytest.raises(SaveCorruptError):
        repo.load_consistent_snapshot("camp.001")


def test_commit_turn_creates_snapshot_at_interval(repo: CampaignRepository) -> None:
    state = INITIAL_GAME_STATE.model_copy()
    events = [_created_event("camp.001")]
    for seq in range(2, 21):
        events.append(_mk_event("camp.001", seq, EventType.SNAPSHOT_CREATED))
    state = _apply_and_commit(repo, state, events)
    snap = repo.load_latest_snapshot("camp.001")
    assert snap is not None
    assert snap.sequence == 20