from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from computeforge.cli.app import app

runner = CliRunner()


def _make_mock_engine():
    engine = MagicMock()
    engine.create_session = AsyncMock()
    engine.start_session = AsyncMock()
    engine.navigate = AsyncMock(return_value=MagicMock(success=True))
    engine.get_page_info = AsyncMock(
        return_value={"url": "https://example.com", "title": "Example"}
    )
    engine.screenshot = AsyncMock(
        return_value=MagicMock(success=True, data={"image": b"fake"})
    )
    engine.extract_text = AsyncMock(
        return_value=MagicMock(success=True, data={"text": "Hello world"})
    )
    engine.scroll = AsyncMock()
    engine.stop_session = AsyncMock()
    engine.session = MagicMock(
        action_count=5,
        status=MagicMock(value="completed"),
    )
    return engine


def test_run_command_basic():
    engine = _make_mock_engine()
    with patch("computeforge.cli.run.ComputeEngine", return_value=engine):
        result = runner.invoke(app, ["run", "https://example.com"])
    assert result.exit_code == 0
    assert "Session complete" in result.stdout
    assert "5" in result.stdout


def test_run_with_visible_flag():
    engine = _make_mock_engine()
    with patch("computeforge.cli.run.ComputeEngine", return_value=engine):
        result = runner.invoke(app, ["run", "https://example.com", "--visible"])
    assert result.exit_code == 0


def test_run_navigation_failure():
    engine = _make_mock_engine()
    engine.navigate = AsyncMock(
        return_value=MagicMock(success=False, error="Connection refused")
    )
    with patch("computeforge.cli.run.ComputeEngine", return_value=engine):
        result = runner.invoke(app, ["run", "https://example.com"])
    assert result.exit_code == 0
    assert "Navigation failed" in result.stdout


def test_run_exception_handling():
    engine = _make_mock_engine()
    engine.create_session = AsyncMock(side_effect=Exception("Engine crash"))
    with patch("computeforge.cli.run.ComputeEngine", return_value=engine):
        result = runner.invoke(app, ["run", "https://example.com"])
    assert result.exit_code == 0
    assert "Error" in result.stdout
