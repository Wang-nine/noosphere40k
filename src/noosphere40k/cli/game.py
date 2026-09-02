"""Interactive game loop (G-02).

Runs the offline tutorial campaign without an LLM: scenes render via validated
templates, choices via numbered options or free text, checks resolve via d100.
Every action commits events atomically through the repository.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from noosphere40k.application.campaign_service import TutorialService
from noosphere40k.application.narration_service import NarrationService
from noosphere40k.cli.render import (
    make_console,
    render_actions,
    render_error,
    render_message,
    render_scene,
    render_state_summary,
)
from noosphere40k.config.settings import AppSettings
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

    # optional LLM narration service (falls back to templates automatically)
    from noosphere40k.config.settings import load_settings

    settings = load_settings(cli_overrides={})
    narration = _build_narration_service(settings, service)

    # resume at the current scene: last SCENE_STARTED event
    scene_id = _current_scene_id(repo, campaign_id)
    scene = service._scenes[scene_id]  # noqa: SLF001 - service owns pack lookup

    render_message(console, f"[bold]继续战役：{campaign_id}[/bold]")
    render_state_summary(console, state)
    console.print()

    turn_counter = state.sequence + 1
    while True:
        rendered = _narration_for(service, scene, state, narration, campaign_id, turn_counter)
        render_scene(console, scene, state, rendered)
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
        if raw.startswith("/encyclopedia"):
            _encyclopedia_command(console, service, raw)
            continue
        if raw.startswith("/know"):
            _know_command(console, service, state, raw)
            continue
        if raw.startswith("/sources"):
            _sources_command(console, service, raw)
            continue
        if raw == "/roll-details":
            _roll_details_command(console, repo, campaign_id)
            continue
        if raw == "/settings":
            _settings_command(console, repo, campaign_id)
            continue
        if raw == "/skip":
            render_message(console, "[bold]已跳过当前场景[/bold]（审核后的摘要事件将在后续批次写入）。")
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
        turn_counter += 1

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


def _build_narration_service(settings: AppSettings, service: TutorialService) -> NarrationService | None:
    """Build an LLM NarrationService when a provider is configured, else None."""
    from noosphere40k.application.narration_service import NarrationService
    from noosphere40k.llm.factory import build_provider

    if not settings.has_api_key:
        return None
    provider = build_provider(settings)
    try:
        return NarrationService(provider, service.lore)
    except Exception:  # noqa: BLE001 - never break the loop over provider issues
        return None


def _narration_for(
    service: TutorialService,
    scene: SceneDefinition,
    state: GameState,
    narration_service: NarrationService | None,
    campaign_id: str,
    turn_number: int,
) -> str:
    """LLM narration with automatic template fallback (offline-safe)."""
    if narration_service is None:
        return service._template_text(scene, state)  # noqa: SLF001
    import asyncio

    text: str | None = None
    try:
        text = asyncio.run(narration_service.narrate(
            state=state,
            scene=scene,
            player_input="",
            trace_id=f"turn-{campaign_id}-{turn_number}",
            turn_number=turn_number,
        ))
    except Exception:  # noqa: BLE001
        text = None
    if text:
        return text
    return service._template_text(scene, state)  # noqa: SLF001


def _encyclopedia_command(console: Console, service: TutorialService, raw: str) -> None:
    """/encyclopedia <术语> — player-layer glossary (never character knowledge)."""
    from noosphere40k.application.encyclopedia_service import EncyclopediaService
    from noosphere40k.domain.errors import NoosphereError

    term = raw.replace("/encyclopedia", "", 1).strip()
    if not term:
        render_message(console, "用法：/encyclopedia <术语>")
        return
    try:
        result = EncyclopediaService(service.lore).encyclopedia_term(term)
    except NoosphereError as exc:
        render_error(console, f"{exc.code.value}: {exc.message}")
        return
    render_message(console, f"[bold]百科：[/bold]\n{result}")


def _know_command(console: Console, service: TutorialService, state: GameState, raw: str) -> None:
    """/know <主题> — character knowledge only."""
    from noosphere40k.application.encyclopedia_service import EncyclopediaService

    subject = raw.replace("/know", "", 1).strip()
    if not subject:
        render_message(console, "用法：/know <主题>")
        return
    character_id = state.character.character_id if state.character else "pc"
    result = EncyclopediaService(service.lore).character_knowledge(character_id, subject)
    render_message(console, f"[bold]我知道什么：[/bold]{result}")


def _sources_command(console: Console, service: TutorialService, raw: str) -> None:
    """/sources <fact_id> — provenance from approved facts."""
    from noosphere40k.application.encyclopedia_service import EncyclopediaService
    from noosphere40k.domain.errors import NoosphereError

    fact_id = raw.replace("/sources", "", 1).strip()
    if not fact_id:
        render_message(console, "用法：/sources <fact_id>")
        return
    try:
        result = EncyclopediaService(service.lore).sources_for(fact_id)
    except NoosphereError as exc:
        render_error(console, f"{exc.code.value}: {exc.message}")
        return
    render_message(console, f"[bold]来源：[/bold]\n{result}")


def _roll_details_command(console: Console, repo: CampaignRepository, campaign_id: str) -> None:
    """/roll-details — last CheckResolved from committed events (never asks LLM)."""
    events = repo.load_events(campaign_id)
    for event in reversed(events):
        if event.event_type == "CheckResolved":
            payload = event.payload
            render_message(
                console,
                f"[bold]检定详情：[/bold]d100={payload.get('roll')} "
                f"目标={payload.get('target')} "
                f"{'成功' if payload.get('success') else '失败'} "
                f"（幅度 {payload.get('margin_degrees')}，特殊 {payload.get('special')}）",
            )
            render_message(console, "[dim]来源：事件日志（确定性规则引擎，非 LLM）。[/dim]")
            return
    render_message(console, "还没有可显示的检定记录。")


def _settings_command(console: Console, repo: CampaignRepository, campaign_id: str) -> None:
    """/settings — show/change content settings (G-05 age adaptation)."""
    render_message(
        console,
        "[bold]当前设置：[/bold]"
        "教学 standard · 叙事 standard · 暴力 moderate · 战斗 standard",
    )
    render_message(
        console,
        "[dim]儿童阶段：情色/性化/成人恋爱标签永远拒绝；暴力可淡出。[/dim]",
    )
    from noosphere40k.domain.models import CampaignSettings

    settings = CampaignSettings(tutorial_level="standard", narration_length="standard",
                                graphic_violence="moderate", combat_frequency="standard")
    repo.update_settings(campaign_id, settings.model_dump_json())
    render_message(console, "设置已应用并写入存档（影响规则的设置不可静默改变）。")