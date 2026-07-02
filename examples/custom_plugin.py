"""
Custom Plugin Example

Demonstrates creating and registering a custom plugin for ComputeForge.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from computeforge.extensibility.plugin import PluginBase, PluginMeta
from computeforge.extensibility.registry import PluginRegistry
from computeforge.core.actions import ActionRequest, ActionType, ActionResult


class LoggingPlugin(PluginBase):
    """Plugin that logs all actions to a file."""

    def __init__(self):
        self._log_file = None

    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="logging-plugin",
            version="1.0.0",
            description="Logs all actions to a file for debugging",
            author="ComputeForge",
        )

    async def on_load(self) -> None:
        self._log_file = open("computeforge_actions.log", "a")
        self._log_file.write("=== ComputeForge Action Log Started ===\n")
        self._log_file.flush()

    async def on_unload(self) -> None:
        if self._log_file:
            self._log_file.write("=== ComputeForge Action Log Ended ===\n")
            self._log_file.close()

    async def on_action_before(self, request: ActionRequest) -> ActionRequest:
        self._log(f"BEFORE: {request.type} params={request.params}")
        return request

    async def on_action_after(self, request: ActionRequest, result: ActionResult) -> None:
        status = "SUCCESS" if result.success else "FAIL"
        self._log(f"AFTER: {request.type} -> {status} ({result.duration_ms:.0f}ms)")
        if result.error:
            self._log(f"  ERROR: {result.error}")

    async def on_session_start(self, session_id: str, config: dict) -> None:
        self._log(f"SESSION START: {session_id}")

    async def on_session_end(self, session_id: str, status: str) -> None:
        self._log(f"SESSION END: {session_id} status={status}")

    def _log(self, message: str) -> None:
        if self._log_file:
            self._log_file.write(f"{message}\n")
            self._log_file.flush()


async def main():
    registry = PluginRegistry()
    registry.register(LoggingPlugin())
    await registry.load_all()

    print("Plugin registered and loaded!")
    print(f"Active plugins: {[m.name for m in registry.list_plugins()]}")

    # Dispatch some test events
    req = ActionRequest(type=ActionType.SCREENSHOT, params={})
    result = ActionResult(success=True, action_type=ActionType.SCREENSHOT, data={}, duration_ms=150.0)

    req = await registry.dispatch_action_before(req)
    await registry.dispatch_action_after(req, result)
    await registry.dispatch_session_start("test-session-id", {"headless": True})

    print("Events dispatched. Check computeforge_actions.log")


if __name__ == "__main__":
    asyncio.run(main())
