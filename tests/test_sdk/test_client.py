"""Tests for the SDK client."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.core.actions import ActionResult, ActionType
from computeforge.core.exceptions import ComputeForgeError
from computeforge.models.session import Session, SessionConfig
from computeforge.sdk.client import BatchResult, ComputeForgeClient
from computeforge.sdk.progress import ActionProgress


class TestComputeForgeClient:
    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        client = ComputeForgeClient()
        await client.connect()
        assert client.is_connected
        await client.close()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self):
        client = ComputeForgeClient()
        await client.connect()
        sessions = await client.list_sessions()
        assert isinstance(sessions, list)
        await client.close()

    @pytest.mark.asyncio
    async def test_export_import_session(self):
        import json

        from computeforge.models.session import Session

        client = ComputeForgeClient()
        await client.connect()

        session = Session()
        await client._storage.save_session(session)

        json_str = await client.export_session(session.id)
        data = json.loads(json_str)
        assert data["session"]["id"] == session.id

        await client.delete_session(session.id)
        await client.close()

    @pytest.mark.asyncio
    async def test_progress_callbacks(self):
        client = ComputeForgeClient()
        await client.connect()

        received = []

        async def progress_cb(progress: ActionProgress):
            received.append(progress)

        client.add_progress_callback(progress_cb)
        assert len(client._progress_callbacks) == 1
        await client.close()

    def test_engine_property(self):
        client = ComputeForgeClient()
        assert client.engine is None

    def test_storage_property(self):
        client = ComputeForgeClient()
        assert client.storage is None

    @pytest.mark.asyncio
    async def test_is_session_active_false(self):
        client = ComputeForgeClient()
        assert client.is_session_active is False

    @pytest.mark.asyncio
    async def test_is_session_active_true(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.is_running = True
        assert client.is_session_active is True

    @pytest.mark.asyncio
    async def test_auto_connect_loop_not_running(self):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        with patch("computeforge.sdk.client.StorageBackend") as mock_sb:
            mock_instance = MagicMock()
            mock_instance.connect = AsyncMock()
            mock_sb.return_value = mock_instance
            with patch("asyncio.get_event_loop", return_value=mock_loop):
                client = ComputeForgeClient(auto_connect=True)
                mock_loop.run_until_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_connect_loop_running(self):
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        with patch("asyncio.get_event_loop", return_value=mock_loop):
            with patch("asyncio.ensure_future") as mock_ensure:
                client = ComputeForgeClient(auto_connect=True)
                mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_when_already_connected(self):
        client = ComputeForgeClient()
        client._connected = True
        client._storage = MagicMock()
        client._storage.connect = AsyncMock()
        await client.connect()
        client._storage.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_with_engine_and_recorder(self):
        client = ComputeForgeClient()
        mock_engine = MagicMock()
        mock_engine.stop_session = AsyncMock()
        client._engine = mock_engine
        mock_recorder = MagicMock()
        mock_recorder.close = AsyncMock()
        client._recorder = mock_recorder
        client._storage = MagicMock()
        client._storage.close = AsyncMock()
        client._owns_storage = True
        await client.close()
        mock_engine.stop_session.assert_called_once()
        assert client._engine is None
        mock_recorder.close.assert_called_once()
        assert client._recorder is None
        client._storage.close.assert_called_once()
        assert not client._connected

    @pytest.mark.asyncio
    async def test_close_without_engine_or_recorder(self):
        client = ComputeForgeClient()
        client._engine = None
        client._recorder = None
        client._storage = MagicMock()
        client._storage.close = AsyncMock()
        client._owns_storage = False
        await client.close()
        client._storage.close.assert_not_called()
        assert not client._connected

    @pytest.mark.asyncio
    async def test_create_session(self):
        session = Session()
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock(return_value=session)
        mock_engine.start_session = AsyncMock()
        mock_engine.register_post_action_hook = MagicMock()
        mock_recorder = MagicMock()
        mock_recorder.connect = AsyncMock()
        mock_recorder.record_session_create = AsyncMock()
        mock_recorder.make_recorder_hooks = MagicMock(return_value=(None, MagicMock(), None))

        client = ComputeForgeClient()
        await client.connect()

        with patch("computeforge.sdk.client.ComputeEngine", return_value=mock_engine):
            with patch("computeforge.sdk.client.SessionRecorder", return_value=mock_recorder):
                result = await client.create_session()

        assert result.id == session.id
        mock_engine.create_session.assert_called_once()
        mock_engine.start_session.assert_called_once()
        mock_recorder.connect.assert_called_once()
        mock_recorder.record_session_create.assert_called_once_with(session)

    @pytest.mark.asyncio
    async def test_create_session_not_connected(self):
        session = Session()
        mock_engine = MagicMock()
        mock_engine.create_session = AsyncMock(return_value=session)
        mock_engine.start_session = AsyncMock()
        mock_engine.register_post_action_hook = MagicMock()
        mock_recorder = MagicMock()
        mock_recorder.connect = AsyncMock()
        mock_recorder.record_session_create = AsyncMock()
        mock_recorder.make_recorder_hooks = MagicMock(return_value=(None, MagicMock(), None))

        client = ComputeForgeClient()
        client._connected = False
        client._storage = MagicMock()
        client._storage.connect = AsyncMock()

        with patch("computeforge.sdk.client.ComputeEngine", return_value=mock_engine):
            with patch("computeforge.sdk.client.SessionRecorder", return_value=mock_recorder):
                result = await client.create_session()

        assert client._connected
        assert result.id == session.id

    @pytest.mark.asyncio
    async def test_get_session(self):
        session = Session()
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.load_session = AsyncMock(return_value=session)
        result = await client.get_session(session.id)
        assert result.id == session.id
        client._storage.load_session.assert_called_once_with(session.id)

    @pytest.mark.asyncio
    async def test_list_sessions_with_results(self):
        sessions = [Session(), Session()]
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.list_sessions = AsyncMock(return_value=sessions)
        result = await client.list_sessions(limit=10, offset=0, status="running")
        assert len(result) == 2
        client._storage.list_sessions.assert_called_once_with(limit=10, offset=0, status="running")

    @pytest.mark.asyncio
    async def test_list_sessions_no_storage(self):
        client = ComputeForgeClient()
        client._storage = None
        result = await client.list_sessions()
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_session(self):
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.delete_session = AsyncMock()
        await client.delete_session("test-id")
        client._storage.delete_session.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_get_session_summary(self):
        client = ComputeForgeClient()
        client._storage = MagicMock()
        with patch("computeforge.sdk.client.ReplayEngine") as mock_replay_cls:
            mock_replay = MagicMock()
            mock_replay.get_session_summary = AsyncMock(return_value={"summary": "data"})
            mock_replay_cls.return_value = mock_replay
            result = await client.get_session_summary("test-id")
            assert result == {"summary": "data"}
            mock_replay.get_session_summary.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_export_session_with_path(self, tmp_path):
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.export_session_json = AsyncMock(return_value='{"key": "value"}')
        output = tmp_path / "session.json"
        result = await client.export_session("test-id", output)
        assert result == '{"key": "value"}'
        assert output.read_text() == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_import_session(self):
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.import_session_json = AsyncMock(return_value="new-session-id")
        result = await client.import_session('{"some": "json"}')
        assert result == "new-session-id"

    @pytest.mark.asyncio
    async def test_get_engine_state_with_engine(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.get_state = AsyncMock(return_value={"state": "running", "session_id": "abc"})
        result = await client.get_engine_state()
        assert result == {"state": "running", "session_id": "abc"}

    @pytest.mark.asyncio
    async def test_get_engine_state_without_engine(self):
        client = ComputeForgeClient()
        client._engine = None
        result = await client.get_engine_state()
        assert result == {"state": "stopped", "session_id": None}

    @pytest.mark.asyncio
    async def test_navigate(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.NAVIGATE))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.navigate("https://example.com")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_click(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.CLICK))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.click("#button")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_type_text(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.TYPE))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.type_text("hello", "#input")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_screenshot(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.SCREENSHOT))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.screenshot()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_scroll(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.SCROLL))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.scroll()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_extract_text(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.EXTRACT_TEXT))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.extract_text()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_extract_html(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.EXTRACT_HTML))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.extract_html()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_evaluate(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.EVALUATE))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.evaluate("1+1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_hover(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.HOVER))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.hover("#btn")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_wait(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.WAIT))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.wait(500)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_no_engine(self):
        client = ComputeForgeClient()
        client._engine = None
        with pytest.raises(ComputeForgeError, match="No active session"):
            await client.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_engine_error(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(side_effect=ComputeForgeError("engine error"))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()
        result = await client.navigate("https://example.com")
        assert result.success is False
        assert "engine error" in result.error

    @pytest.mark.asyncio
    async def test_execute_without_recorder(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.NAVIGATE))
        client._engine.session = Session()
        client._recorder = None
        result = await client.navigate("https://example.com")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_actions_all_success(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.NAVIGATE))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        actions = [
            {"type": "navigate", "params": {"url": "https://example.com"}},
            {"type": "click", "params": {"selector": "#btn"}},
        ]
        result = await client.run_actions(actions)
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.completed is True
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_run_actions_stop_on_failure(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(side_effect=[
            ActionResult(success=True, action_type=ActionType.NAVIGATE),
            ActionResult(success=False, action_type=ActionType.CLICK, error="click failed"),
        ])
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        actions = [
            {"type": "navigate", "params": {"url": "https://example.com"}},
            {"type": "click", "params": {"selector": "#btn"}, "stop_on_failure": True},
        ]
        result = await client.run_actions(actions)
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.completed is True

    @pytest.mark.asyncio
    async def test_run_actions_exception(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(side_effect=ValueError("something bad"))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        actions = [
            {"type": "navigate", "params": {"url": "https://example.com"}},
        ]
        result = await client.run_actions(actions)
        assert result.failed == 1
        assert result.results[0].success is False

    @pytest.mark.asyncio
    async def test_run_workflow(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=True, action_type=ActionType.NAVIGATE))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        result = await client.run_workflow([{"type": "navigate", "params": {"url": "https://example.com"}}])
        assert result.succeeded == 1

    @pytest.mark.asyncio
    async def test_navigate_and_extract_success(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(side_effect=[
            ActionResult(success=True, action_type=ActionType.NAVIGATE, data={"url": "https://example.com", "title": "Example"}),
            ActionResult(success=True, action_type=ActionType.EXTRACT_TEXT, data={"text": "Hello world"}),
        ])
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        result = await client.navigate_and_extract("https://example.com")
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example"
        assert result["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_navigate_and_extract_nav_failure(self):
        client = ComputeForgeClient()
        client._engine = MagicMock()
        client._engine.execute = AsyncMock(return_value=ActionResult(success=False, action_type=ActionType.NAVIGATE, error="nav failed"))
        client._engine.session = Session()
        client._recorder = MagicMock()
        client._recorder.record_action = AsyncMock()

        result = await client.navigate_and_extract("https://example.com")
        assert result["success"] is False
        assert result["error"] == "nav failed"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        client = ComputeForgeClient()
        client._storage = MagicMock()
        client._storage.connect = AsyncMock()
        client._storage.close = AsyncMock()
        async with client as c:
            assert c.is_connected
        assert not c.is_connected

    @pytest.mark.asyncio
    async def test_notify_progress_async_callback(self):
        client = ComputeForgeClient()
        received = []

        async def cb(progress):
            received.append(progress)

        client._progress_callbacks = [cb]
        progress = ActionProgress(total=1, current=0, current_action="test")
        await client._notify_progress(progress)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_notify_progress_sync_callback(self):
        client = ComputeForgeClient()
        received = []

        def cb(progress):
            received.append(progress)

        client._progress_callbacks = [cb]
        progress = ActionProgress(total=1, current=0, current_action="test")
        await client._notify_progress(progress)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_notify_progress_error(self):
        client = ComputeForgeClient()

        def cb(progress):
            raise ValueError("callback error")

        client._progress_callbacks = [cb]
        progress = ActionProgress(total=1, current=0, current_action="test")
        await client._notify_progress(progress)


class TestBatchResult:
    def test_batch_result_defaults(self):
        result = BatchResult()
        assert result.total_duration_ms == 0.0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.completed is True
