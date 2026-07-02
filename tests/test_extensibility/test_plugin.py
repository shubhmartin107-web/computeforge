from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.extensibility.plugin import (
    PluginBase,
    PluginLoader,
    PluginManifest,
    PluginMeta,
    PluginValidator,
)


def test_plugin_base_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        PluginBase()


class GoodPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(name="good", version="1.0.0", description="A good plugin")


class BadPlugin:
    pass


def test_plugin_meta_dataclass():
    meta = PluginMeta(name="test", version="1.0.0", description="desc", author="me")
    assert meta.name == "test"
    assert meta.version == "1.0.0"
    assert meta.description == "desc"
    assert meta.author == "me"
    assert meta.tags == []


def test_plugin_manifest_dataclass():
    manifest = PluginManifest(
        name="test",
        version="1.0.0",
        description="desc",
        author="me",
        tags=["tag1"],
        permissions=["network"],
    )
    assert manifest.name == "test"
    assert manifest.version == "1.0.0"
    assert manifest.author == "me"
    assert manifest.tags == ["tag1"]
    assert manifest.permissions == ["network"]
    assert manifest.license == "MIT"


def test_plugin_loader_initialization():
    loader = PluginLoader()
    assert loader._plugin_dirs == []
    assert loader._watched_files == {}


@patch("importlib.metadata.entry_points")
def test_discover_entry_points(mock_entry_points):
    mock_ep = MagicMock()
    mock_ep.name = "good"
    mock_ep.load.return_value = GoodPlugin
    mock_entry_points.return_value = [mock_ep]

    loader = PluginLoader()
    classes = loader.discover_entry_points()
    assert len(classes) == 1
    assert classes[0] is GoodPlugin


@patch("importlib.metadata.entry_points")
def test_discover_entry_points_validation_fails(mock_entry_points):
    mock_ep = MagicMock()
    mock_ep.name = "bad"
    mock_ep.load.return_value = BadPlugin
    mock_entry_points.return_value = [mock_ep]

    loader = PluginLoader()
    classes = loader.discover_entry_points()
    assert len(classes) == 0


def test_discover_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_code = """
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class TempPlugin(PluginBase):
    def get_meta(self):
        return PluginMeta(name="temp", version="0.1.0", description="temp plugin")
"""
        plugin_path = os.path.join(tmpdir, "myplugin.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_code)

        loader = PluginLoader()
        classes = loader.discover_directory(tmpdir)
        assert len(classes) == 1
        assert classes[0].__name__ == "TempPlugin"


def test_discover_directory_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PluginLoader()
        classes = loader.discover_directory(tmpdir)
        assert classes == []


def test_discover_directory_non_existent():
    loader = PluginLoader()
    classes = loader.discover_directory("/nonexistent/path")
    assert classes == []


def test_hot_reload_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_code = """
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class ReloadPlugin(PluginBase):
    def get_meta(self):
        return PluginMeta(name="reload", version="0.1.0", description="reloadable")
"""
        plugin_path = os.path.join(tmpdir, "reloadable.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_code)

        loader = PluginLoader()
        loader.add_plugin_dir(tmpdir)
        first = loader.discover_directory(tmpdir)
        assert len(first) == 1

        initial_mtime = os.path.getmtime(plugin_path)
        assert loader._watched_files[plugin_path] == initial_mtime

        os.utime(plugin_path, (initial_mtime + 10, initial_mtime + 10))
        changed = loader.check_hot_reload()
        assert len(changed) == 1


def test_add_plugin_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PluginLoader()
        loader.add_plugin_dir(tmpdir)
        assert tmpdir in loader._plugin_dirs


def test_add_plugin_dir_duplicate():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PluginLoader()
        loader.add_plugin_dir(tmpdir)
        loader.add_plugin_dir(tmpdir)
        assert loader._plugin_dirs.count(tmpdir) == 1


def test_plugin_validator_validate_manifest():
    manifest = PluginManifest(name="", version="", description="", author="")
    errors = PluginValidator.validate_manifest(manifest)
    assert len(errors) == 4

    manifest = PluginManifest(name="ok", version="1.0", description="desc", author="me")
    errors = PluginValidator.validate_manifest(manifest)
    assert errors == []


def test_plugin_validator_validate_class():
    errors = PluginValidator.validate_class(PluginBase)
    assert "Cannot instantiate PluginBase directly" in errors

    errors = PluginValidator.validate_class(GoodPlugin)
    assert errors == []

    errors = PluginValidator.validate_class(BadPlugin)
    assert "BadPlugin does not extend PluginBase" in errors


def test_load_plugins():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_code = """
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class LoadablePlugin(PluginBase):
    def get_meta(self):
        return PluginMeta(name="loadable", version="1.0.0", description="loadable plugin")
"""
        plugin_path = os.path.join(tmpdir, "loadable.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_code)

        loader = PluginLoader()
        loader.add_plugin_dir(tmpdir)
        instances = loader.load_plugins()
        assert len(instances) == 1
        assert instances[0].get_meta().name == "loadable"


@pytest.mark.asyncio
async def test_plugin_lifecycle_methods():
    plugin = GoodPlugin()
    meta = plugin.get_meta()
    assert meta.name == "good"

    await plugin.on_load()
    await plugin.on_unload()
    await plugin.on_activate()
    await plugin.on_deactivate()

    request = ActionRequest(type=ActionType.SCREENSHOT)
    result = await plugin.on_action_before(request)
    assert result is request

    action_result = ActionResult(success=True, action_type=ActionType.SCREENSHOT)
    await plugin.on_action_after(request, action_result)
    await plugin.on_session_start("session-1", {})
    await plugin.on_session_end("session-1", "completed")
    await plugin.on_error(ValueError("test"), {})
    await plugin.on_config_change({})
    await plugin.on_tick()


class CallsSuperGetMeta(PluginBase):
    def get_meta(self) -> PluginMeta:
        super().get_meta()
        return PluginMeta(name="super", version="1.0.0", description="calls super")


def test_plugin_base_get_meta_abstract_body():
    plugin = CallsSuperGetMeta()
    meta = plugin.get_meta()
    assert meta.name == "super"


def test_plugin_base_get_manifest_none():
    plugin = GoodPlugin()
    assert plugin.get_manifest() is None


@patch("importlib.metadata.entry_points")
def test_discover_entry_points_import_error(mock_entry_points):
    mock_entry_points.side_effect = Exception("importlib error")
    loader = PluginLoader()
    classes = loader.discover_entry_points()
    assert classes == []


def test_discover_directory_load_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_plugin = os.path.join(tmpdir, "borked.py")
        with open(bad_plugin, "w") as f:
            f.write("this is not valid python {{{")
        loader = PluginLoader()
        classes = loader.discover_directory(tmpdir)
        assert classes == []


def test_discover_directory_validation_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_code = """
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class NotAPlugin:
    pass
"""
        plugin_path = os.path.join(tmpdir, "invalid.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_code)

        loader = PluginLoader()
        classes = loader.discover_directory(tmpdir)
        assert classes == []


@patch("importlib.metadata.entry_points")
def test_discover_entry_points_load_fails(mock_entry_points):
    mock_ep = MagicMock()
    mock_ep.name = "broken"
    mock_ep.load.side_effect = ImportError("broken package")
    mock_entry_points.return_value = [mock_ep]

    loader = PluginLoader()
    classes = loader.discover_entry_points()
    assert classes == []


def test_hot_reload_non_existent_dir():
    loader = PluginLoader()
    loader._plugin_dirs.append("/nonexistent/plugins")
    changed = loader.check_hot_reload()
    assert changed == []


class ManifestFailPlugin(PluginBase):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(name="mfail", version="", description="", author="")

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(name="mfail", version="", description="", author="")


def test_instantiate_with_bad_manifest():
    loader = PluginLoader()
    instances = loader._instantiate_plugins([ManifestFailPlugin])
    assert len(instances) == 1


class CrashOnInitPlugin(PluginBase):
    def __init__(self):
        raise RuntimeError("init crash")

    def get_meta(self) -> PluginMeta:
        return PluginMeta(name="crash", version="1.0.0", description="crashes")


def test_instantiate_plugin_error():
    loader = PluginLoader()
    instances = loader._instantiate_plugins([CrashOnInitPlugin])
    assert instances == []
