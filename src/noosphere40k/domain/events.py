"""Event envelope and the pure event reducer (DATA_PROTOCOL_SPEC §13, §14; C-01).

``new_state = reduce_event(old_state, event)`` is a pure function. Unknown
event types and out-of-order sequences are rejected. State hashing is
deterministic and independent of the Python version.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import cast

from pydantic import Field

from noosphere40k.domain.enums import EventOrigin
from noosphere40k.domain.errors import UnknownEventError
from noosphere40k.domain.models import (
    GameState,
    PlayerCharacter,
    StrictModel,
    WorldTime,
)

EVENT_SCHEMA_VERSION = 1

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "EventType",
    "LLM_FORBIDDEN_EVENT_TYPES",
    "EventEnvelope",
    "GameState",
    "INITIAL_GAME_STATE",
    "reduce_event",
    "compute_state_hash",
    "canonical_state_dump",
]


class EventType(StrEnum):
    CAMPAIGN_CREATED = "CampaignCreated"
    CAMPAIGN_SETTING_CHANGED = "CampaignSettingChanged"
    PLAYER_INPUT_ACCEPTED = "PlayerInputAccepted"
    ACTION_INTENT_RESOLVED = "ActionIntentResolved"
    RANDOM_DRAWN = "RandomDrawn"
    CHECK_RESOLVED = "CheckResolved"
    TIME_ADVANCED = "TimeAdvanced"
    LIFE_STAGE_CHANGED = "LifeStageChanged"
    ATTRIBUTE_CHANGED = "AttributeChanged"
    SKILL_PROGRESSED = "SkillProgressed"
    TRAIT_ADDED = "TraitAdded"
    TRAIT_REMOVED = "TraitRemoved"
    CONDITION_APPLIED = "ConditionApplied"
    CONDITION_REMOVED = "ConditionRemoved"
    WOUND_APPLIED = "WoundApplied"
    WOUND_CHANGED = "WoundChanged"
    CHARACTER_DIED = "CharacterDied"
    INVENTORY_ADDED = "InventoryAdded"
    INVENTORY_REMOVED = "InventoryRemoved"
    RESOURCE_CHANGED = "ResourceChanged"
    RELATIONSHIP_CHANGED = "RelationshipChanged"
    KNOWLEDGE_CHANGED = "KnowledgeChanged"
    ENCYCLOPEDIA_UNLOCKED = "EncyclopediaUnlocked"
    GOAL_ADDED = "GoalAdded"
    GOAL_UPDATED = "GoalUpdated"
    GOAL_COMPLETED = "GoalCompleted"
    VOCATION_STARTED = "VocationStarted"
    VOCATION_ENDED = "VocationEnded"
    LOCATION_CHANGED = "LocationChanged"
    NPC_INTRODUCED = "NPCIntroduced"
    NPC_PROFILE_FROZEN = "NPCProfileFrozen"
    SCENE_STARTED = "SceneStarted"
    SCENE_COMPLETED = "SceneCompleted"
    LORE_CLAIM_USED = "LoreClaimUsed"
    NARRATION_RECORDED = "NarrationRecorded"
    CAMPAIGN_TERMINATED = "CampaignTerminated"
    SNAPSHOT_CREATED = "SnapshotCreated"


LLM_FORBIDDEN_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.RANDOM_DRAWN,
        EventType.CHECK_RESOLVED,
        EventType.ATTRIBUTE_CHANGED,
        EventType.CHARACTER_DIED,
        EventType.CAMPAIGN_TERMINATED,
        EventType.SNAPSHOT_CREATED,
    }
)


class EventEnvelope(StrictModel):
    event_id: str
    campaign_id: str
    sequence: int
    turn_id: str
    event_type: str
    schema_version: int = EVENT_SCHEMA_VERSION
    occurred_at_utc: datetime
    world_time: WorldTime | None = None
    actor_id: str | None = None
    causation_event_id: str | None = None
    correlation_id: str
    origin: EventOrigin
    payload: dict[str, object] = Field(default_factory=dict)
    prior_state_hash: str = ""
    resulting_state_hash: str = ""

    @property
    def type_enum(self) -> EventType:
        try:
            return EventType(self.event_type)
        except ValueError as exc:
            raise UnknownEventError(f"unknown event type: {self.event_type}") from exc


def canonical_state_dump(state: GameState) -> str:
    data = state.model_dump(mode="json")
    data.pop("state_hash", None)
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_state_hash(state: GameState) -> str:
    return hashlib.sha256(canonical_state_dump(state).encode("utf-8")).hexdigest()


INITIAL_GAME_STATE = GameState(campaign_id="", status="creating", sequence=0, state_hash="")


Reducer = Callable[[GameState, EventEnvelope], GameState]


def _created(state: GameState, event: EventEnvelope) -> GameState:
    payload = event.payload
    character = None
    if payload.get("character_id"):
        attributes = cast(dict[str, int], payload.get("attributes")) or {}
        character = PlayerCharacter(
            character_id=payload["character_id"],
            display_name=payload.get("display_name", "Unknown"),
            birth_world_time=WorldTime(
                era_id=payload.get("era_id", event.campaign_id),
                local_calendar_id=payload.get("local_calendar_id", "local"),
                ordering_key=0,
                precision="era",
            ),
            chronological_age_days=payload["chronological_age_days"],
            subjective_age_days=payload.get("subjective_age_days", payload["chronological_age_days"]),
            life_stage=payload.get("life_stage", "childhood"),
            origin_id=payload.get("origin_id", ""),
            attributes=dict(attributes),
        )
    return state.model_copy(
        update={
            "campaign_id": event.campaign_id,
            "status": payload.get("status", "creating"),
            "sequence": event.sequence,
            "world_time": event.world_time,
            "character": character,
        }
    )


def _time_advanced(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"world_time": event.world_time, "sequence": event.sequence})
    days = cast(int, event.payload.get("days", 0))
    new_age = character.chronological_age_days + days
    new_subjective = character.subjective_age_days + days
    return state.model_copy(
        update={
            "world_time": event.world_time,
            "sequence": event.sequence,
            "character": character.model_copy(
                update={
                    "chronological_age_days": new_age,
                    "subjective_age_days": new_subjective,
                }
            ),
        }
    )


def _skill_progressed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    skill_id = str(event.payload["skill_id"])
    progress = cast(int, event.payload.get("progress", 0))
    skills = dict(character.skills)
    entry = dict(skills.get(skill_id, {"rank": "untrained", "progress": 0, "learned_from_event_ids": []}))
    entry["progress"] = int(cast(int, entry.get("progress", 0))) + progress
    learned = list(cast(list[object], entry.get("learned_from_event_ids", [])))
    cause = event.payload.get("learned_from_event_id")
    if cause and cause not in learned:
        learned.append(str(cause))
    entry["learned_from_event_ids"] = learned
    rank = _rank_from_progress(int(cast(int, entry["progress"])))
    entry["rank"] = rank
    skills[skill_id] = entry
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"skills": skills}),
        }
    )


def _rank_from_progress(progress: int) -> str:
    if progress >= 60:
        return "master"
    if progress >= 35:
        return "specialist"
    if progress >= 10:
        return "trained"
    return "untrained"


def _condition_applied(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    from noosphere40k.domain.models import Condition

    condition = Condition(
        condition_id=str(event.payload["condition_id"]),
        severity=cast(int, event.payload.get("severity", 1)),
        applied_event_id=event.event_id,
    )
    conditions = [c for c in character.conditions if c.condition_id != condition.condition_id]
    conditions.append(condition)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"conditions": conditions}),
        }
    )


def _condition_removed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    condition_id = str(event.payload["condition_id"])
    conditions = [c for c in character.conditions if c.condition_id != condition_id]
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"conditions": conditions}),
        }
    )


def _wound_applied(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    from noosphere40k.domain.models import Wound

    wound = Wound(
        wound_id=str(event.payload["wound_id"]),
        location=str(event.payload.get("location", "body")),
        severity=str(event.payload.get("severity", "minor")),
        cause_event_id=event.event_id,
        treatment_state="untreated",
    )
    wounds = [w for w in character.wounds if w.wound_id != wound.wound_id]
    wounds.append(wound)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"wounds": wounds}),
        }
    )


def _wound_changed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    wound_id = str(event.payload["wound_id"])
    severity = str(event.payload.get("severity"))
    treatment = str(event.payload.get("treatment_state"))
    wounds = []
    for wound in character.wounds:
        if wound.wound_id == wound_id:
            wounds.append(wound.model_copy(update={"severity": severity, "treatment_state": treatment}))
        else:
            wounds.append(wound)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"wounds": wounds}),
        }
    )


def _vocation_started(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    from noosphere40k.domain.models import VocationPeriod

    vocation = VocationPeriod(
        vocation_id=str(event.payload["vocation_id"]),
        started_event_id=event.event_id,
        organization_id=event.payload.get("organization_id"),
    )
    history = list(character.vocation_history) + [vocation]
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"vocation_history": history}),
        }
    )


def _vocation_ended(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    vocation_id = str(event.payload["vocation_id"])
    history = []
    for vocation in character.vocation_history:
        if vocation.vocation_id == vocation_id and vocation.ended_event_id is None:
            history.append(vocation.model_copy(update={"ended_event_id": event.event_id}))
        else:
            history.append(vocation)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"vocation_history": history}),
        }
    )


def _goal_added(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    from noosphere40k.domain.models import Goal

    goal = Goal(
        goal_id=str(event.payload["goal_id"]),
        description=str(event.payload.get("description", "")),
        status="active",
        created_event_id=event.event_id,
    )
    goals = [g for g in character.goals if g.goal_id != goal.goal_id] + [goal]
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"goals": goals}),
        }
    )


def _goal_updated(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    goal_id = str(event.payload["goal_id"])
    status = str(event.payload.get("status", character.life_stage))
    goals = []
    for goal in character.goals:
        if goal.goal_id == goal_id:
            goals.append(goal.model_copy(update={"status": status}))
        else:
            goals.append(goal)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"goals": goals}),
        }
    )


def _life_stage_changed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    stage = event.payload.get("life_stage", character.life_stage)
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"life_stage": stage}),
        }
    )


def _attribute_changed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    key = str(event.payload["attribute_id"])
    value = cast(int, event.payload["value"])
    attributes = dict(character.attributes)
    attributes[key] = value
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"attributes": attributes}),
        }
    )


def _resource_changed(state: GameState, event: EventEnvelope) -> GameState:
    character = state.character
    if character is None:
        return state.model_copy(update={"sequence": event.sequence})
    key = str(event.payload["resource_id"])
    delta = cast(int, event.payload["delta"])
    resources = dict(character.resources)
    resources[key] = resources.get(key, 0) + delta
    return state.model_copy(
        update={
            "sequence": event.sequence,
            "character": character.model_copy(update={"resources": resources}),
        }
    )


def _relationship_changed(state: GameState, event: EventEnvelope) -> GameState:
    rel_id = str(event.payload["relationship_id"])
    axis = str(event.payload["axis"])
    delta = cast(int, event.payload["delta"])
    relationships = dict(state.relationships)
    rel = relationships.get(rel_id)
    if rel is not None:
        relationships[rel_id] = rel.model_copy(update={axis: rel.model_dump()[axis] + delta})
    return state.model_copy(update={"sequence": event.sequence, "relationships": relationships})


def _campaign_terminated(state: GameState, event: EventEnvelope) -> GameState:
    return state.model_copy(update={"sequence": event.sequence, "status": "terminal"})


def _character_died(state: GameState, event: EventEnvelope) -> GameState:
    return state.model_copy(update={"sequence": event.sequence, "status": "terminal"})


def _noop(state: GameState, event: EventEnvelope) -> GameState:
    return state.model_copy(update={"sequence": event.sequence})


REDUCERS: dict[EventType, Reducer] = {
    EventType.CAMPAIGN_CREATED: _created,
    EventType.TIME_ADVANCED: _time_advanced,
    EventType.LIFE_STAGE_CHANGED: _life_stage_changed,
    EventType.ATTRIBUTE_CHANGED: _attribute_changed,
    EventType.RESOURCE_CHANGED: _resource_changed,
    EventType.RELATIONSHIP_CHANGED: _relationship_changed,
    EventType.CHARACTER_DIED: _character_died,
    EventType.CAMPAIGN_TERMINATED: _campaign_terminated,
    EventType.SKILL_PROGRESSED: _skill_progressed,
    EventType.CONDITION_APPLIED: _condition_applied,
    EventType.CONDITION_REMOVED: _condition_removed,
    EventType.WOUND_APPLIED: _wound_applied,
    EventType.WOUND_CHANGED: _wound_changed,
    EventType.VOCATION_STARTED: _vocation_started,
    EventType.VOCATION_ENDED: _vocation_ended,
    EventType.GOAL_ADDED: _goal_added,
    EventType.GOAL_UPDATED: _goal_updated,
    EventType.SNAPSHOT_CREATED: _noop,
    EventType.RANDOM_DRAWN: _noop,
    EventType.CHECK_RESOLVED: _noop,
    EventType.NARRATION_RECORDED: _noop,
    EventType.PLAYER_INPUT_ACCEPTED: _noop,
    EventType.ACTION_INTENT_RESOLVED: _noop,
    EventType.TRAIT_ADDED: _noop,
    EventType.TRAIT_REMOVED: _noop,
    EventType.INVENTORY_ADDED: _noop,
    EventType.INVENTORY_REMOVED: _noop,
    EventType.KNOWLEDGE_CHANGED: _noop,
    EventType.ENCYCLOPEDIA_UNLOCKED: _noop,
    EventType.GOAL_COMPLETED: _noop,
    EventType.LOCATION_CHANGED: _noop,
    EventType.NPC_INTRODUCED: _noop,
    EventType.NPC_PROFILE_FROZEN: _noop,
    EventType.SCENE_STARTED: _noop,
    EventType.SCENE_COMPLETED: _noop,
    EventType.LORE_CLAIM_USED: _noop,
}


def reduce_event(state: GameState, event: EventEnvelope) -> GameState:
    """Pure reducer returning the next state.

    Rejects unknown event types, mismatched schema versions and out-of-order
    sequences. The prior state hash is verified to detect tampering or stale
    commits. Sequence 1 must be CampaignCreated.
    """
    if event.schema_version != EVENT_SCHEMA_VERSION:
        raise UnknownEventError(f"unsupported event schema version: {event.schema_version}")
    if event.prior_state_hash and event.prior_state_hash != state.state_hash:
        raise UnknownEventError(
            f"prior state hash mismatch: event={event.prior_state_hash[:12]} state={state.state_hash[:12]}"
        )
    handler = REDUCERS.get(event.type_enum)
    if handler is None:
        raise UnknownEventError(f"no reducer for event type: {event.event_type}")
    if event.sequence == 1 and event.type_enum != EventType.CAMPAIGN_CREATED:
        raise UnknownEventError("sequence 1 must be CampaignCreated")
    expected = state.sequence + 1
    if event.sequence != expected:
        raise UnknownEventError(f"sequence mismatch: expected {expected}, got {event.sequence}")
    next_state = handler(state, event)
    return next_state.model_copy(update={"state_hash": compute_state_hash(next_state)})