"""F-02/G-02: offline tutorial campaign end-to-end (no LLM)."""

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


def test_create_campaign_builds_state(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    assert state.status == "active"
    assert state.character is not None
    assert state.character.display_name == "Ada"
    assert state.character.life_stage == "childhood"
    assert service.repo.latest_sequence("camp.t") == 2


def test_play_first_scene_by_index(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001
    playback = service.play_scene(
        campaign_id="camp.t", state=state, scene=scene, choice=1
    )
    assert playback.next_scene_id == "scene.tutorial.red_robed_visitor"
    assert playback.scene is not None
    assert playback.scene.scene_id == "scene.tutorial.red_robed_visitor"


def test_play_by_free_text_matches_keywords(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001
    playback = service.play_scene(campaign_id="camp.t", state=state, scene=scene, choice="我想问母亲")
    assert playback.next_scene_id == "scene.tutorial.red_robed_visitor"


def test_full_tutorial_three_scenes_reaches_end(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    path = [
        ("scene.tutorial.ration_morning", 1),
        ("scene.tutorial.red_robed_visitor", 1),
        ("scene.tutorial.neighbor_missing", 1),
    ]
    ended = False
    for scene_id, choice in path:
        scene = service._scenes[scene_id]  # noqa: SLF001
        playback = service.play_scene(campaign_id="camp.t", state=state, scene=scene, choice=choice)
        state = service.repo.load_consistent_snapshot("camp.t")
        ended = playback.ended
    assert ended is True
    assert service.repo.latest_sequence("camp.t") >= 8


def test_out_of_range_choice_rejected(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001
    from noosphere40k.domain.errors import RuleInvalidActionError

    with pytest.raises(RuleInvalidActionError):
        service.play_scene(campaign_id="camp.t", state=state, scene=scene, choice=99)


def test_observe_check_records_detail(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.red_robed_visitor"]  # noqa: SLF001
    playback = service.play_scene(
        campaign_id="camp.t", state=state, scene=scene, choice=2
    )
    assert playback.check_detail is not None
    assert "d100=" in playback.check_detail
    assert playback.next_scene_id == "scene.tutorial.neighbor_missing"


def test_load_consistent_snapshot_after_tutorial(service: TutorialService) -> None:
    state = service.create_campaign("camp.t", "T", display_name="Ada")
    scene = service._scenes["scene.tutorial.ration_morning"]  # noqa: SLF001
    service.play_scene(campaign_id="camp.t", state=state, scene=scene, choice=1)
    loaded = service.repo.load_consistent_snapshot("camp.t")
    assert loaded.sequence >= 4
    assert loaded.state_hash == service.repo.replay_from_scratch("camp.t").state_hash