from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from computeforge.cli.app import app

runner = CliRunner()


def _make_mock_action(
    type_name: str = "navigate",
    status: str = "succeeded",
    duration_ms: float = 100.0,
    error: str | None = None,
    params: dict | None = None,
):
    action = MagicMock()
    action.type = type_name
    mock_status = MagicMock()
    mock_status.value = status
    action.status = mock_status
    action.duration_ms = duration_ms
    action.error = error
    action.params = params or {}
    action.screenshot_after = None
    return action


def _make_mock_replay(actions=None):
    replay = MagicMock()
    replay.session_exists = AsyncMock(return_value=True)
    replay.get_screenshot = AsyncMock(return_value=b"fake_image_bytes")
    replay.get_session_summary = AsyncMock(
        return_value={
            "session_id": "test-session-id",
            "status": "completed",
            "total_actions": 3,
            "succeeded": 2,
            "failed": 1,
            "blocked": 0,
            "total_duration_ms": 1500.0,
            "avg_action_duration_ms": 500.0,
            "success_rate": 66.7,
        }
    )
    replay.get_actions = AsyncMock(
        return_value=actions
        or [
            _make_mock_action("navigate", "succeeded", 500.0),
            _make_mock_action("click", "succeeded", 200.0),
            _make_mock_action("type", "failed", 300.0, error="Timeout"),
        ]
    )
    return replay


def test_replay_summary():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    replay = _make_mock_replay()

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
    ):
        result = runner.invoke(app, ["replay", "test-session-id"])

    assert result.exit_code == 0
    assert "test-session-id" in result.stdout


def test_replay_list():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    replay = _make_mock_replay()

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
    ):
        result = runner.invoke(app, ["replay", "test-session-id", "--list"])

    assert result.exit_code == 0
    assert "Session Actions" in result.stdout
    assert "navigate" in result.stdout


def test_replay_interactive():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    replay = _make_mock_replay()

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
        patch("builtins.input", return_value=""),
    ):
        result = runner.invoke(app, ["replay", "test-session-id", "--interactive"])

    assert result.exit_code == 0
    assert "Interactive Replay" in result.stdout


def test_replay_session_not_found():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    replay = MagicMock()
    replay.session_exists = AsyncMock(return_value=False)

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
    ):
        result = runner.invoke(app, ["replay", "nonexistent-session"])

    assert result.exit_code == 0
    assert "Session not found" in result.stdout


def test_replay_interactive_with_params():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    actions = [
        _make_mock_action("navigate", "succeeded", 500.0, params={"url": "https://example.com"}),
        _make_mock_action("click", "succeeded", 200.0, params={"selector": "#btn"}),
    ]
    actions[1].screenshot_after = "screenshot-abc123"
    replay = _make_mock_replay(actions)

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
        patch("builtins.input", return_value=""),
    ):
        result = runner.invoke(app, ["replay", "test-session-id", "--interactive"])

    assert result.exit_code == 0
    assert "Params" in result.stdout
    assert "screenshot-abc123" in result.stdout or "Screenshot" in result.stdout


def test_replay_interactive_keyboard_interrupt():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    actions = [
        _make_mock_action("navigate", "succeeded", 500.0),
        _make_mock_action("click", "succeeded", 200.0),
    ]
    replay = _make_mock_replay(actions)

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
        patch("builtins.input", side_effect=KeyboardInterrupt()),
    ):
        result = runner.invoke(app, ["replay", "test-session-id", "--interactive"])

    assert result.exit_code == 0


def test_replay_summary_many_actions():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    actions = [_make_mock_action("navigate", "succeeded", 100.0) for _ in range(15)]
    replay = _make_mock_replay(actions)

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
    ):
        result = runner.invoke(app, ["replay", "test-session-id"])

    assert result.exit_code == 0
    assert "5 more actions" in result.stdout


def test_replay_interactive_with_error():
    storage = MagicMock()
    storage.connect = AsyncMock()
    storage.close = AsyncMock()
    actions = [
        _make_mock_action("navigate", "failed", 500.0, error="Navigation timeout"),
    ]
    replay = _make_mock_replay(actions)

    with (
        patch("computeforge.cli.replay.StorageBackend", return_value=storage),
        patch("computeforge.cli.replay.ReplayEngine", return_value=replay),
        patch("builtins.input", return_value=""),
    ):
        result = runner.invoke(app, ["replay", "test-session-id", "--interactive"])

    assert result.exit_code == 0
    assert "Navigation timeout" in result.stdout
