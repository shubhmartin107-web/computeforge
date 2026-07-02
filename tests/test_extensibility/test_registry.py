from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.extensibility.plugin import PluginBase, PluginMeta
from computeforge.extensibility.registry import PluginRegistry


class MockPlugin(PluginBase):
    def __init__(self, name: str = "mock", version: str = "1.0.0", **kwargs):
        super().__init__()
        self._meta = PluginMeta(name=name, version=version, description="mock plugin", **kwargs)
        self.on_load_called = False
        self.on_unload_called = False
        self.on_action_before_called = False
        self.on_action_after_called = False
        self.on_session_start_called = False
        self.on_session_end_called = False
        self.on_error_called = False
        self.before_return = None

    def get_meta(self) -> PluginMeta:
        return self._meta

    async def on_load(self) -> None:
        self.on_load_called = True

    async def on_unload(self) -> None:
        self.on_unload_called = True

    async def on_action_before(self, request: ActionRequest) -> ActionRequest | None:
        self.on_action_before_called = True
        return self.before_return

    async def on_action_after(self, request: ActionRequest, result: ActionResult) -> None:
        self.on_action_after_called = True

    async def on_session_start(self, session_id: str, config: dict) -> None:
        self.on_session_start_called = True

    async def on_session_end(self, session_id: str, status: str) -> None:
        self.on_session_end_called = True

    async def on_error(self, error: Exception, context: dict) -> None:
        self.on_error_called = True


class FailingPlugin(PluginBase):
    def __init__(self, name: str = "failing"):
        super().__init__()
        self._meta = PluginMeta(name=name, version="1.0.0", description="failing plugin")

    def get_meta(self) -> PluginMeta:
        return self._meta

    async def on_action_before(self, request: ActionRequest) -> ActionRequest | None:
        raise RuntimeError("plugin failed")

    async def on_action_after(self, request: ActionRequest, result: ActionResult) -> None:
        raise RuntimeError("plugin failed")

    async def on_session_start(self, session_id: str, config: dict) -> None:
        raise RuntimeError("plugin failed")

    async def on_session_end(self, session_id: str, status: str) -> None:
        raise RuntimeError("plugin failed")

    async def on_error(self, error: Exception, context: dict) -> None:
        raise RuntimeError("plugin failed")

    async def on_load(self) -> None:
        raise RuntimeError("plugin failed")


def test_registry_singleton():
    PluginRegistry._instance = None
    r1 = PluginRegistry()
    r2 = PluginRegistry()
    assert r1 is r2


def test_registry_initialization():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    assert registry._plugins == {}
    assert registry._plugin_meta == {}


def test_register_and_get():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="test_plugin")
    registry.register(plugin)
    assert registry.get("test_plugin") is plugin
    assert registry.get("test_plugin") is not None
    assert registry.get("nonexistent") is None


def test_register_duplicate_overwrites():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    p1 = MockPlugin(name="dup")
    p2 = MockPlugin(name="dup")
    registry.register(p1)
    registry.register(p2)
    assert registry.get("dup") is p2


def test_unregister():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="remove_me")
    registry.register(plugin)
    assert "remove_me" in registry._plugins
    registry.unregister("remove_me")
    assert registry.get("remove_me") is None
    assert "remove_me" not in registry._plugins


def test_unregister_nonexistent():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    registry.unregister("nope")
    assert registry.get("nope") is None


def test_plugins_property():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="prop_test")
    registry.register(plugin)
    plugins = registry.plugins
    assert "prop_test" in plugins
    assert plugins["prop_test"] is plugin
    plugins["prop_test"] = None
    assert registry._plugins["prop_test"] is not None


def test_list_plugins():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    p1 = MockPlugin(name="p1")
    p2 = MockPlugin(name="p2")
    registry.register(p1)
    registry.register(p2)
    metas = registry.list_plugins()
    assert len(metas) == 2
    names = [m.name for m in metas]
    assert "p1" in names
    assert "p2" in names


def test_get_meta():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="meta_test")
    registry.register(plugin)
    meta = registry.get_meta("meta_test")
    assert meta is not None
    assert meta.name == "meta_test"


def test_get_meta_nonexistent():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    assert registry.get_meta("nope") is None


@pytest.mark.asyncio
async def test_dispatch_action_before():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="before_test")
    registry.register(plugin)
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = await registry.dispatch_action_before(request)
    assert plugin.on_action_before_called
    assert result is request


@pytest.mark.asyncio
async def test_dispatch_action_before_modifies_request():
    PluginRegistry._instance = None
    registry = PluginRegistry()

    class ModifyingPlugin(PluginBase):
        def __init__(self):
            self._meta = PluginMeta(name="modifier", version="1.0", description="mod")

        def get_meta(self) -> PluginMeta:
            return self._meta

        async def on_action_before(self, request: ActionRequest) -> ActionRequest | None:
            request.params["modified"] = True
            return request

    registry.register(ModifyingPlugin())
    request = ActionRequest(type=ActionType.NAVIGATE, params={"url": "https://example.com"})
    result = await registry.dispatch_action_before(request)
    assert result.params.get("modified") is True


@pytest.mark.asyncio
async def test_dispatch_action_before_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good")
    bad = FailingPlugin(name="bad")
    registry.register(bad)
    registry.register(good)
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = await registry.dispatch_action_before(request)
    assert good.on_action_before_called
    assert result is not None


@pytest.mark.asyncio
async def test_dispatch_action_after():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="after_test")
    registry.register(plugin)
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = ActionResult(success=True, action_type=ActionType.SCREENSHOT)
    await registry.dispatch_action_after(request, result)
    assert plugin.on_action_after_called


@pytest.mark.asyncio
async def test_dispatch_action_after_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good_after")
    bad = FailingPlugin(name="bad_after")
    registry.register(bad)
    registry.register(good)
    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = ActionResult(success=True, action_type=ActionType.SCREENSHOT)
    await registry.dispatch_action_after(request, result)
    assert good.on_action_after_called


@pytest.mark.asyncio
async def test_dispatch_session_start():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="session_start_test")
    registry.register(plugin)
    await registry.dispatch_session_start("session-1", {"key": "val"})
    assert plugin.on_session_start_called


@pytest.mark.asyncio
async def test_dispatch_session_start_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good_ss")
    bad = FailingPlugin(name="bad_ss")
    registry.register(bad)
    registry.register(good)
    await registry.dispatch_session_start("session-1", {"key": "val"})
    assert good.on_session_start_called


@pytest.mark.asyncio
async def test_dispatch_session_end():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="session_end_test")
    registry.register(plugin)
    await registry.dispatch_session_end("session-1", "completed")
    assert plugin.on_session_end_called


@pytest.mark.asyncio
async def test_dispatch_session_end_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good_se")
    bad = FailingPlugin(name="bad_se")
    registry.register(bad)
    registry.register(good)
    await registry.dispatch_session_end("session-1", "completed")
    assert good.on_session_end_called


@pytest.mark.asyncio
async def test_dispatch_error():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    plugin = MockPlugin(name="error_test")
    registry.register(plugin)
    await registry.dispatch_error(ValueError("oops"), {"key": "val"})
    assert plugin.on_error_called


@pytest.mark.asyncio
async def test_dispatch_error_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good_err")
    bad = FailingPlugin(name="bad_err")
    registry.register(bad)
    registry.register(good)
    await registry.dispatch_error(ValueError("oops"), {"key": "val"})
    assert good.on_error_called


@pytest.mark.asyncio
async def test_plugin_isolation():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good")
    bad = FailingPlugin(name="bad")
    registry.register(good)
    registry.register(bad)

    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = await registry.dispatch_action_before(request)
    assert good.on_action_before_called
    assert result is not None


@pytest.mark.asyncio
async def test_load_all():
    PluginRegistry._instance = None
    registry = PluginRegistry()

    plugin = MockPlugin(name="load_all_test")
    registry.register(plugin)
    await registry.load_all()
    assert plugin.on_load_called


@pytest.mark.asyncio
async def test_load_all_failing_continues():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    good = MockPlugin(name="good_load")
    bad = FailingPlugin(name="bad_load")
    registry.register(bad)
    registry.register(good)
    await registry.load_all()
    assert good.on_load_called


@pytest.mark.asyncio
async def test_add_plugin_dir():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    with patch.object(registry._loader, "add_plugin_dir") as mock_add:
        registry.add_plugin_dir("/some/path")
        mock_add.assert_called_once_with("/some/path")


def test_discover_and_load():
    PluginRegistry._instance = None
    registry = PluginRegistry()
    with patch.object(registry._loader, "load_plugins", return_value=[MockPlugin(name="discovered")]):
        metas = registry.discover_and_load()
        assert len(metas) == 1
        assert metas[0].name == "discovered"
        assert registry.get("discovered") is not None
