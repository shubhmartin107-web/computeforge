from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.models.session import SessionStatus
from tests.factories import make_action_record, make_session


@pytest.fixture
def run_async():
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    def _run(coro):
        return _loop.run_until_complete(coro)
    yield _run
    _loop.close()


def _sm_callbacks_setup() -> tuple[dict, MagicMock]:
    callbacks = {}
    mock_gr = MagicMock()
    mock_gr.Markdown = MagicMock()
    mock_gr.Button = MagicMock()
    mock_gr.Textbox = MagicMock()
    mock_gr.Dataframe = MagicMock()
    mock_gr.Row.return_value.__enter__.return_value = None
    mock_gr.Row.return_value.__exit__ = MagicMock()
    mock_gr.Column.return_value.__enter__.return_value = None
    mock_gr.Column.return_value.__exit__ = MagicMock()
    mock_gr.State = MagicMock()

    def capture_click(fn=None, inputs=None, outputs=None):
        callbacks[fn.__name__] = fn
        return MagicMock()

    mock_gr.Button.return_value.click = capture_click

    return callbacks, mock_gr


class TestSessionManager:
    def test_list_all_sessions_returns_formatted_data(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[
            make_session(
                id="abc12345-1111-1111-1111-111111111111",
                status=SessionStatus.COMPLETED,
                action_count=7,
                created_at=datetime(2025, 6, 1, 10, 0, 0),
                ended_at=datetime(2025, 6, 1, 10, 30, 0),
                error=None,
            ),
        ])
        mock_storage.get_session_stats = AsyncMock(return_value={
            "total_sessions": 1, "by_status": {"completed": 1},
            "top_action_types": [], "total_actions": 7, "avg_duration_ms": 100.0,
        })

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        _stats_str, rows = callbacks["refresh_all"]()
        assert len(rows) == 1
        assert rows[0][1] == "completed"
        assert rows[0][2] == "7"

    def test_list_all_sessions_handles_exception(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=Exception("DB error"))
        mock_storage.get_session_stats = AsyncMock(return_value={
            "total_sessions": 0, "by_status": {}, "top_action_types": [],
            "total_actions": 0, "avg_duration_ms": 0.0,
        })

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        _stats_str, rows = callbacks["refresh_all"]()
        assert rows == []

    def test_get_stats_returns_formatted_stats(self, mock_storage, run_async):
        mock_storage.get_session_stats = AsyncMock(return_value={
            "total_sessions": 5, "by_status": {"completed": 3, "failed": 2},
            "top_action_types": [("navigate", 10)], "total_actions": 20,
            "avg_duration_ms": 150.0,
        })
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        stats_str, _rows = callbacks["refresh_all"]()
        assert "Total Sessions" in stats_str
        assert "5" in stats_str
        assert "Total Actions" in stats_str
        assert "20" in stats_str
        assert "completed" in stats_str
        assert "failed" in stats_str

    def test_delete_session_finds_and_deletes(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.PENDING,
        )
        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.delete_session = AsyncMock(return_value=None)

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["delete_session"]("abc12345")
        assert "Deleted" in result
        mock_storage.delete_session.assert_awaited_once_with(session.id)

    def test_delete_session_not_found(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["delete_session"]("nonexistent")
        assert "not found" in result

    def test_export_session_exports_data(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.COMPLETED,
        )
        actions = [
            make_action_record(session_id=session.id, type="navigate", duration_ms=100.0),
        ]
        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.load_actions = AsyncMock(return_value=actions)

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["export_session"]("abc12345")
        assert "session" in result
        assert "actions" in result
        assert "abc12345" in result

    def test_get_stats_error(self, mock_storage, run_async):
        mock_storage.get_session_stats = AsyncMock(side_effect=ValueError("Stats error"))
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        _stats_str, _rows = callbacks["refresh_all"]()
        assert "Error" in _stats_str

    def test_delete_session_error(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=ValueError("List error"))

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["delete_session"]("abc12345")
        assert "Error" in result

    def test_export_session_not_found(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["export_session"]("nonexistent")
        assert "not found" in result

    def test_export_session_error(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=ValueError("Export error"))

        callbacks, mock_gr = _sm_callbacks_setup()
        with patch("computeforge.dashboard.session_manager.gr", mock_gr):
            from computeforge.dashboard.session_manager import create_session_manager_tab
            create_session_manager_tab(mock_storage, run_async)

        result = callbacks["export_session"]("abc12345")
        assert "Error" in result
