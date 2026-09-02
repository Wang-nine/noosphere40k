"""Extended reducers: age, skill, condition, wound, vocation, goal (B-04..B-08)."""

from __future__ import annotations

from datetime import UTC, datetime

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.events import (
    INITIAL_GAME_STATE,
    EventEnvelope,
    EventType,
    reduce_event,
)


def _evt(seq: int, etype: EventType, payload=None) -> EventEnvelope:
    return EventEnvelope(
        event_id=f"e{seq}",
        campaign_id="c",
        sequence=seq,
        turn_id="t",
        event_type=etype.value,
        occurred_at_utc=datetime.now(UTC),
        correlation_id="tr",
        origin=EventOrigin.RULES,
        payload=payload or {},
    )


def _created(seq: int = 1) -> EventEnvelope:
    return _evt(seq, EventType.CAMPAIGN_CREATED, {
        "character_id": "pc",
        "display_name": "Ada",
        "chronological_age_days": 2920,
        "attributes": {"body": 30},
    })


def test_time_advanced_increases_age() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.TIME_ADVANCED, {"days": 365}))
    assert state.character is not None
    assert state.character.chronological_age_days == 2920 + 365


def test_skill_progressed_updates_rank() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.SKILL_PROGRESSED, {
        "skill_id": "literacy", "progress": 12, "learned_from_event_id": "evt-x"
    }))
    skill = state.character.skills["literacy"]
    assert skill["rank"] == "trained"
    assert "evt-x" in skill["learned_from_event_ids"]


def test_condition_apply_and_remove() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.CONDITION_APPLIED, {"condition_id": "corruption_notable", "severity": 45}))
    assert any(c.condition_id == "corruption_notable" for c in state.character.conditions)
    state = reduce_event(state, _evt(3, EventType.CONDITION_REMOVED, {"condition_id": "corruption_notable"}))
    assert not any(c.condition_id == "corruption_notable" for c in state.character.conditions)


def test_wound_apply_and_change() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.WOUND_APPLIED, {
        "wound_id": "w1", "location": "leg", "severity": "major"
    }))
    assert any(w.wound_id == "w1" and w.severity == "major" for w in state.character.wounds)
    state = reduce_event(state, _evt(3, EventType.WOUND_CHANGED, {
        "wound_id": "w1", "severity": "critical", "treatment_state": "treated"
    }))
    wound = next(w for w in state.character.wounds if w.wound_id == "w1")
    assert wound.severity == "critical"
    assert wound.treatment_state == "treated"


def test_vocation_start_and_end() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.VOCATION_STARTED, {"vocation_id": "admin_clerk"}))
    assert len(state.character.vocation_history) == 1
    assert state.character.vocation_history[0].ended_event_id is None
    state = reduce_event(state, _evt(3, EventType.VOCATION_ENDED, {"vocation_id": "admin_clerk"}))
    assert state.character.vocation_history[0].ended_event_id is not None


def test_goal_add_and_update() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.GOAL_ADDED, {"goal_id": "g1", "description": "调查灰籍"}))
    assert any(g.goal_id == "g1" and g.status == "active" for g in state.character.goals)
    state = reduce_event(state, _evt(3, EventType.GOAL_UPDATED, {"goal_id": "g1", "status": "completed"}))
    goal = next(g for g in state.character.goals if g.goal_id == "g1")
    assert goal.status == "completed"


def test_character_died_sets_terminal() -> None:
    state = reduce_event(INITIAL_GAME_STATE, _created())
    state = reduce_event(state, _evt(2, EventType.CHARACTER_DIED, {"reason": "战斗阵亡"}))
    assert state.status == "terminal"