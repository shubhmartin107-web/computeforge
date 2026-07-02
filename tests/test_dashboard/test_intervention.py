from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

from computeforge.core.actions import ActionResult


def _make_intervention_callbacks() -> dict:
    callbacks = {}
    mock_gr = MagicMock()
    mock_gr.Row.return_value.__enter__.return_value = None
    mock_gr.Row.return_value.__exit__ = MagicMock()
    mock_gr.Column.return_value.__enter__.return_value = None
    mock_gr.Column.return_value.__exit__ = MagicMock()
    mock_gr.Markdown = MagicMock()
    mock_gr.Button = MagicMock()
    mock_gr.Textbox = MagicMock()
    mock_gr.Checkbox = MagicMock()
    mock_gr.Dropdown = MagicMock()
    mock_gr.State = MagicMock()

    click_registry: dict[str, object] = {}

    def click_side_effect(fn=None, inputs=None, outputs=None):
        nonlocal callbacks
        key = fn.__name__ if hasattr(fn, "__name__") else str(id(fn))
        click_registry[key] = fn
        callbacks[key] = fn
        return MagicMock()

    mock_gr.Button.return_value.click = click_side_effect

    captured_locals = {}
    old_trace = sys.gettrace()

    def trace_calls(frame, event, arg):
        if event == 'call' and frame.f_code.co_name == 'create_intervention_tab':
            def trace_returns(frame, event, arg):
                if event == 'return':
                    captured_locals.update(frame.f_locals)
                return trace_returns
            return trace_returns
        return None

    sys.settrace(trace_calls)
    try:
        with patch("computeforge.dashboard.intervention.gr", mock_gr):
            from computeforge.dashboard.intervention import create_intervention_tab
            create_intervention_tab()
    finally:
        sys.settrace(old_trace)

    if 'update_status' in captured_locals:
        callbacks['update_status'] = captured_locals['update_status']

    return callbacks


class TestInterventionTab:
    def test_start_engine_starts_engine(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            result = callbacks["start_engine"]("https://example.com", True)

        assert "Engine started" in result
        mock_engine.create_session.assert_awaited_once()
        mock_engine.start_session.assert_awaited_once()
        mock_engine.navigate.assert_awaited_once()

    def test_start_engine_without_url(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            result = callbacks["start_engine"]("", True)

        assert "Engine started" in result
        mock_engine.navigate.assert_not_called()

    def test_start_engine_navigation_failure(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=False, action_type="navigate", data={}, error="Timeout"))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            result = callbacks["start_engine"]("https://example.com", True)

        assert "Navigation failed" in result

    def test_start_engine_error(self):
        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", side_effect=ValueError("Engine init failed")):
            result = callbacks["start_engine"]("https://example.com", True)

        assert "Error" in result

    def test_stop_engine_stops_running_engine(self):
        mock_engine = MagicMock()
        mock_engine.stop_session = AsyncMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=MagicMock(success=True))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            start_result = callbacks["start_engine"]("https://example.com", True)
            assert "Engine started" in start_result

        result = callbacks["stop_engine"]()
        assert "Engine stopped" in result

    def test_stop_engine_without_running_engine(self):
        callbacks = _make_intervention_callbacks()
        result = callbacks["stop_engine"]()
        assert "No engine running" in result

    def test_stop_engine_error(self):
        mock_engine = MagicMock()
        mock_engine.stop_session = AsyncMock(side_effect=Exception("Stop failed"))
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        result = callbacks["stop_engine"]()
        assert "Error" in result

    def test_pause_and_resume_engine(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.pause_session = AsyncMock()
        mock_engine.resume_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)
            pause_result = callbacks["pause_engine"]()
            resume_result = callbacks["resume_engine"]()

        assert "Engine paused" in pause_result
        assert "Engine resumed" in resume_result
        mock_engine.pause_session.assert_awaited_once()
        mock_engine.resume_session.assert_awaited_once()

    def test_pause_engine_without_running_engine(self):
        callbacks = _make_intervention_callbacks()
        result = callbacks["pause_engine"]()
        assert "No engine running" in result

    def test_pause_engine_error(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.pause_session = AsyncMock(side_effect=Exception("Pause failed"))
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        result = callbacks["pause_engine"]()
        assert "Error" in result

    def test_resume_engine_without_running_engine(self):
        callbacks = _make_intervention_callbacks()
        result = callbacks["resume_engine"]()
        assert "No engine running" in result

    def test_resume_engine_error(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.resume_session = AsyncMock(side_effect=Exception("Resume failed"))
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        result = callbacks["resume_engine"]()
        assert "Error" in result

    def test_execute_custom_action(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.execute = AsyncMock(return_value=ActionResult(
            success=True, action_type="click", data={"clicked": True}, duration_ms=42.0
        ))
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)
            result = callbacks["execute_custom_action"]("click", '{"selector": "#btn"}')

        assert "success=True" in result
        assert "clicked" in result
        mock_engine.execute.assert_awaited_once()

    def test_execute_custom_action_without_engine(self):
        callbacks = _make_intervention_callbacks()
        result = callbacks["execute_custom_action"]("navigate", '{"url": "https://example.com"}')
        assert "No engine running" in result

    def test_execute_custom_action_error(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("Execute failed"))
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        result = callbacks["execute_custom_action"]("click", '{"selector": "#btn"}')
        assert "Error" in result

    def test_execute_custom_action_invalid_json(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.execute = AsyncMock()
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        result = callbacks["execute_custom_action"]("navigate", "invalid json")
        assert "Error" in result

    def test_update_status_engine_stopped(self):
        callbacks = _make_intervention_callbacks()
        assert "update_status" in callbacks
        result = callbacks["update_status"]()
        assert "stopped" in result

    def test_update_status_engine_running(self):
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock()
        mock_engine.start_session = AsyncMock()
        mock_engine.navigate = AsyncMock(return_value=ActionResult(success=True, action_type="navigate", data={}))
        mock_engine.session.id = "test-session-id-1234"

        callbacks = _make_intervention_callbacks()

        with patch("computeforge.core.engine.ComputeEngine", return_value=mock_engine):
            callbacks["start_engine"]("https://example.com", True)

        assert "update_status" in callbacks
        result = callbacks["update_status"]()
        assert "running" in result

    def test_tab_ui_construction(self):
        mock_gr = MagicMock()
        mock_gr.Row.return_value.__enter__.return_value = None
        mock_gr.Row.return_value.__exit__ = MagicMock()
        mock_gr.Column.return_value.__enter__.return_value = None
        mock_gr.Column.return_value.__exit__ = MagicMock()
        mock_gr.Markdown = MagicMock()
        mock_gr.Button = MagicMock()
        mock_gr.Button.return_value.click = MagicMock()
        mock_gr.Textbox = MagicMock()
        mock_gr.Checkbox = MagicMock()
        mock_gr.Dropdown = MagicMock()
        mock_gr.State = MagicMock()

        with patch("computeforge.dashboard.intervention.gr", mock_gr):
            from computeforge.dashboard.intervention import create_intervention_tab
            create_intervention_tab()

        assert mock_gr.Button.call_count >= 4
        assert mock_gr.Markdown.call_count >= 4
        assert mock_gr.Dropdown.call_count == 1
        assert mock_gr.Textbox.call_count >= 2
