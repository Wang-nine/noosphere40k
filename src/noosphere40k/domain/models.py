"""Stable domain support models (DATA_PROTOCOL_SPEC §2, §4, §5, §7, §18; C-01).

Contract models only: no CLI, no database, no vendor SDK imports.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldTime(StrictModel):
    era_id: str
    local_calendar_id: str
    local_year: int | None = None
    local_day: int | None = None
    local_second: int | None = None
    ordering_key: int
    precision: str
    uncertainty_note: str | None = None


class PackLock(StrictModel):
    pack_id: str
    version: str
    content_hash: str


class Membership(StrictModel):
    faction_id: str
    role_id: str
    rank_id: str | None = None
    started_event_id: str
    ended_event_id: str | None = None


class VocationPeriod(StrictModel):
    vocation_id: str
    started_event_id: str
    ended_event_id: str | None = None
    organization_id: str | None = None
    outcome_tags: set[str] = Field(default_factory=set)


class Condition(StrictModel):
    condition_id: str
    severity: int
    applied_event_id: str
    expires_world_time: WorldTime | None = None


class Wound(StrictModel):
    wound_id: str
    location: str
    severity: str
    cause_event_id: str
    treatment_state: str


class InventoryEntry(StrictModel):
    instance_id: str
    item_template_id: str
    quantity: int = 1
    condition: int = 100
    provenance_event_id: str


class Belief(StrictModel):
    belief_id: str
    statement: str
    strength: int = 0
    origin_event_id: str


class Goal(StrictModel):
    goal_id: str
    description: str
    status: str
    created_event_id: str


class LegacyState(StrictModel):
    successor_character_ids: list[str] = Field(default_factory=list)
    entrusted_item_ids: list[str] = Field(default_factory=list)
    entrusted_fact_ids: list[str] = Field(default_factory=list)
    reputation_tags: set[str] = Field(default_factory=set)
    terminal_summary_id: str | None = None


class AgeState(StrictModel):
    chronological_age_days: int
    subjective_age_days: int
    life_stage: str


class LocalizedAlias(StrictModel):
    language: str
    text: str
    alias_type: str


class CampaignSeed(StrictModel):
    era_id: str
    region_id: str
    faction_id: str
    origin_template_id: str
    start_age: int = 8
    lifepath_mode: str = "full_life"
    themes: list[str] = Field(default_factory=list)
    tone: str = "balanced"
    power_scale: str = "human"
    opening_hook_id: str
    canon_validation: str = "passed"
    validation_evidence: list[str] = Field(default_factory=list)


class CampaignSettings(StrictModel):
    tutorial_level: str = "standard"
    narration_length: str = "standard"
    graphic_violence: str = "moderate"
    combat_frequency: str = "standard"
    irreversible_death: bool = False
    spoiler_policy: str = "strict"
    cloud_private_source_access: bool = False
    max_cost_per_turn_minor: int | None = None
    disabled_content_tags: set[str] = Field(default_factory=set)


class Campaign(StrictModel):
    campaign_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    state_version: int = 0
    ruleset_version: str = "0.1.0"
    prompt_version: str
    schema_version: int = 1
    seed: CampaignSeed
    settings: CampaignSettings
    player_character_id: str
    installed_pack_locks: list[PackLock] = Field(default_factory=list)
    last_event_sequence: int = 0
    state_hash: str


class PlayerCharacter(StrictModel):
    character_id: str
    display_name: str
    pronouns: str | None = None
    birth_world_time: WorldTime
    chronological_age_days: int
    subjective_age_days: int
    life_stage: str
    origin_id: str
    guardian_ids: list[str] = Field(default_factory=list)
    household_id: str | None = None
    social_class_tags: set[str] = Field(default_factory=set)
    faction_memberships: list[Membership] = Field(default_factory=list)
    vocation_history: list[VocationPeriod] = Field(default_factory=list)
    attributes: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, dict[str, object]] = Field(default_factory=dict)
    traits: set[str] = Field(default_factory=set)
    conditions: list[Condition] = Field(default_factory=list)
    wounds: list[Wound] = Field(default_factory=list)
    inventory: list[InventoryEntry] = Field(default_factory=list)
    resources: dict[str, int] = Field(default_factory=dict)
    beliefs: list[Belief] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)
    knowledge_index_version: int = 0
    legacy: LegacyState = Field(default_factory=LegacyState)


class KnowledgeRecord(StrictModel):
    owner_character_id: str
    subject_id: str
    status: str
    reliability_basis_points: int = 0
    learned_at_event_id: str | None = None
    learned_from_character_id: str | None = None
    source_viewpoint: str | None = None
    superseded_by_event_id: str | None = None


class Relationship(StrictModel):
    relationship_id: str
    subject_id: str
    object_id: str
    type: str
    direction: str
    trust: int
    obligation: int
    suspicion: int
    hostility: int
    public_visibility: str
    valid_from_event_id: str
    valid_to_event_id: str | None = None
    evidence_event_ids: list[str] = Field(default_factory=list)
    origin: str


class GameState(StrictModel):
    """Aggregate state produced by the pure event reducer."""

    campaign_id: str = ""
    status: str = "creating"
    sequence: int = 0
    world_time: WorldTime | None = None
    character: PlayerCharacter | None = None
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    knowledge: dict[str, KnowledgeRecord] = Field(default_factory=dict)
    state_hash: str = ""