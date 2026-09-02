"""Content schemas: scenes, transitions, predicates and lore requirements (F-01).

Models per DATA_PROTOCOL_SPEC §8 and §19. Content packs are data only; they
are validated by :mod:`noosphere40k.content.validator` and never execute code.
"""

from __future__ import annotations

from pydantic import Field

from noosphere40k.domain.models import StrictModel


class Predicate(StrictModel):
    predicate_type: str
    subject_id: str | None = None
    operator: str
    expected: object | None = None


class ParticipantSelector(StrictModel):
    slot_id: str
    required_tags: set[str] = Field(default_factory=set)
    preferred_character_ids: list[str] = Field(default_factory=list)
    create_from_template_id: str | None = None


class LoreRequirement(StrictModel):
    requirement_id: str
    fact_id: str | None = None
    topic_id: str | None = None
    purpose: str = ""
    minimum_source_class: str = "A1"
    hard: bool = False
    fallback_template_id: str | None = None


class LoreRequirementSet(StrictModel):
    hard: list[LoreRequirement] = Field(default_factory=list)
    optional: list[LoreRequirement] = Field(default_factory=list)
    forbidden_topics: set[str] = Field(default_factory=set)


class ObjectiveDefinition(StrictModel):
    objective_id: str
    display_text: str
    completion_predicates: list[Predicate] = Field(default_factory=list)
    failure_predicates: list[Predicate] = Field(default_factory=list)


class ActionTemplate(StrictModel):
    action_template_id: str
    display_text: str
    action_type: str
    target_selector: ParticipantSelector | None = None
    check_template_id: str | None = None
    content_tags: set[str] = Field(default_factory=set)


class TransitionRule(StrictModel):
    priority: int = 0
    predicates: list[Predicate] = Field(default_factory=list)
    next_scene_id: str | None = None
    terminal_outcome_id: str | None = None


class SceneDefinition(StrictModel):
    scene_id: str
    pack_id: str
    title: str
    allowed_life_stages: set[str] = Field(default_factory=set)
    entry_conditions: list[Predicate] = Field(default_factory=list)
    exit_conditions: list[Predicate] = Field(default_factory=list)
    location_id: str
    participant_selectors: list[ParticipantSelector] = Field(default_factory=list)
    lore_requirements: LoreRequirementSet = Field(default_factory=LoreRequirementSet)
    content_tags: set[str] = Field(default_factory=set)
    objectives: list[ObjectiveDefinition] = Field(default_factory=list)
    action_templates: list[ActionTemplate] = Field(default_factory=list)
    fallback_narration_template_id: str
    next_scene_rules: list[TransitionRule] = Field(default_factory=list)


class LifeTransitionDefinition(StrictModel):
    transition_id: str
    from_stage: str
    to_stage: str
    min_time_days: int = 0
    required_milestones: list[str] = Field(default_factory=list)
    choice_prompts: list[str] = Field(default_factory=list)
    aging_ruleset_id: str
    summary_template_id: str
    confirmation_required: bool = True


# --- fallback / narration template variables ---
SAFE_TEMPLATE_VARIABLES: frozenset[str] = frozenset(
    {
        "display_name",
        "location",
        "scene_title",
        "roll",
        "target",
        "success",
        "margin_degrees",
        "special",
    }
)


class NarrationTemplate(StrictModel):
    template_id: str
    pack_id: str
    text: str
    variables: set[str] = Field(default_factory=set)


class ScenePack(StrictModel):
    """A validated, loadable scenario pack (scenarios, transitions, templates)."""

    pack_id: str
    version: str
    schema_version: int = 1
    scenes: list[SceneDefinition] = Field(default_factory=list)
    transitions: list[LifeTransitionDefinition] = Field(default_factory=list)
    templates: list[NarrationTemplate] = Field(default_factory=list)
    dependency_pack_ids: list[str] = Field(default_factory=list)


__all__ = [
    "Predicate",
    "ParticipantSelector",
    "LoreRequirement",
    "LoreRequirementSet",
    "ObjectiveDefinition",
    "ActionTemplate",
    "TransitionRule",
    "SceneDefinition",
    "LifeTransitionDefinition",
    "NarrationTemplate",
    "ScenePack",
    "SAFE_TEMPLATE_VARIABLES",
]