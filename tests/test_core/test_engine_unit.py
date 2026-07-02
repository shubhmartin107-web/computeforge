from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.core.engine import ComputeEngine, EngineMetrics, EngineState
from computeforge.core.exceptions import (
    ActionFailed,
    ComputeForgeError,
    ElementNotFound,
    SafetyBlocked,
    SessionNotActive,
)
from computeforge.models.config import EngineConfig
from computeforge.models.session import SessionConfig
from tests.mocks.playwright_mock import MockPlaywright


@pytest.fixture
def engine():
    config = EngineConfig()
    config.safety.enabled = False
    eng = ComputeEngine(config=config)
    return eng


@pytest.mark.asyncio
async def test_engine_state_initial():
    engine = ComputeEngine()
    assert engine.state == EngineState.STOPPED
    assert not engine.is_running
    assert not engine.is_paused


@pytest.mark.asyncio
async def test_create_session(engine):
    session = await engine.create_session(SessionConfig(headless=True))
    assert session is not None
    assert session.id is not None
    assert engine.state == EngineState.STOPPED


@pytest.mark.asyncio
async def test_create_session_twice(engine):
    await engine.create_session(SessionConfig())
    await engine.create_session(SessionConfig())
    assert engine._session is not None


@pytest.mark.asyncio
async def test_start_session(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        session = await engine.start_session()
        assert engine.state == EngineState.RUNNING
        assert engine.is_running
        assert session is not None


@pytest.mark.asyncio
async def test_start_session_creates_session_auto(engine):
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        session = await engine.start_session()
        assert session is not None
        assert engine.state == EngineState.RUNNING


@pytest.mark.asyncio
async def test_start_session_browser_failure(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(side_effect=Exception("Browser failed"))
        with pytest.raises(Exception, match="Browser failed"):
            await engine.start_session()
        assert engine.state == EngineState.ERROR


@pytest.mark.asyncio
async def test_pause_and_resume(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        assert engine.is_running
        await engine.pause_session()
        assert engine.is_paused
        assert engine.state == EngineState.PAUSED
        await engine.resume_session()
        assert engine.is_running
        assert engine.state == EngineState.RUNNING


@pytest.mark.asyncio
async def test_pause_when_not_running(engine):
    with pytest.raises(ComputeForgeError, match="Cannot pause"):
        await engine.pause_session()


@pytest.mark.asyncio
async def test_resume_when_not_paused(engine):
    with pytest.raises(ComputeForgeError, match="Cannot resume"):
        await engine.resume_session()


@pytest.mark.asyncio
async def test_stop_session(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        await engine.stop_session()
        assert engine.state == EngineState.STOPPED
        assert engine._browser is None


@pytest.mark.asyncio
async def test_execute_while_stopped(engine):
    with pytest.raises(SessionNotActive, match="No active session"):
        await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_execute_string_action_type(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        result = await engine.execute("screenshot")
        assert result.success


@pytest.mark.asyncio
async def test_execute_invalid_string_action_type(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        with pytest.raises(ActionFailed, match="Unknown action type"):
            await engine.execute("not_an_action")


@pytest.mark.asyncio
async def test_execute_max_actions_limit(engine):
    config = SessionConfig(headless=True, max_actions=1)
    await engine.create_session(config)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        await engine.execute(ActionType.SCREENSHOT)
        with pytest.raises(ActionFailed, match="Max actions limit"):
            await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_execute_timeout(engine):
    config = SessionConfig(headless=True, timeout_seconds=1)
    await engine.create_session(config)
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._metrics.start_time = 0.001
        with patch("computeforge.core.engine.time.time", return_value=99999.0):
            with pytest.raises(ActionFailed, match="Session timeout"):
                await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_execute_success_with_hooks(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        hook_called = False
        async def pre_hook(req):
            nonlocal hook_called
            hook_called = True
        engine.register_pre_action_hook(pre_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success
        assert hook_called


@pytest.mark.asyncio
async def test_safety_hook_blocks(engine):
    engine.config.safety.enabled = True
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def safety_hook(req):
            raise SafetyBlocked("test", "blocked")
        engine.register_safety_hook(safety_hook)
        with pytest.raises(SafetyBlocked):
            await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_pre_action_hook_blocks(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def pre_hook(req):
            raise SafetyBlocked("test", "blocked")
        engine.register_pre_action_hook(pre_hook)
        with pytest.raises(SafetyBlocked):
            await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_post_action_hooks(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        hook_called = False
        async def post_hook(req, res):
            nonlocal hook_called
            hook_called = True
        engine.register_post_action_hook(post_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success
        assert hook_called


@pytest.mark.asyncio
async def test_observability_hooks(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        hook_called = False
        async def obs_hook(req, res):
            nonlocal hook_called
            hook_called = True
        engine.register_observability_hook(obs_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success
        assert hook_called


@pytest.mark.asyncio
async def test_on_error_hooks(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        error_caught = None
        async def err_hook(error, ctx):
            nonlocal error_caught
            error_caught = error
        engine.register_on_error_hook(err_hook)
        engine._browser.execute_action = AsyncMock(side_effect=ElementNotFound("test", "css", ""))
        with pytest.raises(ElementNotFound):
            await engine.execute(ActionType.NAVIGATE, url="https://example.com")
        assert error_caught is not None


@pytest.mark.asyncio
async def test_on_state_change_hooks(engine):
    state_changes = []
    async def state_hook(new_state):
        state_changes.append(new_state)
    engine.register_on_state_change_hook(state_hook)
    await engine.create_session(SessionConfig(headless=True))
    assert EngineState.STOPPED in state_changes


@pytest.mark.asyncio
async def test_execute_batch(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        actions = [
            {"type": "screenshot", "params": {}},
            {"type": "screenshot", "params": {}},
        ]
        results = await engine.execute_batch(actions)
        assert len(results) == 2
        assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_execute_batch_stop_on_failure(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._browser.execute_action = AsyncMock(side_effect=[ActionResult(success=True, action_type=ActionType.SCREENSHOT), ElementNotFound("x", "css", "")])
        actions = [
            {"type": "screenshot", "params": {}, "stop_on_failure": True},
            {"type": "navigate", "params": {"url": "https://example.com"}, "stop_on_failure": True},
        ]
        results = await engine.execute_batch(actions)
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success


@pytest.mark.asyncio
async def test_execute_action_request(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        request = ActionRequest(type=ActionType.SCREENSHOT)
        result = await engine.execute_action_request(request)
        assert result.success


@pytest.mark.asyncio
async def test_get_state(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        state = await engine.get_state()
        assert state["state"] == "running"
        assert state["session_id"] == engine._session.id
        assert "metrics" in state


@pytest.mark.asyncio
async def test_metrics_initial():
    m = EngineMetrics()
    assert m.total_actions == 0
    assert m.successful_actions == 0
    assert m.failed_actions == 0
    assert m.retried_actions == 0


@pytest.mark.asyncio
async def test_metrics_record_action():
    m = EngineMetrics()
    m.record_action(100.0, success=True, retried=False)
    assert m.total_actions == 1
    assert m.successful_actions == 1
    assert m.avg_action_duration_ms == 100.0
    m.record_action(50.0, success=False, retried=True)
    assert m.total_actions == 2
    assert m.failed_actions == 1
    assert m.retried_actions == 1


@pytest.mark.asyncio
async def test_session_property_raises_when_none(engine):
    with pytest.raises(SessionNotActive, match="No active session"):
        _ = engine.session


@pytest.mark.asyncio
async def test_browser_property_raises_when_none(engine):
    with pytest.raises(SessionNotActive, match="Browser not initialized"):
        _ = engine.browser


@pytest.mark.asyncio
async def test_context_manager():
    config = EngineConfig()
    config.safety.enabled = False
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        async with ComputeEngine(config=config) as eng:
            assert eng.state == EngineState.RUNNING
        assert eng.state == EngineState.STOPPED


@pytest.mark.asyncio
async def test_convenience_methods(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        for method in ["navigate", "click", "screenshot"]:
            if method == "navigate":
                result = await engine.navigate("https://example.com")
            elif method == "click":
                result = await engine.click("div")
            else:
                result = await engine.screenshot()
            assert result.success


@pytest.mark.asyncio
async def test_state_properties(engine):
    assert engine.state == EngineState.STOPPED
    assert not engine.is_running
    assert not engine.is_paused


@pytest.mark.asyncio
async def test_metrics_property(engine):
    assert engine.metrics is not None
    assert engine.metrics.total_actions == 0


@pytest.mark.asyncio
async def test_create_session_existing_session(engine):
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.create_session(SessionConfig(headless=True))
        await engine.start_session()
        session2 = await engine.create_session(SessionConfig(headless=True))
        assert session2 is not None


@pytest.mark.asyncio
async def test_stop_session_browser_error(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._browser.stop = AsyncMock(side_effect=Exception("Stop error"))
        await engine.stop_session()
        assert engine.state == EngineState.STOPPED


@pytest.mark.asyncio
async def test_execute_while_paused_then_resume(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        await engine.pause_session()
        async def resume_soon():
            await asyncio.sleep(0.01)
            await engine.resume_session()
        asyncio.create_task(resume_soon())
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_execute_in_error_state(engine):
    await engine.create_session(SessionConfig(headless=True))
    engine._state = EngineState.ERROR
    with pytest.raises(SessionNotActive, match="Engine not running"):
        await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_pre_action_hook_error_logged(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def bad_hook(req):
            raise ValueError("Hook error")
        engine.register_pre_action_hook(bad_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_safety_hook_error_logged(engine):
    engine.config.safety.enabled = True
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def bad_hook(req):
            raise ValueError("Safety error")
        engine.register_safety_hook(bad_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_post_action_hook_error_logged(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def bad_hook(req, res):
            raise ValueError("Post error")
        engine.register_post_action_hook(bad_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_observability_hook_error_logged(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def bad_hook(req, res):
            raise ValueError("Obs error")
        engine.register_observability_hook(bad_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_execute_generic_exception_raises_action_failed(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._browser.execute_action = AsyncMock(return_value="not_an_action_result")
        with pytest.raises(ActionFailed):
            await engine.execute(ActionType.SCREENSHOT)


@pytest.mark.asyncio
async def test_execute_batch_with_exception(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._browser.execute_action = AsyncMock(side_effect=RuntimeError("Batch error"))
        actions = [
            {"type": "screenshot", "params": {}},
        ]
        results = await engine.execute_batch(actions)
        assert len(results) == 1
        assert not results[0].success


@pytest.mark.asyncio
async def test_execute_batch_early_stop_on_failure(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        engine._browser.execute_action = AsyncMock(return_value=ActionResult(success=False, action_type=ActionType.SCREENSHOT, error="fail"))
        actions = [
            {"type": "screenshot", "params": {}, "stop_on_failure": True},
        ]
        results = await engine.execute_batch(actions)
        assert len(results) == 1
        assert not results[0].success


@pytest.mark.asyncio
async def test_type_text_convenience(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        result = await engine.type_text("hello")
        assert result.success


@pytest.mark.asyncio
async def test_scroll_convenience(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        result = await engine.scroll()
        assert result.success


@pytest.mark.asyncio
async def test_run_hook_sync_function(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        calls = []
        def sync_hook(req):
            calls.append("called")
        engine.register_pre_action_hook(sync_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_hook_sync_exception(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        def bad_sync_hook(req):
            raise ValueError("Sync hook error")
        engine.register_pre_action_hook(bad_sync_hook)
        result = await engine.execute(ActionType.SCREENSHOT)
        assert result.success


@pytest.mark.asyncio
async def test_handle_error_hook_exception(engine):
    engine.config.safety.enabled = True
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
        async def bad_error_hook(error, ctx):
            raise RuntimeError("Hook error in error handler")
        engine.register_on_error_hook(bad_error_hook)
        engine._browser.execute_action = AsyncMock(side_effect=ElementNotFound("test", "css", ""))
        with pytest.raises(ElementNotFound):
            await engine.execute(ActionType.NAVIGATE, url="https://example.com")


@pytest.mark.asyncio
async def test_dispatch_state_change_hook_exception(engine):
    async def bad_hook(state):
        raise RuntimeError("State hook error")
    engine.register_on_state_change_hook(bad_hook)
    session = await engine.create_session(SessionConfig(headless=True))
    assert session is not None


@pytest.mark.asyncio
async def test_browser_property_when_set(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
    assert engine.browser is not None


@pytest.mark.asyncio
async def test_extract_text_convenience(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
    result = await engine.extract_text()
    assert result.success


@pytest.mark.asyncio
async def test_get_page_info(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()
    info = await engine.get_page_info()
    assert "url" in info
    assert "title" in info


@pytest.mark.asyncio
async def test_handle_error_safety_blocked_hook(engine):
    await engine.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await engine.start_session()

    async def raising_hook(error, ctx):
        raise SafetyBlocked("test", "blocked")
    engine.register_on_error_hook(raising_hook)
    engine._browser.execute_action = AsyncMock(side_effect=ElementNotFound("test", "css", ""))
    with pytest.raises(ElementNotFound):
        await engine.execute(ActionType.NAVIGATE, url="https://example.com")


@pytest.mark.asyncio
async def test_dispatch_state_change_safety_blocked_hook(engine):
    async def raising_hook(state):
        raise SafetyBlocked("test", "blocked")
    engine.register_on_state_change_hook(raising_hook)
    session = await engine.create_session(SessionConfig(headless=True))
    assert session is not None
