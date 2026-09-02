"""Interactive game loop (G-02).

Runs the offline tutorial campaign without an LLM: scenes render via validated
templates, choices via numbered options or free text, checks resolve via d100.
Every action commits events atomically through the repository.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from noosphere40k.application.campaign_service import TutorialService
from noosphere40k.cli.render import (
    make_console,
    render_actions,
    render_error,
    render_message,
    render_scene,
    render_state_summary,
)
from noosphere40k.content.schemas import SceneDefinition
from noosphere40k.domain.errors import NoosphereError
from noosphere40k.domain.models import GameState
from noosphere40k.persistence.repositories import CampaignRepository

META_COMMANDS = {"/help", "/quit", "/character", "/saves"}


def _parse_choice(raw: str) -> str | int:
    text = raw.strip()
    if text.isdigit():
        return int(text)
    return text


def run_game_loop(*, db_path: Path, campaign_id: str, console: Console | None = None) -> int:
    console = console or make_console()
    repo = CampaignRepository.at(db_path)
    service = TutorialService(repo)
    state = repo.load_consistent_snapshot(campaign_id)

    if state.character is None:
        render_error(console, "存档没有角色，无法继续。")
        return 1

    # resume at the current scene: last SCENE_STARTED event
    scene_id = _current_scene_id(repo, campaign_id)
    scene = service._scenes[scene_id]  # noqa: SLF001 - service owns pack lookup

    render_message(console, f"[bold]继续战役：{campaign_id}[/bold]")
    render_state_summary(console, state)
    console.print()

    while True:
        render_scene(console, scene, state, _narration_for(service, scene, state))
        render_actions(console, scene)

        try:
            raw = console.input("> ").strip()
        except EOFError:
            render_message(console, "再见。")
            return 0

        if not raw:
            continue
        if raw == "/quit":
            render_message(console, "已保存，再见。")
            return 0
        if raw == "/help":
            render_message(
                console,
                "/quit 退出 · /character 查看角色 · /recap 回顾 · /timejump 时间跳跃 · "
                "输入编号或自然语言行动 · 无 LLM 模式使用模板叙事",
            )
            continue
        if raw == "/character":
            render_state_summary(console, state)
            continue
        if raw == "/saves":
            render_message(console, "自动存档已启用，每回合事务提交。")
            continue
        if raw == "/recap":
            from noosphere40k.application.chronicle import generate_recap

            events = repo.load_events(campaign_id)
            render_message(console, f"[bold]回顾：[/bold]{generate_recap(events)}")
            continue
        if raw == "/timejump":

            try:
                days = int(console.input("跳过多少天？> ").strip())
            except (ValueError, EOFError):
                render_message(console, "已取消时间跳跃（无事件产生）。")
                continue
            preview = service.time_jump(
                campaign_id=campaign_id, state=state, days=days, confirm=False
            )
            render_message(console, preview.narration)
            try:
                confirm = console.input("确认时间跳跃？[y/N] > ").strip().lower()
            except EOFError:
                confirm = "n"
            if confirm not in ("y", "yes"):
                render_message(console, "已取消时间跳跃（无事件产生）。")
                continue
            playback = service.time_jump(
                campaign_id=campaign_id, state=state, days=days, confirm=True
            )
            state = repo.load_consistent_snapshot(campaign_id)
            render_message(console, playback.narration)
            render_state_summary(console, state)
            continue

        choice = _parse_choice(raw)
        try:
            playback = service.play_scene(
                campaign_id=campaign_id,
                state=state,
                scene=scene,
                choice=choice,
            )
        except NoosphereError as exc:
            render_error(console, f"{exc.code.value}: {exc.message}")
            continue

        if playback.check_detail:
            render_message(console, f"[dim]检定详情：{playback.check_detail}[/dim]")
        if playback.next_scene_id is not None and playback.scene is not None:
            scene = playback.scene
            state = repo.load_consistent_snapshot(campaign_id)
            continue

        render_message(console, "[bold]教程片段完成。[/bold]")
        render_message(
            console,
            "你已看到《灰籍》问题的第一次闪现。后续批次将扩展少年、青年与终局。",
        )
        return 0


def _current_scene_id(repo: CampaignRepository, campaign_id: str) -> str:
    events = repo.load_events(campaign_id)
    for event in reversed(events):
        if event.event_type == "SceneStarted":
            return str(event.payload.get("scene_id", "scene.tutorial.ration_morning"))
    return "scene.tutorial.ration_morning"


def _narration_for(service: TutorialService, scene: SceneDefinition, state: GameState) -> str:
    """Re-render the fallback template for the current scene (offline narration)."""
    return service._template_text(scene, state)  # noqa: SLF001