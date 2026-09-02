"""LLM narration service (E-05/E-06 wired into the game loop).

Builds a NarrationRequest from only the visible state + allowed facts, calls
the narrator, validates the response (one repair, then template fallback),
and returns either the validated narration or None (caller falls back to the
scene template). Never submits events; narration is display-only.
"""

from __future__ import annotations

from noosphere40k.content.schemas import SceneDefinition
from noosphere40k.domain.models import GameState
from noosphere40k.llm.base import LLMProvider, Message
from noosphere40k.llm.context_builder import NarrationContextBuilder
from noosphere40k.llm.output_guard import OutputGuard
from noosphere40k.llm.schemas import (
    ActionIntent,
    NarrationRequest,
    NarrationResponse,
)
from noosphere40k.lore.retrieval import LoreRepository

NARRATOR_PROMPT_VERSION = "narrator-0.1.0"

SYSTEM_PROMPT = (
    "你是一个受约束的中文叙事器，服务于《诺斯菲尔纪事》终端文字游戏。"
    "只描述当前场景与角色可见的状态，不生成新的世界观事实，不更改骰点、"
    "伤势、物品、年龄、关系或时间。可以基于角色的处境给出 3 个以内的建议行动。"
    "严格输出 NarrationResponse JSON。"
)


class NarrationService:
    def __init__(
        self,
        provider: LLMProvider,
        lore: LoreRepository,
        *,
        narration_length: str = "standard",
        tutorial_level: str = "standard",
        max_suggested_actions: int = 3,
    ) -> None:
        self.provider = provider
        self.builder = NarrationContextBuilder(
            lore,
            narration_length=narration_length,
            tutorial_level=tutorial_level,
            max_suggested_actions=max_suggested_actions,
        )
        self.guard = OutputGuard(provider)

    async def narrate(
        self,
        *,
        state: GameState,
        scene: SceneDefinition,
        player_input: str,
        trace_id: str,
        turn_number: int,
    ) -> str | None:
        request = self._build_request(state, scene, player_input, trace_id, turn_number)
        try:
            draft = await self.provider.generate_structured(
                messages=[
                    Message(role="system", content=SYSTEM_PROMPT),
                    Message(role="user", content=self._user_prompt(scene, player_input)),
                ],
                response_model=NarrationResponse,
                timeout_seconds=30.0,
                request_metadata={"prompt_version": NARRATOR_PROMPT_VERSION, "trace_id": trace_id},
            )
        except Exception:  # noqa: BLE001 - provider failure falls back to template
            return None
        assert isinstance(draft, NarrationResponse)
        outcome = await self.guard.validate_and_repair(request, draft)
        if outcome.fell_back_to_template or outcome.response is None:
            return None
        return outcome.response.narration

    def _build_request(
        self,
        state: GameState,
        scene: SceneDefinition,
        player_input: str,
        trace_id: str,
        turn_number: int,
    ) -> NarrationRequest:
        character = state.character
        if character is None:
            raise ValueError("cannot narrate without a player character")
        intent = ActionIntent(
            intent_id=f"intent-{trace_id}",
            actor_id=character.character_id,
            action_type="custom",
            free_text_summary=player_input[:200],
        )
        request = self.builder.build(
            state=state,
            player_input=player_input,
            trace_id=trace_id,
            turn_number=turn_number,
            scene_id=scene.scene_id,
            scene_title=scene.title,
            location_display=scene.location_id,
            allowed_fact_ids=[],
            allowed_original_entity_ids=[scene.location_id, character.origin_id],
        )
        return request.model_copy(update={"action_intent": intent})

    @staticmethod
    def _user_prompt(scene: SceneDefinition, player_input: str) -> str:
        parts = [f"场景：{scene.title}（{scene.location_id}）"]
        if player_input.strip():
            parts.append(f"玩家行动：{player_input}")
        return "\n".join(parts)


__all__ = ["NarrationService", "NARRATOR_PROMPT_VERSION"]