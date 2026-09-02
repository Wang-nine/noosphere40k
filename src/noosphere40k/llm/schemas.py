"""LLM protocol schemas (DATA_PROTOCOL_SPEC §9–§12, §20; E-03).

NarrationRequest carries only the minimum context needed for narration;
NarrationResponse is the only shape the narrator may emit. Every model is
strict (extra fields forbidden) and validated before entering the pipeline.
"""

from __future__ import annotations

from pydantic import Field

from noosphere40k.domain.enums import ActionType, ClaimType
from noosphere40k.domain.models import StrictModel
from noosphere40k.rules.checks import CheckResult, Modifier

# ---- §9 ActionIntent ----


class ActionIntent(StrictModel):
    intent_id: str
    actor_id: str
    action_type: ActionType
    target_ids: list[str] = Field(default_factory=list)
    free_text_summary: str
    declared_goal: str | None = None
    proposed_method: str | None = None
    requested_meta_command: str | None = None
    parser_confidence_basis_points: int = 500
    unresolved_references: list[str] = Field(default_factory=list)


# ---- §10 RuleResolution ----


class RuleResolution(StrictModel):
    checks: list[CheckResult] = Field(default_factory=list)
    deterministic_events: list[EventProposal] = Field(default_factory=list)
    narration_constraints: list[str] = Field(default_factory=list)
    hidden_information_refs: list[str] = Field(default_factory=list)


# ---- §20 display / prompt models ----


class VisibleScene(StrictModel):
    scene_id: str
    title: str
    location_display: str
    visible_character_ids: list[str] = Field(default_factory=list)
    visible_objects: list[str] = Field(default_factory=list)
    active_objectives: list[str] = Field(default_factory=list)
    immediate_pressures: list[str] = Field(default_factory=list)


class VisibleCharacterState(StrictModel):
    display_name: str
    displayed_age: str
    life_stage: str
    visible_conditions: list[str] = Field(default_factory=list)
    visible_resources: dict[str, int] = Field(default_factory=dict)
    role_summary: str


class VisibleRelationship(StrictModel):
    character_id: str
    display_name: str
    player_known_summary: str


class PromptFact(StrictModel):
    fact_id: str
    statement: str
    viewpoint: str
    allowed_usage: str = "objective"
    source_ref_ids: list[str] = Field(default_factory=list)


class TutorialHint(StrictModel):
    term_id: str
    level: str = "beginner"
    text: str
    player_layer: bool = True


class NarrationStyle(StrictModel):
    language: str = "zh-CN"
    length: str = "standard"
    tutorial_level: str = "standard"
    max_suggested_actions: int = 5


# ---- §11 NarrationRequest ----


class NarrationRequest(StrictModel):
    trace_id: str
    campaign_id: str
    turn_number: int
    player_input: str
    action_intent: ActionIntent | None = None
    visible_scene: VisibleScene
    visible_character_state: VisibleCharacterState
    visible_relationships: list[VisibleRelationship] = Field(default_factory=list)
    allowed_lore_facts: list[PromptFact] = Field(default_factory=list)
    allowed_original_entity_ids: list[str] = Field(default_factory=list)
    forbidden_claim_topics: list[str] = Field(default_factory=list)
    rule_resolution: RuleResolution = Field(default_factory=RuleResolution)
    tutorial_payload: list[TutorialHint] = Field(default_factory=list)
    style_settings: NarrationStyle = Field(default_factory=NarrationStyle)
    content_limits: set[str] = Field(default_factory=set)


# ---- §12 NarrationResponse ----


class DialogueLine(StrictModel):
    speaker_id: str
    text: str
    tone: str | None = None


class SuggestedAction(StrictModel):
    action_type: ActionType
    target_ids: list[str] = Field(default_factory=list)
    label: str
    risk_label: str | None = None
    free_text: str = ""


class EventProposal(StrictModel):
    proposal_type: str
    target_id: str | None = None
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    reason: str = ""
    supporting_event_ids: list[str] = Field(default_factory=list)
    supporting_fact_ids: list[str] = Field(default_factory=list)


class LoreClaim(StrictModel):
    text: str
    claim_type: ClaimType
    supporting_fact_ids: list[str] = Field(default_factory=list)
    supporting_entity_ids: list[str] = Field(default_factory=list)


class NarrativeUncertainty(StrictModel):
    text: str
    topic: str
    severity: str = "low"


class NarrationResponse(StrictModel):
    narration: str
    dialogue: list[DialogueLine] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    proposed_events: list[EventProposal] = Field(default_factory=list)
    lore_claims: list[LoreClaim] = Field(default_factory=list)
    glossary_term_ids: list[str] = Field(default_factory=list)
    uncertainties: list[NarrativeUncertainty] = Field(default_factory=list)


# Whitelisted event types the LLM may propose (EventWhitelistGuard).
LLM_PROPOSABLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "RelationshipChanged",
        "KnowledgeChanged",
        "GoalAdded",
        "GoalUpdated",
        "GoalCompleted",
        "VocationStarted",
        "VocationEnded",
        "LocationChanged",
        "NPCIntroduced",
        "SceneCompleted",
        "TimeAdvanced",
    }
)


class IntentParseResult(StrictModel):
    """E-04: parser output — either a resolved intent or a clarification."""

    intent: ActionIntent | None = None
    clarification_prompt: str | None = None
    unresolved_references: list[str] = Field(default_factory=list)
    confidence_basis_points: int = 0
    is_meta_command: bool = False
    meta_command: str | None = None


__all__ = [
    "ActionIntent",
    "RuleResolution",
    "VisibleScene",
    "VisibleCharacterState",
    "VisibleRelationship",
    "PromptFact",
    "TutorialHint",
    "NarrationStyle",
    "NarrationRequest",
    "DialogueLine",
    "SuggestedAction",
    "EventProposal",
    "LoreClaim",
    "NarrativeUncertainty",
    "NarrationResponse",
    "IntentParseResult",
    "LLM_PROPOSABLE_EVENT_TYPES",
    "Modifier",
    "CheckResult",
]