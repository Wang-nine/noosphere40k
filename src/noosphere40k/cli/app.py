"""CLI entry points (TECHNICAL_SPEC §4; G-01).

Program-level commands: version / doctor / new / continue / saves.
Campaign operations are placeholders until persistence repositories land.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

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
) -> None:
    """Create a new campaign (placeholder until C-03)."""
    _render(not_implemented_command("new"))


@app.command("continue")
def continue_(campaign_id: str | None = typer.Argument(None)) -> None:
    """Continue an existing campaign (placeholder until C-03)."""
    _render(not_implemented_command("continue"))


@app.command()
def saves(action: str | None = typer.Argument(None, help="list | export | import")) -> None:
    """Save utilities (placeholder until C-03/C-06)."""
    _render(saves_command(action))


def _render(result: CommandResult) -> None:
    for line in result.lines:
        typer.echo(line)
    raise typer.Exit(code=result.exit_code)


def main() -> None:
    app()