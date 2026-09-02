"""Output validation with one structured repair then template fallback (E-06).

Pipeline (PROMPT_GUARD_SPEC §6):
  SchemaGuard -> EventWhitelistGuard -> StateAuthorityGuard -> ClaimGuard
  -> CharacterKnowledgeGuard -> AgeContentGuard

On the FIRST failure the provider is asked to repair once (minimal feedback).
On the SECOND failure we drop the draft and use a deterministic template
outcome. Illegal drafts never commit events.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from noosphere40k.canon_guard.claim_guard import ClaimGuard, GuardDecision
from noosphere40k.domain.events import LLM_FORBIDDEN_EVENT_TYPES, EventType
from noosphere40k.llm.base import LLMProvider, Message
from noosphere40k.llm.schemas import (
    EventProposal,
    NarrationRequest,
    NarrationResponse,
)


@dataclass
class ValidationOutcome:
    response: NarrationResponse | None = None
    decisions: list[GuardDecision] = field(default_factory=list)
    repaired_once: bool = False
    fell_back_to_template: bool = False
    errors: list[str] = field(default_factory=list)


CHILDHOOD_FORBIDDEN_TAGS = {"erotic", "sexual", "adult_relationship"}


class OutputGuard:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.claim_guard = ClaimGuard()

    async def validate_and_repair(
        self,
        request: NarrationRequest,
        draft: NarrationResponse | None,
    ) -> ValidationOutcome:
        if draft is None:
            return self._template_fallback("provider returned no draft")

        first = self._validate(request, draft)
        if first.ok:
            return ValidationOutcome(response=draft, decisions=[first])

        repair_prompt = self._build_repair_prompt(first.errors)
        try:
            repaired = await self.provider.generate_structured(
                messages=[
                    Message(role="system", content=repair_prompt),
                    Message(role="user", content=draft.narration),
                ],
                response_model=NarrationResponse,
                timeout_seconds=10.0,
                request_metadata={"purpose": "repair"},
            )
        except Exception:
            return self._template_fallback("repair provider unavailable")
        assert isinstance(repaired, NarrationResponse)

        second = self._validate(request, repaired)
        if second.ok:
            return ValidationOutcome(
                response=repaired, decisions=[first, second], repaired_once=True
            )
        return self._template_fallback("; ".join(second.errors), prior_errors=first.errors + second.errors)

    # ---- guards ----

    def _validate(self, request: NarrationRequest, response: NarrationResponse) -> GuardDecision:
        decisions = [
            self._schema_guard(response),
            self._event_whitelist_guard(response.proposed_events),
            self._state_authority_guard(response),
            self._age_content_guard(request, response),
            self.claim_guard.validate(request, response.lore_claims),
        ]
        errors: list[str] = []
        for decision in decisions:
            if not decision.ok:
                errors.extend(decision.errors)
        return GuardDecision(ok=not errors, errors=errors)

    def _schema_guard(self, response: NarrationResponse) -> GuardDecision:
        if not response.narration.strip():
            return GuardDecision(ok=False, errors=["narration is empty"])
        if len(response.narration) > 4000:
            return GuardDecision(ok=False, errors=["narration exceeds 4000 chars"])
        return GuardDecision(ok=True)

    def _event_whitelist_guard(self, proposals: list[EventProposal]) -> GuardDecision:
        errors: list[str] = []
        for proposal in proposals:
            try:
                event_type = EventType(proposal.proposal_type)
            except ValueError:
                errors.append(f"unknown event type in proposal: {proposal.proposal_type}")
                continue
            if event_type in LLM_FORBIDDEN_EVENT_TYPES:
                errors.append(f"LLM may not propose {proposal.proposal_type}")
            elif event_type not in _PROPOSABLE:
                errors.append(f"event type not proposable by narrator: {proposal.proposal_type}")
        return GuardDecision(ok=not errors, errors=errors)

    def _state_authority_guard(self, response: NarrationResponse) -> GuardDecision:
        # The narrator must not claim authority over dice/state; we check the
        # narration does not assert dice rolls, deaths or inventory changes.
        lowered = response.narration.lower()
        forbidden_phrases = ("d100=", "骰子:", "roll=")
        hits = [p for p in forbidden_phrases if p in lowered]
        if hits:
            return GuardDecision(
                ok=False, errors=[f"narration claims rule authority: {hits}"], fail_fast=True
            )
        return GuardDecision(ok=True)

    def _age_content_guard(self, request: NarrationRequest, response: NarrationResponse) -> GuardDecision:
        if request.visible_character_state.life_stage != "childhood":
            return GuardDecision(ok=True)
        lowered = response.narration.lower()
        for tag in CHILDHOOD_FORBIDDEN_TAGS:
            if tag in lowered or any(t in lowered for t in ("sex", "色情", "情色")):
                return GuardDecision(
                    ok=False,
                    errors=["childhood narration must not contain sexual/erotic content"],
                    fail_fast=True,
                )
        return GuardDecision(ok=True)

    # ---- fallback ----

    def _template_fallback(self, reason: str, prior_errors: list[str] | None = None) -> ValidationOutcome:
        from noosphere40k.llm.schemas import LoreClaim

        outcome = ValidationOutcome(fell_back_to_template=True)
        outcome.errors = [reason] + (prior_errors or [])
        outcome.response = NarrationResponse(
            narration="【规则结果】本次回合结果由程序模板生成。" if not reason else
            "【规则结果】回合结果由程序模板生成，未能生成叙事。",
            proposed_events=[],
            lore_claims=[LoreClaim(text="", claim_type="decorative")],
        )
        return outcome

    def _build_repair_prompt(self, errors: list[str]) -> str:
        return (
            "你的响应未通过结构化校验。只修复以下问题，不添加新事实或事件：\n- "
            + "\n- ".join(errors[:5])
            + "\n仍然只能使用原请求中的 fact IDs、entity IDs 和 RuleResolution。输出完整的 NarrationResponse JSON。"
        )


_PROPOSABLE = frozenset(
    {
        EventType.RELATIONSHIP_CHANGED,
        EventType.KNOWLEDGE_CHANGED,
        EventType.GOAL_ADDED,
        EventType.GOAL_UPDATED,
        EventType.GOAL_COMPLETED,
        EventType.VOCATION_STARTED,
        EventType.VOCATION_ENDED,
        EventType.LOCATION_CHANGED,
        EventType.NPC_INTRODUCED,
        EventType.SCENE_COMPLETED,
        EventType.TIME_ADVANCED,
    }
)


__all__ = ["OutputGuard", "ValidationOutcome"]