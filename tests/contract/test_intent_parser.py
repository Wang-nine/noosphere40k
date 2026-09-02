"""E-04: intent parser — meta commands, low-confidence clarification."""

from __future__ import annotations

from noosphere40k.llm.intent import IntentParser
from noosphere40k.llm.schemas import ActionIntent, IntentParseResult
from noosphere40k.llm.stub import StubProvider


async def test_meta_command_never_calls_provider() -> None:
    provider = StubProvider(response=IntentParseResult(
        intent=ActionIntent(
            intent_id="i", actor_id="pc", action_type="attack",
            free_text_summary="x", parser_confidence_basis_points=1000,
        )
    ))
    parser = IntentParser(provider, controllable_actor_id="pc")
    result = await parser.parse("/quit")
    assert result.is_meta_command is True
    assert result.meta_command == "/quit"
    assert provider.request_count == 0  # provider never invoked


async def test_meta_command_splitter() -> None:
    parser = IntentParser(StubProvider(), controllable_actor_id="pc")
    is_meta, command = parser.split_meta("  /save  mygame ")
    assert is_meta is True
    assert command == "/save"


async def test_actor_must_be_controllable() -> None:
    provider = StubProvider(response=IntentParseResult(
        intent=ActionIntent(
            intent_id="i", actor_id="npc_evil", action_type="attack",
            free_text_summary="x", parser_confidence_basis_points=900,
        )
    ))
    parser = IntentParser(provider, controllable_actor_id="pc")
    result = await parser.parse("攻击他")
    assert result.clarification_prompt is not None


async def test_low_confidence_attack_requires_clarification() -> None:
    provider = StubProvider(response=IntentParseResult(
        intent=ActionIntent(
            intent_id="i", actor_id="pc", action_type="attack",
            free_text_summary="打", parser_confidence_basis_points=300,
        )
    ))
    parser = IntentParser(provider, controllable_actor_id="pc")
    result = await parser.parse("打他")
    assert result.clarification_prompt is not None
    assert "不可逆" in result.clarification_prompt


async def test_high_confidence_attack_allowed() -> None:
    provider = StubProvider(response=IntentParseResult(
        intent=ActionIntent(
            intent_id="i", actor_id="pc", action_type="attack",
            free_text_summary="打他", parser_confidence_basis_points=900,
            target_ids=["npc.thug"],
        )
    ))
    parser = IntentParser(provider, controllable_actor_id="pc")
    result = await parser.parse("攻击那个暴徒")
    assert result.intent is not None
    assert result.clarification_prompt is None


async def test_unresolved_references_clarify() -> None:
    provider = StubProvider(response=IntentParseResult(
        intent=ActionIntent(
            intent_id="i", actor_id="pc", action_type="use_item",
            free_text_summary="用道具", parser_confidence_basis_points=800,
            unresolved_references=["道具目标"],
        )
    ))
    parser = IntentParser(provider, controllable_actor_id="pc")
    result = await parser.parse("用道具")
    assert result.clarification_prompt is not None
    assert "道具目标" in result.clarification_prompt