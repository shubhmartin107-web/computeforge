from __future__ import annotations

import pytest

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.core.exceptions import SafetyBlocked
from computeforge.extensibility.hooks import Hook, HookPoint, HookRegistry


def test_hook_point_enum_values():
    assert HookPoint.BEFORE_ACTION.value == "before_action"
    assert HookPoint.AFTER_ACTION.value == "after_action"
    assert HookPoint.ON_ERROR.value == "on_error"
    assert HookPoint.SAFETY_CHECK.value == "safety_check"
    assert HookPoint.SESSION_START.value == "session_start"
    assert HookPoint.SESSION_END.value == "session_end"
    assert HookPoint.PROVIDER_CALL.value == "provider_call"


def test_hook_registry_initialization():
    registry = HookRegistry()
    for hp in HookPoint:
        assert hp in registry._hooks
        assert registry._hooks[hp] == []


def test_register_hook_with_priority():
    registry = HookRegistry()
    hook_a = Hook(name="a", hook_point=HookPoint.BEFORE_ACTION, callback=lambda r: r, priority=20)
    hook_b = Hook(name="b", hook_point=HookPoint.BEFORE_ACTION, callback=lambda r: r, priority=10)
    registry.register(hook_a)
    registry.register(hook_b)
    hooks = registry._hooks[HookPoint.BEFORE_ACTION]
    assert hooks[0].name == "b"
    assert hooks[1].name == "a"


@pytest.mark.asyncio
async def test_dispatch_before_action_priority_order():
    registry = HookRegistry()
    call_order = []

    async def hook_low(req: ActionRequest) -> ActionRequest:
        call_order.append("low")
        return req

    async def hook_high(req: ActionRequest) -> ActionRequest:
        call_order.append("high")
        return req

    registry.register(Hook(name="low", hook_point=HookPoint.BEFORE_ACTION, callback=hook_low, priority=20))
    registry.register(Hook(name="high", hook_point=HookPoint.BEFORE_ACTION, callback=hook_high, priority=5))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    await registry.dispatch_before_action(request)
    assert call_order == ["high", "low"]


@pytest.mark.asyncio
async def test_before_action_hook_modifies_request():
    registry = HookRegistry()

    async def mod_hook(req: ActionRequest) -> ActionRequest:
        req.params["modified"] = True
        return req

    registry.register(Hook(name="mod", hook_point=HookPoint.BEFORE_ACTION, callback=mod_hook, priority=10))
    request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    result = await registry.dispatch_before_action(request)
    assert result.params.get("modified") is True


@pytest.mark.asyncio
async def test_error_in_hook_does_not_break_others():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(req: ActionRequest) -> ActionRequest:
        raise ValueError("hook failed")

    async def good_hook(req: ActionRequest) -> ActionRequest:
        call_log.append("good")
        return req

    registry.register(Hook(name="fail", hook_point=HookPoint.BEFORE_ACTION, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.BEFORE_ACTION, callback=good_hook, priority=20))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = await registry.dispatch_before_action(request)
    assert "good" in call_log
    assert result is not None


@pytest.mark.asyncio
async def test_safety_blocked_propagates():
    registry = HookRegistry()

    async def safety_hook(req: ActionRequest) -> ActionRequest:
        raise SafetyBlocked("test", "blocked")

    registry.register(Hook(name="safety", hook_point=HookPoint.BEFORE_ACTION, callback=safety_hook, priority=10))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    with pytest.raises(SafetyBlocked):
        await registry.dispatch_before_action(request)


@pytest.mark.asyncio
async def test_dispatch_after_action():
    registry = HookRegistry()
    call_log = []

    async def after_hook(req: ActionRequest, res: ActionResult) -> None:
        call_log.append("called")

    registry.register(Hook(name="after", hook_point=HookPoint.AFTER_ACTION, callback=after_hook, priority=10))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = ActionResult(success=True, action_type=ActionType.SCREENSHOT)
    await registry.dispatch_after_action(request, result)
    assert call_log == ["called"]


@pytest.mark.asyncio
async def test_disabled_hook_is_not_dispatched():
    registry = HookRegistry()
    call_log = []

    async def disabled_hook(req: ActionRequest) -> ActionRequest:
        call_log.append("called")
        return req

    hook = Hook(name="disabled", hook_point=HookPoint.BEFORE_ACTION, callback=disabled_hook, priority=10, enabled=False)
    registry.register(hook)
    request = ActionRequest(type=ActionType.SCREENSHOT)
    await registry.dispatch_before_action(request)
    assert call_log == []


@pytest.mark.asyncio
async def test_unregister_hook():
    registry = HookRegistry()
    hook = Hook(name="remove_me", hook_point=HookPoint.BEFORE_ACTION, callback=lambda r: r, priority=10)
    registry.register(hook)
    assert len(registry._hooks[HookPoint.BEFORE_ACTION]) == 1
    registry.unregister("remove_me", HookPoint.BEFORE_ACTION)
    assert len(registry._hooks[HookPoint.BEFORE_ACTION]) == 0


def test_unregister_from_all_hook_points():
    registry = HookRegistry()
    hook_a = Hook(name="common", hook_point=HookPoint.BEFORE_ACTION, callback=lambda r: r)
    hook_b = Hook(name="common", hook_point=HookPoint.AFTER_ACTION, callback=lambda r, s: None)
    registry.register(hook_a)
    registry.register(hook_b)
    assert len(registry._hooks[HookPoint.BEFORE_ACTION]) == 1
    assert len(registry._hooks[HookPoint.AFTER_ACTION]) == 1
    registry.unregister("common")
    assert len(registry._hooks[HookPoint.BEFORE_ACTION]) == 0
    assert len(registry._hooks[HookPoint.AFTER_ACTION]) == 0


@pytest.mark.asyncio
async def test_dispatch_after_action_error_continues():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(req, res):
        raise ValueError("hook failed")

    async def good_hook(req, res):
        call_log.append("good")

    registry.register(Hook(name="fail", hook_point=HookPoint.AFTER_ACTION, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.AFTER_ACTION, callback=good_hook, priority=20))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = ActionResult(success=True, action_type=ActionType.SCREENSHOT)
    await registry.dispatch_after_action(request, result)
    assert "good" in call_log


@pytest.mark.asyncio
async def test_dispatch_safety_check():
    registry = HookRegistry()
    call_log = []

    def sync_hook(req):
        call_log.append("sync")

    async def async_hook(req):
        call_log.append("async")

    registry.register(Hook(name="sync", hook_point=HookPoint.SAFETY_CHECK, callback=sync_hook, priority=10))
    registry.register(Hook(name="async", hook_point=HookPoint.SAFETY_CHECK, callback=async_hook, priority=20))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    await registry.dispatch_safety_check(request)
    assert call_log == ["sync", "async"]


@pytest.mark.asyncio
async def test_dispatch_safety_check_blocked():
    registry = HookRegistry()

    async def blocker(req):
        raise SafetyBlocked("blocker", "blocked")

    registry.register(Hook(name="blocker", hook_point=HookPoint.SAFETY_CHECK, callback=blocker, priority=10))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    with pytest.raises(SafetyBlocked):
        await registry.dispatch_safety_check(request)


@pytest.mark.asyncio
async def test_dispatch_safety_check_error_continues():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(req):
        raise ValueError("fail")

    async def good_hook(req):
        call_log.append("good")

    registry.register(Hook(name="fail", hook_point=HookPoint.SAFETY_CHECK, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.SAFETY_CHECK, callback=good_hook, priority=20))
    request = ActionRequest(type=ActionType.SCREENSHOT)
    await registry.dispatch_safety_check(request)
    assert "good" in call_log


@pytest.mark.asyncio
async def test_dispatch_error():
    registry = HookRegistry()
    error_log = []

    async def error_hook(exc, ctx):
        error_log.append(str(exc))

    registry.register(Hook(name="handler", hook_point=HookPoint.ON_ERROR, callback=error_hook, priority=10))
    await registry.dispatch_error(ValueError("test error"), {"key": "val"})
    assert "test error" in error_log


@pytest.mark.asyncio
async def test_dispatch_error_continues():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(exc, ctx):
        raise ValueError("nested")

    async def good_hook(exc, ctx):
        call_log.append("good")

    registry.register(Hook(name="fail", hook_point=HookPoint.ON_ERROR, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.ON_ERROR, callback=good_hook, priority=20))
    await registry.dispatch_error(ValueError("original"), {})
    assert "good" in call_log


@pytest.mark.asyncio
async def test_dispatch_session_start():
    registry = HookRegistry()
    session_log = []

    def sync_hook(sid, cfg):
        session_log.append(("sync", sid))

    async def async_hook(sid, cfg):
        session_log.append(("async", sid))

    registry.register(Hook(name="sync", hook_point=HookPoint.SESSION_START, callback=sync_hook, priority=10))
    registry.register(Hook(name="async", hook_point=HookPoint.SESSION_START, callback=async_hook, priority=20))
    await registry.dispatch_session_start("session-1", {"key": "val"})
    assert ("sync", "session-1") in session_log
    assert ("async", "session-1") in session_log


@pytest.mark.asyncio
async def test_dispatch_session_start_error_continues():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(sid, cfg):
        raise ValueError("fail")

    async def good_hook(sid, cfg):
        call_log.append("good")

    registry.register(Hook(name="fail", hook_point=HookPoint.SESSION_START, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.SESSION_START, callback=good_hook, priority=20))
    await registry.dispatch_session_start("s1", {})
    assert "good" in call_log


@pytest.mark.asyncio
async def test_dispatch_session_end():
    registry = HookRegistry()
    end_log = []

    async def end_hook(sid, status):
        end_log.append((sid, status))

    registry.register(Hook(name="end", hook_point=HookPoint.SESSION_END, callback=end_hook, priority=10))
    await registry.dispatch_session_end("session-1", "completed")
    assert end_log == [("session-1", "completed")]


@pytest.mark.asyncio
async def test_dispatch_session_end_error_continues():
    registry = HookRegistry()
    call_log = []

    async def failing_hook(sid, status):
        raise ValueError("fail")

    async def good_hook(sid, status):
        call_log.append("good")

    registry.register(Hook(name="fail", hook_point=HookPoint.SESSION_END, callback=failing_hook, priority=10))
    registry.register(Hook(name="good", hook_point=HookPoint.SESSION_END, callback=good_hook, priority=20))
    await registry.dispatch_session_end("s1", "done")
    assert "good" in call_log
