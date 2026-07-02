from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from computeforge.cli.app import app
from computeforge.cli.shell import InteractiveShell

runner = CliRunner()


def test_shell_initialization():
    shell = InteractiveShell()
    try:
        assert shell.prompt is not None
        assert shell._loop is not None
        assert not shell._session_active
        assert shell._client is None
    finally:
        shell._loop.close()


def test_shell_exit_command():
    shell = InteractiveShell()
    ret = shell.onecmd("exit")
    assert ret is True


def test_shell_quit_command():
    shell = InteractiveShell()
    ret = shell.onecmd("quit")
    assert ret is True


def test_shell_help_command(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("help")
        captured = capsys.readouterr()
        assert "ComputeForge Commands" in captured.out
        assert "start" in captured.out
        assert "stop" in captured.out
    finally:
        shell._loop.close()


def test_shell_emptyline():
    shell = InteractiveShell()
    try:
        ret = shell.emptyline()
        assert ret is False
    finally:
        shell._loop.close()


def test_shell_ensure_session_no_active():
    shell = InteractiveShell()
    try:
        assert not shell._ensure_session()
    finally:
        shell._loop.close()


def test_shell_ensure_session_active():
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        assert shell._ensure_session()
    finally:
        shell._loop.close()


def test_shell_start_command(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_session = AsyncMock(
        return_value=MagicMock(id="session-abc-123")
    )
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start")
            captured = capsys.readouterr()
            assert "Session started" in captured.out
            assert shell._session_active
        finally:
            shell._loop.close()


def test_shell_navigate_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("navigate https://example.com")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_navigate_with_session(capsys):
    mock_client = MagicMock()
    mock_client.navigate = AsyncMock(
        return_value=MagicMock(success=True, data={"url": "https://example.com"})
    )
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("navigate https://example.com")
        captured = capsys.readouterr()
        assert "Navigated to" in captured.out
    finally:
        shell._loop.close()


def test_shell_status_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("status")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_through_cli():
    with patch("computeforge.cli.app.InteractiveShell") as mock_shell:
        instance = mock_shell.return_value
        instance.cmdloop = MagicMock()
        result = runner.invoke(app, ["shell"])
        assert result.exit_code == 0
        instance.cmdloop.assert_called_once()


# ─── do_start coverage ─────────────────────────────────────────────


def test_shell_start_with_visible(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=MagicMock(id="session-abc-123"))
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start --visible")
            captured = capsys.readouterr()
            assert "Session started" in captured.out
            assert shell._session_active
            _, kwargs = mock_client.create_session.call_args
            assert kwargs["config"].headless is False
        finally:
            shell._loop.close()


def test_shell_start_with_unknown_flag(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=MagicMock(id="session-abc-123"))
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start --some-unknown-flag")
            captured = capsys.readouterr()
            assert "Session started" in captured.out
        finally:
            shell._loop.close()


def test_shell_start_with_url_success(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=MagicMock(id="session-abc-123"))
    mock_client.navigate = AsyncMock(return_value=MagicMock(success=True, data={"url": "https://example.com"}))
    mock_client._engine = MagicMock()
    mock_client._engine.get_page_info = AsyncMock(return_value={"title": "Example Page"})
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start https://example.com")
            captured = capsys.readouterr()
            assert "Navigating to" in captured.out
            assert "Example Page" in captured.out
        finally:
            shell._loop.close()


def test_shell_start_with_url_failure(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=MagicMock(id="session-abc-123"))
    mock_client.navigate = AsyncMock(return_value=MagicMock(success=False, error="Navigation timeout"))
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start https://example.com")
            captured = capsys.readouterr()
            assert "Navigation failed" in captured.out
        finally:
            shell._loop.close()


def test_shell_start_exception(capsys):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=Exception("Connection refused"))
    with patch("computeforge.cli.shell.ComputeForgeClient", return_value=mock_client):
        shell = InteractiveShell()
        try:
            shell.onecmd("start")
            captured = capsys.readouterr()
            assert "Error: Connection refused" in captured.out
        finally:
            shell._loop.close()


# ─── do_stop coverage ──────────────────────────────────────────────


def test_shell_stop_with_session(capsys):
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("stop")
        captured = capsys.readouterr()
        assert "Session stopped" in captured.out
        assert not shell._session_active
        assert shell._client is None
        mock_client.close.assert_called_once()
    finally:
        shell._loop.close()


def test_shell_stop_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("stop")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


# ─── do_status coverage ────────────────────────────────────────────


def test_shell_status_with_session(capsys):
    mock_client = MagicMock()
    mock_client.get_engine_state = AsyncMock(return_value={
        "state": "running",
        "session_id": "abc-123",
        "metrics": {"total_actions": 5, "successful": 4, "failed": 1},
    })
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("status")
        captured = capsys.readouterr()
        assert "Session Status" in captured.out
        assert "running" in captured.out
    finally:
        shell._loop.close()


# ─── do_navigate coverage ──────────────────────────────────────────


def test_shell_navigate_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("navigate")
        captured = capsys.readouterr()
        assert "Usage: navigate" in captured.out
    finally:
        shell._loop.close()


def test_shell_navigate_failure(capsys):
    mock_client = MagicMock()
    mock_client.navigate = AsyncMock(return_value=MagicMock(success=False, error="DNS error"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("navigate https://example.com")
        captured = capsys.readouterr()
        assert "Failed: DNS error" in captured.out
    finally:
        shell._loop.close()


# ─── do_click coverage ─────────────────────────────────────────────


def test_shell_click_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("click #button")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_click_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("click")
        captured = capsys.readouterr()
        assert "Usage: click" in captured.out
    finally:
        shell._loop.close()


def test_shell_click_success(capsys):
    mock_client = MagicMock()
    mock_client.click = AsyncMock(return_value=MagicMock(success=True))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("click #button")
        captured = capsys.readouterr()
        assert "Clicked" in captured.out
    finally:
        shell._loop.close()


def test_shell_click_failure(capsys):
    mock_client = MagicMock()
    mock_client.click = AsyncMock(return_value=MagicMock(success=False, error="Element not found"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("click #button")
        captured = capsys.readouterr()
        assert "Failed: Element not found" in captured.out
    finally:
        shell._loop.close()


# ─── do_type coverage ──────────────────────────────────────────────


def test_shell_type_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("type hello")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_type_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("type")
        captured = capsys.readouterr()
        assert "Usage: type" in captured.out
    finally:
        shell._loop.close()


def test_shell_type_with_selector(capsys):
    mock_client = MagicMock()
    mock_client.type_text = AsyncMock(return_value=MagicMock(success=True))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("type hello --selector #input")
        captured = capsys.readouterr()
        assert "Typed" in captured.out
        mock_client.type_text.assert_called_once_with("hello", selector="#input")
    finally:
        shell._loop.close()


def test_shell_type_failure(capsys):
    mock_client = MagicMock()
    mock_client.type_text = AsyncMock(return_value=MagicMock(success=False, error="Cannot type"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("type hello")
        captured = capsys.readouterr()
        assert "Failed: Cannot type" in captured.out
    finally:
        shell._loop.close()


# ─── do_ss (screenshot) coverage ───────────────────────────────────


def test_shell_ss_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("ss")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_ss_success_with_image(capsys):
    mock_client = MagicMock()
    mock_client.screenshot = AsyncMock(return_value=MagicMock(success=True, data={"image": b"pngdata..."}))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("ss")
        captured = capsys.readouterr()
        assert "Screenshot captured" in captured.out
        assert "bytes" in captured.out
    finally:
        shell._loop.close()


def test_shell_ss_success_no_image(capsys):
    mock_client = MagicMock()
    mock_client.screenshot = AsyncMock(return_value=MagicMock(success=True, data={}))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("ss")
        captured = capsys.readouterr()
        assert "Screenshot captured" in captured.out
    finally:
        shell._loop.close()


def test_shell_ss_failure(capsys):
    mock_client = MagicMock()
    mock_client.screenshot = AsyncMock(return_value=MagicMock(success=False, error="No page"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("ss")
        captured = capsys.readouterr()
        assert "Failed: No page" in captured.out
    finally:
        shell._loop.close()


# ─── do_scroll coverage ────────────────────────────────────────────


def test_shell_scroll_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("scroll")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_scroll_with_delta(capsys):
    mock_client = MagicMock()
    mock_client.scroll = AsyncMock(return_value=MagicMock(success=True))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("scroll 500")
        captured = capsys.readouterr()
        assert "Scrolled 500px" in captured.out
        mock_client.scroll.assert_called_once_with(delta_y=500)
    finally:
        shell._loop.close()


def test_shell_scroll_default(capsys):
    mock_client = MagicMock()
    mock_client.scroll = AsyncMock(return_value=MagicMock(success=True))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("scroll")
        captured = capsys.readouterr()
        assert "Scrolled 300px" in captured.out
        mock_client.scroll.assert_called_once_with(delta_y=300)
    finally:
        shell._loop.close()


def test_shell_scroll_failure(capsys):
    mock_client = MagicMock()
    mock_client.scroll = AsyncMock(return_value=MagicMock(success=False, error="Cannot scroll"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("scroll")
        captured = capsys.readouterr()
        assert "Failed: Cannot scroll" in captured.out
    finally:
        shell._loop.close()


# ─── do_extract coverage ───────────────────────────────────────────


def test_shell_extract_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("extract")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_extract_with_selector(capsys):
    mock_client = MagicMock()
    mock_client.extract_text = AsyncMock(return_value=MagicMock(success=True, data={"text": "# Hello World"}))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("extract h1")
        captured = capsys.readouterr()
        assert "Hello World" in captured.out
        mock_client.extract_text.assert_called_once_with(selector="h1")
    finally:
        shell._loop.close()


def test_shell_extract_no_selector(capsys):
    mock_client = MagicMock()
    mock_client.extract_text = AsyncMock(return_value=MagicMock(success=True, data={"text": "Full page text"}))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("extract")
        captured = capsys.readouterr()
        assert "Full page text" in captured.out
        mock_client.extract_text.assert_called_once_with(selector=None)
    finally:
        shell._loop.close()


def test_shell_extract_failure(capsys):
    mock_client = MagicMock()
    mock_client.extract_text = AsyncMock(return_value=MagicMock(success=False, error="No content"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("extract")
        captured = capsys.readouterr()
        assert "Failed: No content" in captured.out
    finally:
        shell._loop.close()


# ─── do_eval coverage ──────────────────────────────────────────────


def test_shell_eval_no_session(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("eval 1+1")
        captured = capsys.readouterr()
        assert "No active session" in captured.out
    finally:
        shell._loop.close()


def test_shell_eval_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("eval")
        captured = capsys.readouterr()
        assert "Usage: eval" in captured.out
    finally:
        shell._loop.close()


def test_shell_eval_success(capsys):
    mock_client = MagicMock()
    mock_client.evaluate = AsyncMock(return_value=MagicMock(success=True, data={"result": "2"}))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("eval 1+1")
        captured = capsys.readouterr()
        assert "Result: 2" in captured.out
    finally:
        shell._loop.close()


def test_shell_eval_failure(capsys):
    mock_client = MagicMock()
    mock_client.evaluate = AsyncMock(return_value=MagicMock(success=False, error="JS Error"))
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("eval bad()")
        captured = capsys.readouterr()
        assert "Failed: JS Error" in captured.out
    finally:
        shell._loop.close()


# ─── do_sessions coverage ──────────────────────────────────────────


def test_shell_sessions_with_limit(capsys):
    mock_session = MagicMock()
    mock_session.id = "abc123def456"
    mock_session.status = MagicMock(value="completed")
    mock_session.action_count = 10
    mock_session.created_at = datetime(2024, 1, 1, 12, 0)

    mock_client = MagicMock()
    mock_client.list_sessions = AsyncMock(return_value=[mock_session])
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("sessions 10")
        captured = capsys.readouterr()
        assert "Recent Sessions" in captured.out
        assert "completed" in captured.out
        mock_client.list_sessions.assert_called_once_with(limit=10)
    finally:
        shell._loop.close()


def test_shell_sessions_empty(capsys):
    mock_client = MagicMock()
    mock_client.list_sessions = AsyncMock(return_value=[])
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("sessions")
        captured = capsys.readouterr()
        assert "No sessions found" in captured.out
    finally:
        shell._loop.close()


def test_shell_sessions_list(capsys):
    mock_session1 = MagicMock()
    mock_session1.id = "abc123def456"
    mock_session1.status = MagicMock(value="completed")
    mock_session1.action_count = 10
    mock_session1.created_at = datetime(2024, 1, 1, 12, 0)

    mock_session2 = MagicMock()
    mock_session2.id = "ghi789jkl012"
    mock_session2.status = MagicMock(value="failed")
    mock_session2.action_count = 5
    mock_session2.created_at = None

    mock_client = MagicMock()
    mock_client.list_sessions = AsyncMock(return_value=[mock_session1, mock_session2])
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("sessions")
        captured = capsys.readouterr()
        assert "Recent Sessions" in captured.out
        assert "completed" in captured.out
        assert "failed" in captured.out
    finally:
        shell._loop.close()


# ─── do_replay coverage ────────────────────────────────────────────


def test_shell_replay_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("replay")
        captured = capsys.readouterr()
        assert "Usage: replay" in captured.out
    finally:
        shell._loop.close()


def test_shell_replay_with_session(capsys):
    mock_client = MagicMock()
    mock_client.storage = MagicMock()

    mock_summary = {
        "status": "completed",
        "total_actions": 15,
        "succeeded": 12,
        "failed": 2,
        "blocked": 1,
        "success_rate": 80.0,
        "total_duration_ms": 5000.0,
        "avg_action_duration_ms": 333.33,
    }

    with patch("computeforge.observability.replay.ReplayEngine") as mock_replay_cls:
        mock_replay = mock_replay_cls.return_value
        mock_replay.get_session_summary = AsyncMock(return_value=mock_summary)

        shell = InteractiveShell()
        try:
            shell._client = mock_client
            shell._session_active = True
            shell.onecmd("replay session-123")
            captured = capsys.readouterr()
            assert "Session Summary" in captured.out
            assert "completed" in captured.out
            assert "80.0" in captured.out
        finally:
            shell._loop.close()


# ─── do_export coverage ────────────────────────────────────────────


def test_shell_export_no_arg(capsys):
    shell = InteractiveShell()
    try:
        shell._client = MagicMock()
        shell._session_active = True
        shell.onecmd("export")
        captured = capsys.readouterr()
        assert "Usage: export" in captured.out
    finally:
        shell._loop.close()


def test_shell_export_with_output(capsys):
    mock_client = MagicMock()
    mock_client.export_session = AsyncMock(return_value='{"key": "value"}')
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("export session-123 output.json")
        captured = capsys.readouterr()
        assert "Exported to output.json" in captured.out
        mock_client.export_session.assert_called_once_with("session-123", output_path="output.json")
    finally:
        shell._loop.close()


def test_shell_export_without_output(capsys):
    mock_client = MagicMock()
    mock_client.export_session = AsyncMock(return_value='{"key": "value"}')
    shell = InteractiveShell()
    try:
        shell._client = mock_client
        shell._session_active = True
        shell.onecmd("export session-123")
        captured = capsys.readouterr()
        assert "key" in captured.out
        assert "value" in captured.out
        mock_client.export_session.assert_called_once_with("session-123", output_path=None)
    finally:
        shell._loop.close()


# ─── do_help coverage ──────────────────────────────────────────────


def test_shell_help_with_arg(capsys):
    shell = InteractiveShell()
    try:
        shell.onecmd("help start")
        captured = capsys.readouterr()
        assert "Start a new session" in captured.out
    finally:
        shell._loop.close()


# ─── do_exit / do_EOF coverage ─────────────────────────────────────


def test_shell_exit_with_session(capsys):
    mock_client = MagicMock()
    mock_client.close = AsyncMock()
    shell = InteractiveShell()
    shell._client = mock_client
    shell._session_active = True
    ret = shell.onecmd("exit")
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out
    assert ret is True
    mock_client.close.assert_called_once()


def test_shell_eof_command(capsys):
    shell = InteractiveShell()
    ret = shell.onecmd("EOF")
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out
    assert ret is True
