"""Intent Parser (PROMPT_GUARD_SPEC §2, E-04).

Parses player natural language into an ActionIntent using the LLM provider
(or an offline stub), then applies programmatic validation:

- meta commands never reach the LLM (handled before parsing),
- actor must be a controllable character,
- low-confidence attacks, resource consumption and irreversible actions
  require clarification instead of guessing,
- unresolved references are surfaced as clarifications.
"""

from __future__ import annotations

from noosphere40k.llm.base import LLMProvider, Message, ProviderHealth
from noosphere40k.llm.schemas import ActionIntent, IntentParseResult

IRREVERSIBLE_ACTION_TYPES = {"attack", "use_item"}

LOW_CONFIDENCE_THRESHOLD = 600  # below this, clarify when irreversible


class IntentParser:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        controllable_actor_id: str,
        prompt_version: str = "intent-0.1.0",
    ) -> None:
        self.provider = provider
        self.controllable_actor_id = controllable_actor_id
        self.prompt_version = prompt_version

    @staticmethod
    def is_meta_command(raw: str) -> bool:
        return raw.strip().startswith("/")

    def split_meta(self, raw: str) -> tuple[bool, str | None]:
        """Return (is_meta, meta_command). Meta commands never go to the LLM."""
        stripped = raw.strip()
        if stripped.startswith("/"):
            command = stripped.split()[0].lower()
            return True, command
        return False, None

    async def parse(self, raw: str) -> IntentParseResult:
        is_meta, meta_command = self.split_meta(raw)
        if is_meta:
            return IntentParseResult(
                is_meta_command=True,
                meta_command=meta_command,
                confidence_basis_points=1000,
            )

        result = await self._call_parser(raw)
        if result.clarification_prompt:
            return result
        intent = result.intent
        if intent is None:
            return result

        # programmatic validation
        validation_error = self._validate_intent(intent)
        if validation_error:
            return IntentParseResult(
                clarification_prompt=validation_error,
                unresolved_references=intent.unresolved_references,
                confidence_basis_points=intent.parser_confidence_basis_points,
            )
        return result

    async def _call_parser(self, raw: str) -> IntentParseResult:
        """Ask the provider (stub in offline mode) for a structured intent."""
        try:
            response = await self.provider.generate_structured(
                messages=[
                    Message(role="system", content=self._system_prompt()),
                    Message(role="user", content=raw),
                ],
                response_model=IntentParseResult,
                timeout_seconds=10.0,
                request_metadata={"prompt_version": self.prompt_version},
            )
        except Exception:
            # Offline / stub without a scripted response: fall back to
            # deterministic keyword parsing so the game stays playable.
            return self._keyword_fallback(raw)
        assert isinstance(response, IntentParseResult)
        return response

    def _validate_intent(self, intent: ActionIntent) -> str | None:
        if intent.actor_id != self.controllable_actor_id:
            return f"actor {intent.actor_id} is not the controllable character"
        if intent.unresolved_references:
            return "目标指代不明确：" + "、".join(intent.unresolved_references)
        if (intent.action_type.value in IRREVERSIBLE_ACTION_TYPES
                and intent.parser_confidence_basis_points < LOW_CONFIDENCE_THRESHOLD):
            return f"{intent.action_type.value} 是不可逆行动，请确认目标后再执行"
        return None

    def _keyword_fallback(self, raw: str) -> IntentParseResult:
        lowered = raw.strip().lower()
        action_type = "custom"
        if any(w in lowered for w in ("看", "观察", "look", "watch")):
            action_type = "observe"
        elif any(w in lowered for w in ("问", "询问", "ask")):
            action_type = "ask"
        elif any(w in lowered for w in ("攻击", "打", "attack", "kill")):
            action_type = "attack"
        intent = ActionIntent(
            intent_id="intent-offline",
            actor_id=self.controllable_actor_id,
            action_type=action_type,
            free_text_summary=raw.strip()[:200],
            parser_confidence_basis_points=400,
        )
        return IntentParseResult(intent=intent, confidence_basis_points=400)

    def _system_prompt(self) -> str:
        return (
            "你只把玩家输入解析为 ActionIntent。不要判断行动是否成功，不要掷骰，"
            "不要生成世界观事实，不要推进时间。只引用请求中列出的角色、物品、地点和动作类型。"
            "当攻击、资源消费、不可逆选择或目标指代不明确时，返回 unresolved_references，不能猜测。"
            "严格输出指定 JSON Schema。"
        )

    async def healthcheck(self) -> ProviderHealth:
        return await self.provider.healthcheck()


__all__ = ["IntentParser"]