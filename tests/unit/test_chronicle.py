"""B-08 + E-07: chronicle generation from committed events; recap."""

from __future__ import annotations

from datetime import UTC, datetime

from noosphere40k.application.chronicle import build_chronicle, generate_recap
from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.events import (
    INITIAL_GAME_STATE,
    EventEnvelope,
    EventType,
    reduce_event,
)


def _event(seq: int, event_type: EventType, payload=None) -> EventEnvelope:
    return EventEnvelope(
        event_id=f"e{seq}",
        campaign_id="c",
        sequence=seq,
        turn_id=f"t{seq}",
        event_type=event_type.value,
        occurred_at_utc=datetime.now(UTC),
        correlation_id="tr",
        origin=EventOrigin.RULES,
        payload=payload or {},
    )


def test_chronicle_lists_committed_events_only() -> None:
    events = [
        _event(1, EventType.CAMPAIGN_CREATED, {"display_name": "Ada"}),
        _event(2, EventType.VOCATION_STARTED, {"vocation_id": "admin_clerk"}),
        _event(3, EventType.TIME_ADVANCED, {"days": 3650}),
        _event(4, EventType.LIFE_STAGE_CHANGED, {"life_stage": "adolescence"}),
    ]
    state = INITIAL_GAME_STATE.model_copy()
    for event in events:
        state = reduce_event(state, event)
    chronicle = build_chronicle("c", events, state)
    assert any("诞生" in e.summary for e in chronicle.entries)
    assert any("admin_clerk" in e.summary for e in chronicle.entries)
    assert any("3650" in e.summary for e in chronicle.entries)
    assert chronicle.ended is False


def test_chronicle_death_ends_terminal() -> None:
    events = [
        _event(1, EventType.CAMPAIGN_CREATED, {"display_name": "Ada"}),
        _event(2, EventType.CHARACTER_DIED, {"reason": "战斗阵亡"}),
        _event(3, EventType.CAMPAIGN_TERMINATED),
    ]
    state = INITIAL_GAME_STATE.model_copy()
    for event in events:
        state = reduce_event(state, event)
    chronicle = build_chronicle("c", events, state)
    assert chronicle.ended is True
    assert chronicle.death_reason == "战斗阵亡"
    assert any("死亡" in e.summary for e in chronicle.entries)


def test_chronicle_does_not_invent_facts() -> None:
    events = [_event(1, EventType.CAMPAIGN_CREATED, {"display_name": "Ada"})]
    state = reduce_event(INITIAL_GAME_STATE.model_copy(), events[0])
    chronicle = build_chronicle("c", events, state)
    assert len(chronicle.entries) == 1
    assert "动机" not in " ".join(e.summary for e in chronicle.entries)


def test_recap_returns_recent_events() -> None:
    events = [
        _event(1, EventType.CAMPAIGN_CREATED, {"display_name": "Ada"}),
        _event(2, EventType.SKILL_PROGRESSED, {"skill_id": "literacy", "progress": 10}),
    ]
    recap = generate_recap(events)
    assert "Ada" in recap
    assert "literacy" in recap


def test_recap_empty() -> None:
    assert "还没有" in generate_recap([])


def test_recap_only_summarizes() -> None:
    events = [_event(1, EventType.CAMPAIGN_CREATED, {"display_name": "Ada"})]
    recap = generate_recap(events, limit=1)
    assert "Ada" in recap
    assert "结局" not in recap