"""Stable domain enums (DATA_PROTOCOL_SPEC §1, §3.1, §6, §14; A-02).

Values are the public contract. Never change the meaning of a published
value; add new members instead. Python 3.11+ StrEnum keeps stable values.
"""

from enum import StrEnum


class CampaignStatus(StrEnum):
    CREATING = "creating"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINAL = "terminal"
    ARCHIVED = "archived"
    READ_ONLY = "read_only"


class LifeStage(StrEnum):
    CHILDHOOD = "childhood"
    ADOLESCENCE = "adolescence"
    YOUTH = "youth"
    ADULTHOOD = "adulthood"
    LATE_LIFE = "late_life"
    TERMINAL = "terminal"


class AttributeId(StrEnum):
    MELEE = "melee"
    RANGED = "ranged"
    BODY = "body"
    AGILITY = "agility"
    INTELLECT = "intellect"
    AWARENESS = "awareness"
    WILLPOWER = "willpower"
    PRESENCE = "presence"


class SkillRank(StrEnum):
    UNTRAINED = "untrained"
    TRAINED = "trained"
    SPECIALIST = "specialist"
    MASTER = "master"


class FactType(StrEnum):
    CANON_EDITORIAL = "canon_editorial"
    CANON_PERSPECTIVE = "canon_perspective"
    LICENSED_DERIVED = "licensed_derived"
    DISPUTED = "disputed"
    GAME_ORIGINAL = "game_original"
    CAMPAIGN_EVENT = "campaign_event"
    INFERENCE = "inference"


class SourceClass(StrEnum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    B = "B"


class SourceViewpoint(StrEnum):
    EDITORIAL = "editorial"
    IN_UNIVERSE = "in_universe"
    CHARACTER_LIMITED = "character_limited"


class ReviewStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ConfidenceLevel(StrEnum):
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    PERSPECTIVE_ONLY = "perspective_only"


class EntityOrigin(StrEnum):
    CANON = "canon"
    LICENSED = "licensed"
    GAME_ORIGINAL = "game_original"


class EventOrigin(StrEnum):
    PLAYER = "player"
    RULES = "rules"
    CONTENT = "content"
    LLM_VALIDATED = "llm_validated"
    SYSTEM = "system"


class ErrorCode(StrEnum):
    E_CONFIG_INVALID = "E_CONFIG_INVALID"
    E_PROVIDER_UNAVAILABLE = "E_PROVIDER_UNAVAILABLE"
    E_PROVIDER_TIMEOUT = "E_PROVIDER_TIMEOUT"
    E_PROVIDER_SCHEMA = "E_PROVIDER_SCHEMA"
    E_LORE_UNCOVERED = "E_LORE_UNCOVERED"
    E_LORE_CONFLICT = "E_LORE_CONFLICT"
    E_CANON_VIOLATION = "E_CANON_VIOLATION"
    E_RULE_INVALID_ACTION = "E_RULE_INVALID_ACTION"
    E_SAVE_CONFLICT = "E_SAVE_CONFLICT"
    E_SAVE_CORRUPT = "E_SAVE_CORRUPT"
    E_CONTENT_MISSING = "E_CONTENT_MISSING"
    E_MIGRATION_FAILED = "E_MIGRATION_FAILED"
    E_UNKNOWN_EVENT = "E_UNKNOWN_EVENT"