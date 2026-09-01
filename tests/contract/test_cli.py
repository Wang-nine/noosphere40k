"""G-01: program-level CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from noosphere40k import __version__
from noosphere40k.cli.app import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"noosphere40k {__version__}" in result.output


def test_doctor_command_runs_without_key() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Data dir" in result.output
    assert "API key: absent" in result.output


def test_new_is_placeholder() -> None:
    result = runner.invoke(app, ["new", "Test"])
    assert result.exit_code == 0
    assert "not implemented yet" in result.output


def test_continue_is_placeholder() -> None:
    result = runner.invoke(app, ["continue", "camp-1"])
    assert result.exit_code == 0
    assert "not implemented yet" in result.output


def test_saves_is_placeholder() -> None:
    result = runner.invoke(app, ["saves", "list"])
    assert result.exit_code == 0
    assert "not implemented yet" in result.output


def test_unknown_command_errors() -> None:
    result = runner.invoke(app, ["frobnicate"])
    assert result.exit_code != 0