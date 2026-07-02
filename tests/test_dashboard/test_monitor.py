from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.models.action import ActionStatus
from computeforge.models.session import SessionConfig, SessionStatus
from tests.factories import make_action_record, make_session


@pytest.fixture
def run_async():
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    def _run(coro):
        return _loop.run_until_complete(coro)
    yield _run
    _loop.close()


def _callbacks_setup() -> tuple[dict, MagicMock]:
    callbacks = {}
    mock_gr = MagicMock()
    mock_gr.Row.return_value.__enter__.return_value = None
    mock_gr.Row.return_value.__exit__ = MagicMock()
    mock_gr.Column.return_value.__enter__.return_value = None
    mock_gr.Column.return_value.__exit__ = MagicMock()
    mock_gr.Markdown = MagicMock()
    mock_gr.Button = MagicMock()
    mock_gr.Textbox = MagicMock()
    mock_gr.Dataframe = MagicMock()
    mock_gr.State = MagicMock(return_value={})
    mock_gr.Button.return_value.click = lambda fn=None, **kwargs: callbacks.update(  # noqa: ARG005
        {"refresh": fn}
    ) or MagicMock()
    mock_gr.Textbox.return_value.submit = lambda fn=None, **kwargs: callbacks.update(  # noqa: ARG005
        {"view_details": fn}
    ) or MagicMock()
    return callbacks, mock_gr


class TestMonitorTab:
    def test_create_tab_runs_without_error(self, mock_storage, run_async):
        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)
        assert "refresh" in callbacks
        assert "view_details" in callbacks

    def test_refresh_sessions_returns_formatted_data(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[
            make_session(
                id="abc12345-1111-1111-1111-111111111111",
                status=SessionStatus.RUNNING,
                action_count=5,
                started_at=datetime(2025, 6, 1, 12, 30, 0),
                config=SessionConfig(base_url="https://example.com"),
            ),
        ])

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        rows, status = callbacks["refresh"]()
        assert len(rows) == 1
        assert rows[0][0] == "abc12345..." or rows[0][0].endswith("...")
        assert rows[0][1] == "\U0001f7e2 Running"
        assert rows[0][2] == "5"
        assert rows[0][4] == "https://example.com"
        assert "1 session(s) loaded" in status

    def test_refresh_sessions_empty(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        rows, status = callbacks["refresh"]()
        assert rows == []
        assert status == "No active sessions"

    def test_refresh_sessions_handles_error(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=ValueError("DB error"))

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        rows, status = callbacks["refresh"]()
        assert rows == []
        assert "Error" in status

    def test_view_session_details_shows_details(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.RUNNING,
            action_count=5,
            started_at=datetime(2025, 6, 1, 12, 30, 0),
            config=SessionConfig(base_url="https://example.com"),
        )
        actions = [
            make_action_record(
                session_id=session.id,
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                duration_ms=100.0,
            ),
        ]
        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.load_actions = AsyncMock(return_value=actions)

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        result = callbacks["view_details"]("abc12345", {})
        assert result[0] == session.id
        assert "running" in result[1]
        assert "5 actions" in result[2]
        assert "navigate" in result[3]

    def test_view_session_details_with_error_action(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.FAILED,
            action_count=1,
            config=SessionConfig(base_url="https://example.com"),
        )
        actions = [
            make_action_record(
                session_id=session.id,
                type="click",
                status=ActionStatus.FAILED,
                duration_ms=50.0,
                error="Element not found",
            ),
        ]
        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.load_actions = AsyncMock(return_value=actions)

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        result = callbacks["view_details"]("abc12345", {})
        assert "error" in result[3].lower()

    def test_view_session_details_not_found(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        result = callbacks["view_details"]("nonexistent", {})
        assert result[0] == "Not found"

    def test_view_session_details_error(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=ValueError("DB error"))

        callbacks, mock_gr = _callbacks_setup()
        with patch("computeforge.dashboard.monitor.gr", mock_gr):
            from computeforge.dashboard.monitor import create_monitor_tab
            create_monitor_tab(mock_storage, run_async)

        result = callbacks["view_details"]("abc", {})
        assert "Error" in result[0]
