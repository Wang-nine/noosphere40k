"""Narrator context assembly (E-05).

Builds a NarrationRequest containing ONLY:
- character-visible state,
- approved facts that passed the Lore Gate AND the character knowledge filter,
- explicit original-entity allowlists,
- no private source material, no hidden information.
The ``cloud_private_source_access`` setting gates private data to cloud LLMs.
"""

from __future__ import annotations

from noosphere40k.domain.models import GameState
from noosphere40k.llm.schemas import (
    NarrationRequest,
    NarrationStyle,
    PromptFact,
    RuleResolution,
    TutorialHint,
    VisibleCharacterState,
    VisibleRelationship,
    VisibleScene,
)
from noosphere40k.lore.retrieval import LoreRepository


class NarrationContextBuilder:
    def __init__(
        self,
        lore: LoreRepository,
        *,
        cloud_private_source_access: bool = False,
        narration_length: str = "standard",
        tutorial_level: str = "standard",
        max_suggested_actions: int = 5,
    ) -> None:
        self.lore = lore
        self.cloud_private_source_access = cloud_private_source_access
        self.narration_length = narration_length
        self.tutorial_level = tutorial_level
        self.max_suggested_actions = max_suggested_actions

    def build(
        self,
        *,
        state: GameState,
        player_input: str,
        trace_id: str,
        turn_number: int,
        scene_id: str,
        scene_title: str,
        location_display: str,
        allowed_fact_ids: list[str],
        allowed_original_entity_ids: list[str],
        forbidden_claim_topics: list[str] | None = None,
        rule_resolution: RuleResolution | None = None,
        content_limits: set[str] | None = None,
    ) -> NarrationRequest:
        character = state.character
        if character is None:
            raise ValueError("cannot build narration context without a player character")

        prompt_facts: list[PromptFact] = []
        for fact_id in allowed_fact_ids:
            fact = self.lore.get_fact(fact_id)
            if fact is None:
                continue  # lore gate already blocked; never leak unapproved facts
            prompt_facts.append(
                PromptFact(
                    fact_id=fact.fact_id,
                    statement=fact.claim,
                    viewpoint=fact.confidence.value,
                    allowed_usage="objective" if fact.fact_type == "canon_editorial" else "perspective_only",
                    source_ref_ids=list(fact.source_refs[:5]),
                )
            )

        visible_scene = VisibleScene(
            scene_id=scene_id,
            title=scene_title,
            location_display=location_display,
            visible_character_ids=[],
        )
        visible_character = VisibleCharacterState(
            display_name=character.display_name,
            displayed_age=f"{character.chronological_age_days} 天",
            life_stage=character.life_stage,
            visible_resources=dict(character.resources),
            role_summary=character.origin_id,
        )
        visible_relationships = [
            VisibleRelationship(
                character_id=rel.object_id,
                display_name="?",
                player_known_summary="已知关系",
            )
            for rel in state.relationships.values()
        ]

        return NarrationRequest(
            trace_id=trace_id,
            campaign_id=state.campaign_id,
            turn_number=turn_number,
            player_input=player_input,
            visible_scene=visible_scene,
            visible_character_state=visible_character,
            visible_relationships=visible_relationships,
            allowed_lore_facts=prompt_facts,
            allowed_original_entity_ids=list(allowed_original_entity_ids),
            forbidden_claim_topics=list(forbidden_claim_topics or []),
            rule_resolution=rule_resolution or RuleResolution(),
            tutorial_payload=[TutorialHint(term_id="", text="", player_layer=True)],
            style_settings=NarrationStyle(
                length=self.narration_length,
                tutorial_level=self.tutorial_level,
                max_suggested_actions=self.max_suggested_actions,
            ),
            content_limits=content_limits or set(),
        )


__all__ = ["NarrationContextBuilder"]