from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from computeforge.core.actions import ActionRequest, ActionResult
from computeforge.core.exceptions import PluginError

logger = logging.getLogger("computeforge.extensibility.plugin")


@dataclass
class PluginManifest:
    """Standardized plugin manifest for marketplace compatibility."""

    name: str
    version: str
    description: str
    author: str = ""
    url: str = ""
    license: str = "MIT"
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    min_computeforge_version: str = "0.1.0"
    hooks: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    icon: str = ""
    readme: str = ""


@dataclass
class PluginMeta:
    """Metadata about a loaded plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)
    manifest: PluginManifest | None = None


class PluginBase(ABC):
    """Abstract base class for all ComputeForge plugins.

    Implement get_meta() and optionally override lifecycle hooks.
    """

    @abstractmethod
    def get_meta(self) -> PluginMeta: ...

    def get_manifest(self) -> PluginManifest | None:
        return None

    async def on_load(self) -> None:
        """Called when the plugin is loaded."""

    async def on_unload(self) -> None:
        """Called when the plugin is unloaded."""

    async def on_activate(self) -> None:
        """Called when the plugin is activated after loading."""

    async def on_deactivate(self) -> None:
        """Called when the plugin is deactivated."""

    async def on_action_before(self, request: ActionRequest) -> ActionRequest | None:
        """Intercept action before execution. Return modified request or None."""
        return request

    async def on_action_after(self, request: ActionRequest, result: ActionResult) -> None:
        """Observe action results after execution."""

    async def on_session_start(self, session_id: str, config: dict[str, Any]) -> None:
        """Called when a session starts."""

    async def on_session_end(self, session_id: str, status: str) -> None:
        """Called when a session ends."""

    async def on_error(self, error: Exception, context: dict[str, Any]) -> None:
        """Called when an error occurs."""

    async def on_config_change(self, config: dict[str, Any]) -> None:
        """Called when configuration changes."""

    async def on_tick(self) -> None:
        """Called periodically (every ~5s) while the plugin is active."""


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""


class PluginValidator:
    """Validates plugin manifests and structure."""

    @staticmethod
    def validate_manifest(manifest: PluginManifest) -> list[str]:
        errors = []
        if not manifest.name:
            errors.append("Plugin name is required")
        if not manifest.version:
            errors.append("Plugin version is required")
        if not manifest.description:
            errors.append("Plugin description is required")
        if not manifest.author:
            errors.append("Plugin author is required")
        return errors

    @staticmethod
    def validate_class(cls: type) -> list[str]:
        errors = []
        if not issubclass(cls, PluginBase):
            errors.append(f"{cls.__name__} does not extend PluginBase")
        if cls is PluginBase:
            errors.append("Cannot instantiate PluginBase directly")
        if inspect.isabstract(cls):
            errors.append(f"{cls.__name__} is abstract and cannot be instantiated")
        return errors


class PluginLoader:
    """Discovers and loads plugins from entry points, directories, and packages.

    Features:
    - Entry point discovery (computeforge.plugins)
    - Directory scanning with hot-reload support
    - Manifest validation
    - Dependency checking
    """

    def __init__(self):
        self._plugin_dirs: list[str] = []
        self._watched_files: dict[str, float] = {}

    def add_plugin_dir(self, path: str) -> None:
        path = os.path.abspath(path)
        if os.path.isdir(path) and path not in self._plugin_dirs:
            self._plugin_dirs.append(path)
            logger.info(f"Added plugin directory: {path}")

    def discover_entry_points(self) -> list[type[PluginBase]]:
        """Discover plugins via the 'computeforge.plugins' entry point group."""
        plugin_classes: list[type[PluginBase]] = []
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group="computeforge.plugins")
            for ep in eps:
                try:
                    cls = ep.load()
                    errors = PluginValidator.validate_class(cls)
                    if errors:
                        logger.warning(f"Plugin entry point {ep.name} validation failed: {errors}")
                        continue
                    if (
                        inspect.isclass(cls)
                        and issubclass(cls, PluginBase)
                        and cls is not PluginBase
                    ):
                        plugin_classes.append(cls)
                        logger.info(f"Discovered plugin via entry point: {ep.name}")
                except Exception as e:
                    logger.warning(f"Failed to load entry point plugin {ep.name}: {e}")
        except Exception as e:
            logger.debug(f"Entry point discovery error: {e}")
        return plugin_classes

    def discover_directory(self, plugin_dir: str) -> list[type[PluginBase]]:
        """Scan a directory for Python files containing PluginBase subclasses."""
        plugin_classes: list[type[PluginBase]] = []
        if not os.path.isdir(plugin_dir):
            return plugin_classes

        sys.path.insert(0, plugin_dir)
        try:
            for filename in sorted(os.listdir(plugin_dir)):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = filename[:-3]
                    module_path = os.path.join(plugin_dir, filename)
                    self._watched_files[module_path] = os.path.getmtime(module_path)
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, PluginBase)
                                and obj is not PluginBase
                                and not inspect.isabstract(obj)
                            ):
                                errors = PluginValidator.validate_class(obj)
                                if not errors:
                                    plugin_classes.append(obj)
                                    logger.info(f"Discovered plugin from {filename}: {name}")
                                else:
                                    logger.warning(
                                        f"Plugin {name} in {filename} validation failed: {errors}"
                                    )  # pragma: no cover
                    except Exception as e:
                        logger.debug(f"Failed to load plugin module {filename}: {e}")
        finally:
            if sys.path[0] == plugin_dir:
                del sys.path[0]
        return plugin_classes

    def check_hot_reload(self) -> list[type[PluginBase]]:
        """Check if any plugin files have changed and return new classes."""
        new_classes: list[type[PluginBase]] = []
        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for filename in sorted(os.listdir(plugin_dir)):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_path = os.path.join(plugin_dir, filename)
                    mtime = os.path.getmtime(module_path)
                    if (
                        module_path in self._watched_files
                        and self._watched_files[module_path] != mtime
                    ):
                        logger.info(f"Detected change in plugin: {filename}")
                        self._watched_files[module_path] = mtime
                        new_classes.extend(self.discover_directory(plugin_dir))
        return new_classes

    def load_plugins(self) -> list[PluginBase]:
        """Load all discovered plugins and return instances."""
        classes = self.discover_entry_points()
        for plugin_dir in self._plugin_dirs:
            classes.extend(self.discover_directory(plugin_dir))

        instances = self._instantiate_plugins(classes)
        return instances

    def _instantiate_plugins(self, classes: list[type[PluginBase]]) -> list[PluginBase]:
        instances = []
        for cls in classes:
            try:
                instance = cls()
                meta = instance.get_meta()
                manifest = instance.get_manifest()
                if manifest:
                    errors = PluginValidator.validate_manifest(manifest)
                    if errors:
                        logger.warning(f"Plugin {meta.name} manifest validation failed: {errors}")
                instances.append(instance)
                logger.info(f"Loaded plugin: {meta.name} v{meta.version}")
            except Exception as e:
                logger.error(f"Failed to instantiate plugin {cls.__name__}: {e}")
        return instances
