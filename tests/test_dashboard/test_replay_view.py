from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.models.action import ActionStatus
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


def _replay_callbacks_setup() -> tuple[dict, MagicMock]:
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
    mock_gr.Slider = MagicMock()
    mock_gr.Image = MagicMock()

    mock_gr.Button.return_value.click = lambda fn=None, **kwargs: callbacks.update(  # noqa: ARG005
        {fn.__name__: fn}
    ) or MagicMock()

    mock_gr.Slider.return_value.change = lambda fn=None, **kwargs: callbacks.update(  # noqa: ARG005
        {fn.__name__: fn}
    ) or MagicMock()

    callbacks["_mock_gr"] = mock_gr
    return callbacks, mock_gr


class TestReplayView:
    def test_load_session_list_returns_formatted_data(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[
            make_session(
                id="sess001-....-....-....-............",
                status=SessionStatus.COMPLETED,
                action_count=10,
                created_at=datetime(2025, 6, 1, 14, 30, 0),
            ),
        ])

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        rows = callbacks["load_session_list"]()
        assert isinstance(rows, list)
        assert len(rows) >= 1

    def test_load_session_list_handles_exception(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=Exception("DB error"))

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        rows = callbacks["load_session_list"]()
        assert rows == []

    def test_load_replay_data_loads_session(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.COMPLETED,
            action_count=2,
        )
        actions = [
            make_action_record(
                session_id=session.id,
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                params={"url": "https://example.com"},
                duration_ms=100.0,
            ),
            make_action_record(
                session_id=session.id,
                type="click",
                status=ActionStatus.SUCCEEDED,
                params={"selector": "#btn"},
                duration_ms=50.0,
            ),
        ]

        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.load_actions = AsyncMock(return_value=actions)
        mock_storage.load_screenshot = MagicMock(return_value=None)

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        result = callbacks["load_replay_data"]("abc12345", {})

        assert result[0] == session.id
        assert result[1] == "completed"
        assert "navigate" in result[3]
        assert "click" in result[3]

    def test_load_replay_data_session_not_found(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(return_value=[])

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        result = callbacks["load_replay_data"]("nonexistent", {})
        assert result[0] == "Session not found"

    def test_load_replay_data_error(self, mock_storage, run_async):
        mock_storage.list_sessions = AsyncMock(side_effect=Exception("DB error"))

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        result = callbacks["load_replay_data"]("abc", {})
        assert "Error" in result[0]

    def test_update_step_view_shows_step_details(self, mock_storage, run_async):
        session = make_session(
            id="abc12345-1111-1111-1111-111111111111",
            status=SessionStatus.COMPLETED,
        )
        actions = [
            make_action_record(
                session_id=session.id,
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                params={"url": "https://example.com"},
                duration_ms=100.0,
                result={"title": "Example"},
                risk_score=0.1,
            ),
        ]

        mock_storage.list_sessions = AsyncMock(return_value=[session])
        mock_storage.load_actions = AsyncMock(return_value=actions)
        mock_storage.load_screenshot = MagicMock(return_value=None)

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        state = {"session_id": session.id, "actions": actions}
        detail, risk_info, screenshot = callbacks["update_step_view"](0, state)

        assert detail is not None
        assert "navigate" in str(detail)
        assert "Example" in str(detail)
        assert "Risk" in risk_info
        assert screenshot is None

    def test_update_step_view_out_of_bounds(self, mock_storage, run_async):
        actions = [
            make_action_record(
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                duration_ms=100.0,
            ),
        ]

        mock_storage.load_screenshot = MagicMock(return_value=None)

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        state = {"session_id": "test-id", "actions": actions}
        detail, _risk_info, _screenshot = callbacks["update_step_view"](5, state)

        assert "No data" in detail

    def test_update_step_view_with_error_and_safety(self, mock_storage, run_async):
        actions = [
            make_action_record(
                type="navigate",
                status=ActionStatus.FAILED,
                duration_ms=100.0,
                error="Network error",
                safety_decision="blocked",
            ),
        ]

        mock_storage.load_screenshot = MagicMock(return_value=None)

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        state = {"session_id": "test-id", "actions": actions}
        detail, risk_info, screenshot = callbacks["update_step_view"](0, state)

        assert "Network error" in detail
        assert "blocked" in detail
        assert "Risk" in risk_info

    def test_update_step_view_with_screenshot(self, mock_storage, run_async):
        actions = [
            make_action_record(
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                duration_ms=100.0,
                screenshot_after="screenshots/test.png",
            ),
        ]
        mock_storage.load_screenshot = MagicMock(return_value=b"fake_image_data")

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        state = {"session_id": "test-id", "actions": actions}
        detail, risk_info, screenshot = callbacks["update_step_view"](0, state)
        assert screenshot is not None

    def test_update_step_view_with_screenshot_error(self, mock_storage, run_async):
        actions = [
            make_action_record(
                type="navigate",
                status=ActionStatus.SUCCEEDED,
                duration_ms=100.0,
                screenshot_after="screenshots/test.png",
            ),
        ]
        mock_storage.load_screenshot = MagicMock(side_effect=Exception("Load failed"))

        callbacks, mock_gr = _replay_callbacks_setup()
        with patch("computeforge.dashboard.replay_view.gr", mock_gr):
            from computeforge.dashboard.replay_view import create_replay_tab
            create_replay_tab(mock_storage, run_async)

        state = {"session_id": "test-id", "actions": actions}
        detail, risk_info, screenshot = callbacks["update_step_view"](0, state)
        assert screenshot is None
