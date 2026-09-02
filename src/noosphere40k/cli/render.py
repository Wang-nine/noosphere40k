"""Terminal rendering for the game loop (G-02).

Business logic never depends on colors or terminal width. ``--no-color``
disables styling; all information is preserved as plain text.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from noosphere40k.content.schemas import SceneDefinition
from noosphere40k.domain.models import GameState


def make_console(*, no_color: bool = False) -> Console:
    return Console(no_color=no_color, highlight=False)


def render_scene(
    console: Console,
    scene: SceneDefinition,
    state: GameState,
    narration: str,
) -> None:
    header = Text()
    header.append(scene.title, style="bold")
    if state.character is not None:
        header.append(
            f"  ·  {state.character.display_name} · 阶段：{state.character.life_stage}",
            style="dim",
        )
    console.print(Panel(header, border_style="cyan"))
    console.print(narration)
    console.print()


def render_actions(console: Console, scene: SceneDefinition) -> None:
    console.print("可选行动：")
    for index, action in enumerate(scene.action_templates, start=1):
        console.print(f"  {index}. {action.display_text}")
    console.print(f"  {len(scene.action_templates) + 1}. 自由输入行动（自然语言）")


def render_state_summary(console: Console, state: GameState) -> None:
    if state.character is None:
        return
    char = state.character
    console.print(
        f"[dim]年龄 {char.chronological_age_days} 天 · 生命阶段 {char.life_stage}[/dim]"
    )
    if char.attributes:
        summary = "  ".join(f"{k}={v}" for k, v in sorted(char.attributes.items()))
        console.print(f"[dim]属性：{summary}[/dim]")


def render_roll_details(console: Console, roll: int, target: int, success: bool, margin: int) -> None:
    outcome = "成功" if success else "失败"
    console.print(f"检定详情：d100={roll} 目标={target} → {outcome}（幅度 {margin}）")


def render_message(console: Console, message: str) -> None:
    console.print(message)


def render_error(console: Console, message: str) -> None:
    console.print(f"[red]错误：{message}[/red]")