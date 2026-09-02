"""B-04/G-06: time-jump in the tutorial service — preview then confirm."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.application.campaign_service import TutorialService
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS
from noosphere40k.persistence.repositories import CampaignRepository
from noosphere40k.rules.rng import RngService


@pytest.fixture
def service(tmp_path: Path) -> TutorialService:
    engine = open_engine(tmp_path / "test.db")
    run_migrations(engine, MIGRATIONS)
    repo = CampaignRepository(engine)
    return TutorialService(repo, rng=RngService(seed=7))


def test_time_jump_preview_produces_zero_events(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    before = service.repo.latest_sequence("camp.t")
    preview = service.time_jump(campaign_id="camp.t", state=state, days=3650, confirm=False)
    assert "预览" in preview.narration
    assert service.repo.latest_sequence("camp.t") == before  # nothing committed


def test_time_jump_confirm_commits_and_advances_age(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    before = state.character.chronological_age_days
    service.time_jump(campaign_id="camp.t", state=state, days=3650, confirm=True)
    loaded = service.repo.load_consistent_snapshot("camp.t")
    assert loaded.character is not None
    assert loaded.character.chronological_age_days == before + 3650
    assert loaded.character.life_stage == "youth"  # 8y + 10y = 18y
    assert service.repo.latest_sequence("camp.t") > 3


def test_time_jump_commits_attribute_and_skill_changes(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    service.time_jump(
        campaign_id="camp.t", state=state, days=3650, focus_tags=["scholarship"], confirm=True
    )
    loaded = service.repo.load_consistent_snapshot("camp.t")
    assert loaded.character is not None
    # scholarship focus boosted intellect
    assert loaded.character.skills.get("scholarship", {}).get("rank") == "trained"
    assert loaded.character.attributes.get("intellect", 0) > state.character.attributes.get("intellect", 30)