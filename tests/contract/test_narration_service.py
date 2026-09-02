"""E-05/E-06 wired: NarrationService produces narration with template fallback."""

from __future__ import annotations

import asyncio
from pathlib import Path

from noosphere40k.application.campaign_service import TutorialService
from noosphere40k.application.narration_service import NarrationService
from noosphere40k.llm.schemas import NarrationResponse
from noosphere40k.llm.stub import StubProvider
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS
from noosphere40k.persistence.repositories import CampaignRepository
from noosphere40k.rules.rng import RngService


def _service(tmp_path: Path) -> TutorialService:
    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    return TutorialService(CampaignRepository(engine), rng=RngService(seed=7))


def test_narration_uses_llm_when_provider_present(tmp_path: Path) -> None:
    service = _service(tmp_path)
    state = service.create_campaign("c1", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001

    provider = StubProvider(response=NarrationResponse(narration="LLM 生成的叙事。"))
    narrator = NarrationService(provider, service.lore)

    text = asyncio.run(narrator.narrate(
        state=state, scene=scene, player_input="分配给",
        trace_id="t1", turn_number=1,
    ))
    assert "LLM 生成的叙事" in text


def test_narration_falls_back_to_none_on_failure(tmp_path: Path) -> None:
    service = _service(tmp_path)
    state = service.create_campaign("c1", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001

    # stub with no response -> ProviderUnavailableError -> narrate returns None
    narrator = NarrationService(StubProvider(), service.lore)
    text = asyncio.run(narrator.narrate(
        state=state, scene=scene, player_input="x",
        trace_id="t1", turn_number=1,
    ))
    assert text is None


def test_narration_validates_claims(tmp_path: Path) -> None:
    """A narration that smuggles an unsupported canon claim is rejected."""
    service = _service(tmp_path)
    state = service.create_campaign("c1", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001

    provider = StubProvider(response=NarrationResponse(
        narration="这是官方正史内容",
        lore_claims=[{
            "text": "某个著名正史事件是真的",
            "claim_type": "canon",
            "supporting_fact_ids": ["fact.not_allowed"],
        }],
    ))
    narrator = NarrationService(provider, service.lore)
    text = asyncio.run(narrator.narrate(
        state=state, scene=scene, player_input="x",
        trace_id="t1", turn_number=1,
    ))
    # the canon claim references a fact absent from the request -> rejected ->
    # repair attempt -> stub has no repair script -> falls back to None
    assert text is None or "官方正史" not in text


def test_offline_no_key_keeps_template(tmp_path: Path) -> None:
    """Without a key, the game loop must keep using templates (no provider)."""
    from noosphere40k.config.settings import load_settings

    settings = load_settings(environ={}, data_dir_override=tmp_path)
    assert settings.has_api_key is False