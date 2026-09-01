"""C-01: event envelope, pure reducer, state hashing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.errors import UnknownEventError
from noosphere40k.domain.events import (
    EVENT_SCHEMA_VERSION,
    INITIAL_GAME_STATE,
    LLM_FORBIDDEN_EVENT_TYPES,
    EventEnvelope,
    EventType,
    compute_state_hash,
    reduce_event,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _event(
    sequence: int,
    event_type: EventType,
    *,
    campaign_id: str = "campaign.001",
    payload: dict | None = None,
    prior_hash: str = "",
) -> EventEnvelope:
    return EventEnvelope(
        event_id=f"evt-{uuid4().hex[:10]}",
        campaign_id=campaign_id,
        sequence=sequence,
        turn_id="t001",
        event_type=event_type.value,
        occurred_at_utc=_utcnow(),
        correlation_id="trace-1",
        origin=EventOrigin.RULES,
        payload=payload or {},
        prior_state_hash=prior_hash,
    )


def _campaign_created_event(sequence: int = 1, prior_hash: str = "") -> EventEnvelope:
    return _event(
        sequence,
        EventType.CAMPAIGN_CREATED,
        payload={
            "character_id": "character.pc.01",
            "display_name": "Ada",
            "chronological_age_days": 2920,
            "status": "creating",
            "life_stage": "childhood",
        },
        prior_hash=prior_hash,
    )


def test_reducer_is_pure_and_deterministic() -> None:
    s1 = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    s2 = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    assert s1.model_dump() == s2.model_dump()
    assert compute_state_hash(s1) == compute_state_hash(s2)


def test_state_hash_stable_across_dumps() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    assert state.state_hash == compute_state_hash(state)


def test_unknown_event_type_rejected() -> None:
    bad = _campaign_created_event().model_copy(update={"event_type": "SomeMadeUpEvent"})
    with pytest.raises(UnknownEventError):
        reduce_event(INITIAL_GAME_STATE, bad)


def test_unregistered_event_type_rejected() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    with pytest.raises(UnknownEventError):
        reduce_event(state, _event(2, EventType.CHECK_RESOLVED))


def test_sequence_must_be_continuous() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    with pytest.raises(UnknownEventError):
        reduce_event(state, _event(3, EventType.SNAPSHOT_CREATED))


def test_first_event_must_be_campaign_created() -> None:
    with pytest.raises(UnknownEventError):
        reduce_event(INITIAL_GAME_STATE, _event(1, EventType.SNAPSHOT_CREATED))


def test_prior_hash_mismatch_rejected() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    forged = _event(2, EventType.SNAPSHOT_CREATED, prior_hash="deadbeef")
    with pytest.raises(UnknownEventError):
        reduce_event(state, forged)


def test_schema_version_mismatch_rejected() -> None:
    bad = _campaign_created_event().model_copy(update={"schema_version": EVENT_SCHEMA_VERSION + 1})
    with pytest.raises(UnknownEventError):
        reduce_event(INITIAL_GAME_STATE, bad)


def test_snapshot_noop_preserves_state_hash() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    snap = _event(2, EventType.SNAPSHOT_CREATED, prior_hash=state.state_hash)
    next_state = reduce_event(state, snap)
    assert next_state.sequence == 2
    assert next_state.state_hash == compute_state_hash(next_state)


def test_life_stage_and_attribute_reducers() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _campaign_created_event())
    stage = _event(2, EventType.LIFE_STAGE_CHANGED, prior_hash=state.state_hash,
                   payload={"life_stage": "adolescence"})
    state = reduce_event(state, stage)
    assert state.character is not None and state.character.life_stage == "adolescence"
    attr = _event(3, EventType.ATTRIBUTE_CHANGED, prior_hash=state.state_hash,
                  payload={"attribute_id": "intellect", "value": 30})
    state = reduce_event(state, attr)
    assert state.character is not None and state.character.attributes["intellect"] == 30


def test_llm_forbidden_event_types_exactly_contract() -> None:
    expected = {
        EventType.RANDOM_DRAWN,
        EventType.CHECK_RESOLVED,
        EventType.ATTRIBUTE_CHANGED,
        EventType.CHARACTER_DIED,
        EventType.CAMPAIGN_TERMINATED,
        EventType.SNAPSHOT_CREATED,
    }
    assert expected == LLM_FORBIDDEN_EVENT_TYPES