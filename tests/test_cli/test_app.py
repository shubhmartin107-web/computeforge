from __future__ import annotations

import builtins
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from computeforge.cli.app import app

runner = CliRunner()


def test_app_typer_creation():
    assert app.info.name == "computeforge"
    assert app.info.help is not None


def test_commands_registered():
    names = {c.name for c in app.registered_commands}
    for expected in {"run", "replay", "config", "shell", "export", "stats", "version"}:
        assert expected in names


def test_version_command():
    from computeforge._version import __version__

    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ComputeForge" in result.stdout
    assert __version__ in result.stdout


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ComputeForge" in result.stdout


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage:" in result.stdout
    assert "computeforge" in result.stdout


# ─── export_command coverage ───────────────────────────────────────


def test_export_command_with_output(tmp_path):
    output_file = tmp_path / "export.json"
    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.export_session_json = AsyncMock(return_value='{"key": "value"}')

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        with patch("computeforge.observability.replay.ReplayEngine", return_value=mock_replay):
            result = runner.invoke(app, ["export", "session-123", "--output", str(output_file)])
            assert result.exit_code == 0
            assert "Exported to" in result.stdout
            assert output_file.read_text() == '{"key": "value"}'


def test_export_command_without_output():
    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.export_session_json = AsyncMock(return_value='{"key": "value"}')

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        with patch("computeforge.observability.replay.ReplayEngine", return_value=mock_replay):
            result = runner.invoke(app, ["export", "session-123"])
            assert result.exit_code == 0
            assert "key" in result.stdout
            assert "value" in result.stdout


# ─── stats_command coverage ────────────────────────────────────────


def test_stats_command():
    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.get_session_stats = AsyncMock(return_value={
        "total_sessions": 10,
        "total_actions": 50,
        "succeeded": 40,
        "failed": 10,
        "avg_duration_ms": 100.0,
        "by_status": {"completed": 8, "failed": 2},
    })
    mock_storage.get_daily_stats = AsyncMock(return_value=[])

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "ComputeForge Statistics" in result.stdout
        assert "10" in result.stdout
        assert "50" in result.stdout


def test_stats_command_with_daily():
    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.get_session_stats = AsyncMock(return_value={
        "total_sessions": 10,
        "total_actions": 50,
        "succeeded": 40,
        "failed": 10,
        "avg_duration_ms": 100.0,
    })
    mock_storage.get_daily_stats = AsyncMock(return_value=[
        {"date": "2024-01-01", "sessions": 5, "actions": 25},
        {"date": "2024-01-02", "sessions": 3, "actions": 15},
    ])

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Daily Activity" in result.stdout
        assert "2024-01-01" in result.stdout
        assert "2024-01-02" in result.stdout


# ─── version_command edge cases ────────────────────────────────────


def test_version_command_gradio_import_error():
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "gradio":
            raise ImportError("No module named gradio")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ComputeForge" in result.stdout


def test_version_command_fastapi_import_error():
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "fastapi":
            raise ImportError("No module named fastapi")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ComputeForge" in result.stdout


def test_version_command_both_libraries_installed():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ComputeForge" in result.stdout


# ─── main callback coverage ────────────────────────────────────────


def test_main_callback_no_subcommand():
    with patch.object(app.info, "no_args_is_help", False):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "ComputeForge" in result.stdout
        assert "Commands:" in result.stdout


def test_main_entry():
    from computeforge.cli.app import main_entry

    with patch.object(app.info, "no_args_is_help", False):
        with patch("computeforge.cli.app.app") as mock_app:
            main_entry()
            mock_app.assert_called_once()
