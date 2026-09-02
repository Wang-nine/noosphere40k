"""CLI entry points (TECHNICAL_SPEC §4; G-01).

Program-level commands: version / doctor / new / continue / saves.
Campaign operations are placeholders until persistence repositories land.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer

from noosphere40k import __version__
from noosphere40k.config.settings import AppSettings, load_settings
from noosphere40k.domain.errors import NoosphereError
from noosphere40k.persistence.db import open_engine, run_migrations
from noosphere40k.persistence.migrations import MIGRATIONS

app = typer.Typer(no_args_is_help=True, add_completion=False)


@dataclass
class CommandResult:
    lines: list[str] = field(default_factory=list)
    exit_code: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


def version_command() -> CommandResult:
    return CommandResult(lines=[f"noosphere40k {__version__}"])


def doctor_command(settings: AppSettings) -> CommandResult:
    lines: list[str] = []
    exit_code = 0

    lines.append(f"Python: {sys.version.split()[0]}")
    lines.append(f"Data dir: {settings.data_dir}")
    lines.append(f"DB path: {settings.db_path}")
    lines.append(f"LLM provider configured: {settings.llm.provider or 'none'}")

    if settings.has_api_key:
        lines.append("API key: present (value not displayed)")
    else:
        lines.append("API key: absent (Stub provider remains usable offline)")

    try:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = open_engine(settings.db_path)
        applied = run_migrations(engine, MIGRATIONS)
        lines.append(f"Database: migrations up to date (applied now: {len(applied)})")
    except NoosphereError as exc:
        lines.append(f"Database: ERROR {exc.code.value}: {exc.message}")
        exit_code = 1

    return CommandResult(lines=lines, exit_code=exit_code)


def not_implemented_command(name: str) -> CommandResult:
    return CommandResult(
        lines=[
            f"`{name}` is not implemented yet: it belongs to the persistence "
            "batch (C-03 Repository / later). This is an intentional placeholder.",
        ]
    )


def saves_command(action: str | None) -> CommandResult:
    return not_implemented_command(f"saves {action or ''}".strip())


def _unique_campaign_id(name: str) -> str:
    """A default campaign id is always unique (never collides with an existing save)."""
    import uuid

    base = name or "default"
    return f"campaign.tutorial.{base}.{uuid.uuid4().hex[:6]}"


def _campaign_exists(db_path: Path, campaign_id: str) -> bool:
    from sqlalchemy import text

    from noosphere40k.persistence.db import open_engine

    engine = open_engine(db_path)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT campaign_id FROM campaigns WHERE campaign_id = :cid"),
            {"cid": campaign_id},
        ).fetchone()
    return row is not None


def _list_campaigns(db_path: Path) -> list[str]:
    from sqlalchemy import text

    from noosphere40k.persistence.db import open_engine

    engine = open_engine(db_path)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT campaign_id FROM campaigns ORDER BY created_at_utc")
        ).fetchall()
    return [row[0] for row in rows]


def _ensure_db(settings: AppSettings) -> None:
    """Run migrations so the repository can be used (idempotent)."""
    engine = open_engine(settings.db_path)
    run_migrations(engine, MIGRATIONS)
    engine.dispose()


@app.command()
def version() -> None:
    """Print the installed version."""
    _render(version_command())


@app.command()
def doctor() -> None:
    """Diagnose environment: versions, data dir, keys (never displayed), DB."""
    _render(doctor_command(load_settings()))


@app.command()
def new(
    name: str = typer.Argument("", help="Campaign name"),
    character: str = typer.Option("无名者", "--character", help="角色名"),
    campaign_id: str = typer.Option("", "--campaign-id", help="自定义战役 ID"),
    no_color: bool = typer.Option(False, "--no-color", help="禁用颜色"),
) -> None:
    """Create a new campaign and enter the offline tutorial loop."""
    from noosphere40k.application.campaign_service import TutorialService
    from noosphere40k.cli.game import run_game_loop
    from noosphere40k.config.settings import load_settings
    from noosphere40k.persistence.repositories import CampaignRepository

    settings = load_settings(cli_overrides={})
    _ensure_db(settings)
    cid = campaign_id or _unique_campaign_id(name)
    repo = CampaignRepository.at(settings.db_path)
    service = TutorialService(repo)
    if _campaign_exists(settings.db_path, cid):
        typer.echo(f"战役 {cid} 已存在。如需新建，请用 --campaign-id 指定不同 ID。")
        raise typer.Exit(code=1)
    service.create_campaign(cid, name or "未命名", display_name=character)
    typer.echo(f"已创建战役 {cid}（角色：{character}）")
    console = __import__("noosphere40k.cli.render", fromlist=["make_console"]).make_console(no_color=no_color)
    raise typer.Exit(code=run_game_loop(db_path=settings.db_path, campaign_id=cid, console=console))


@app.command("continue")
def continue_(campaign_id: str | None = typer.Argument(None)) -> None:
    """Continue an existing campaign (offline tutorial loop)."""
    from noosphere40k.cli.game import run_game_loop
    from noosphere40k.config.settings import load_settings

    settings = load_settings(cli_overrides={})
    _ensure_db(settings)
    if campaign_id is None:
        campaigns = _list_campaigns(settings.db_path)
        if not campaigns:
            typer.echo("没有可继续的战役。先运行 `noosphere new`。")
            raise typer.Exit(code=1)
        typer.echo("可用战役：")
        for index, cid in enumerate(campaigns, start=1):
            typer.echo(f"  {index}. {cid}")
        try:
            picked = int(typer.prompt("选择战役编号"))
        except (ValueError, KeyboardInterrupt):
            raise typer.Exit(code=1) from None
        if not 1 <= picked <= len(campaigns):
            typer.echo("编号无效。")
            raise typer.Exit(code=1)
        campaign_id = campaigns[picked - 1]
    raise typer.Exit(code=run_game_loop(db_path=settings.db_path, campaign_id=campaign_id))


@app.command()
def saves(action: str | None = typer.Argument(None, help="list | delete | export | import")) -> None:
    """Save utilities: `saves list` lists, `saves delete <id>` deletes a campaign."""
    from noosphere40k.config.settings import load_settings

    if action == "list":
        settings = load_settings(cli_overrides={})
        _ensure_db(settings)
        campaigns = _list_campaigns(settings.db_path)
        if not campaigns:
            typer.echo("（没有战役存档）")
            raise typer.Exit(code=0)
        for index, cid in enumerate(campaigns, start=1):
            typer.echo(f"{index}. {cid}")
        raise typer.Exit(code=0)
    if action == "delete":
        settings = load_settings(cli_overrides={})
        _ensure_db(settings)
        cid = typer.prompt("要删除的战役 ID")
        campaigns = _list_campaigns(settings.db_path)
        if cid not in campaigns:
            typer.echo(f"没有找到战役：{cid}")
            raise typer.Exit(code=1)
        confirm = typer.prompt(f"确认删除战役 {cid}？此操作不可撤销 [y/N]", default="n")
        if confirm.strip().lower() not in ("y", "yes"):
            typer.echo("已取消删除。")
            raise typer.Exit(code=0)
        from noosphere40k.persistence.repositories import CampaignRepository

        repo = CampaignRepository.at(settings.db_path)
        deleted = repo.delete_campaign(cid)
        if deleted:
            typer.echo(f"已删除战役 {cid}（含其事件、快照与角色数据）。")
        else:
            typer.echo(f"没有找到战役：{cid}")
            raise typer.Exit(code=1)
        raise typer.Exit(code=0)
    _render(saves_command(action))


def _render(result: CommandResult) -> None:
    for line in result.lines:
        typer.echo(line)
    raise typer.Exit(code=result.exit_code)


def main() -> None:
    app()