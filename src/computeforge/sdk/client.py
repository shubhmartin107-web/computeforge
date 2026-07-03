from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from computeforge.core.actions import ActionResult, ActionType
from computeforge.core.engine import ComputeEngine
from computeforge.core.exceptions import ComputeForgeError
from computeforge.models.config import EngineConfig
from computeforge.models.session import Session, SessionConfig
from computeforge.observability.recorder import SessionRecorder
from computeforge.observability.replay import ReplayEngine
from computeforge.observability.storage import StorageBackend
from computeforge.sdk.progress import ActionProgress, ProgressCallback

logger = logging.getLogger("computeforge.sdk.client")


@dataclass
class BatchResult:
    """Result of a batch action execution."""

    results: list[ActionResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    succeeded: int = 0
    failed: int = 0
    completed: bool = True
    error: str | None = None


class ComputeForgeClient:
    """Enterprise-grade Python SDK for ComputeForge.

    Features:
    - Full session lifecycle management
    - Batch operations with progress tracking
    - Session export/import
    - Async iterator support for real-time monitoring
    - Integrated safety and observability
    - Connection pooling
    - Comprehensive error handling
    """

    def __init__(
        self,
        config: EngineConfig | None = None,
        storage: StorageBackend | None = None,
        auto_connect: bool = False,
    ):
        self._config = config or EngineConfig()
        self._storage = storage
        self._engine: ComputeEngine | None = None
        self._recorder: SessionRecorder | None = None
        self._replay: ReplayEngine | None = None
        self._owns_storage = storage is None
        self._connected = False
        self._progress_callbacks: list[ProgressCallback] = []

        if auto_connect:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.connect())  # noqa: RUF006
            else:
                loop.run_until_complete(self.connect())

    @property
    def engine(self) -> ComputeEngine | None:
        return self._engine

    @property
    def storage(self) -> StorageBackend | None:
        return self._storage

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_session_active(self) -> bool:
        return self._engine is not None and self._engine.is_running

    def add_progress_callback(self, callback: ProgressCallback) -> None:
        self._progress_callbacks.append(callback)

    # ─── Connection ──────────────────────────────────────────────────

    async def connect(self) -> None:
        if self._connected:
            return
        if self._storage is None:
            self._storage = StorageBackend()
        await self._storage.connect()
        self._connected = True
        logger.info("SDK client connected")

    async def close(self) -> None:
        if self._engine:
            await self._engine.stop_session()
            self._engine = None
        if self._recorder:
            await self._recorder.close()
            self._recorder = None
        if self._storage and self._owns_storage:
            await self._storage.close()
        self._connected = False
        logger.info("SDK client closed")

    # ─── Session Management ──────────────────────────────────────────

    async def create_session(self, config: SessionConfig | None = None) -> Session:
        """Create and start a new computer-use session."""
        if not self._connected:
            await self.connect()

        self._engine = ComputeEngine(config=self._config)
        session = await self._engine.create_session(config or SessionConfig())

        # Set up recorder
        self._recorder = SessionRecorder(storage=self._storage)
        await self._recorder.connect()
        await self._recorder.record_session_create(session)

        # Wire up hooks
        _, post_hook, _ = self._recorder.make_recorder_hooks()
        self._engine.register_post_action_hook(post_hook)

        # Start the browser
        await self._engine.start_session()

        logger.info(f"Session created: {session.id[:8]}...")
        return session

    async def get_session(self, session_id: str) -> Session:
        assert self._storage is not None
        return await self._storage.load_session(session_id)

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Session]:
        if self._storage:
            return await self._storage.list_sessions(limit=limit, offset=offset, status=status)
        return []

    async def delete_session(self, session_id: str) -> None:
        assert self._storage is not None
        await self._storage.delete_session(session_id)

    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        assert self._storage is not None
        replay = ReplayEngine(storage=self._storage)
        return await replay.get_session_summary(session_id)

    async def export_session(self, session_id: str, output_path: str | Path | None = None) -> str:
        """Export a session to JSON."""
        assert self._storage is not None
        json_str = await self._storage.export_session_json(session_id)
        if output_path:
            Path(output_path).write_text(json_str)
        return json_str

    async def import_session(self, json_str: str) -> str:
        """Import a session from JSON."""
        assert self._storage is not None
        return await self._storage.import_session_json(json_str)

    async def get_engine_state(self) -> dict[str, Any]:
        if self._engine:
            return await self._engine.get_state()
        return {"state": "stopped", "session_id": None}

    # ─── Single Actions ──────────────────────────────────────────────

    async def navigate(self, url: str) -> ActionResult:
        return await self._execute(ActionType.NAVIGATE, url=url)

    async def click(self, selector: str, strategy: str = "css", **kwargs) -> ActionResult:
        return await self._execute(ActionType.CLICK, selector=selector, strategy=strategy, **kwargs)

    async def type_text(self, text: str, selector: str | None = None, **kwargs) -> ActionResult:
        return await self._execute(ActionType.TYPE, text=text, selector=selector, **kwargs)

    async def screenshot(self, **kwargs) -> ActionResult:
        return await self._execute(ActionType.SCREENSHOT, **kwargs)

    async def scroll(self, delta_y: int = 300, **kwargs) -> ActionResult:
        return await self._execute(ActionType.SCROLL, delta_y=delta_y, **kwargs)

    async def extract_text(self, selector: str | None = None, **kwargs) -> ActionResult:
        return await self._execute(ActionType.EXTRACT_TEXT, selector=selector, **kwargs)

    async def extract_html(self, selector: str | None = None, **kwargs) -> ActionResult:
        return await self._execute(ActionType.EXTRACT_HTML, selector=selector, **kwargs)

    async def evaluate(self, script: str) -> ActionResult:
        return await self._execute(ActionType.EVALUATE, script=script)

    async def hover(self, selector: str) -> ActionResult:
        return await self._execute(ActionType.HOVER, selector=selector)

    async def wait(self, timeout_ms: int = 1000) -> ActionResult:
        return await self._execute(ActionType.WAIT, timeout_ms=timeout_ms)

    # ─── Batch Operations ────────────────────────────────────────────

    async def run_actions(self, actions: list[dict[str, Any]]) -> BatchResult:
        """Run a sequence of actions with progress tracking."""
        results: list[ActionResult] = []
        start = time.time()

        for i, action in enumerate(actions):
            progress = ActionProgress(
                total=len(actions),
                current=i,
                current_action=action.get("type", "unknown"),
            )
            await self._notify_progress(progress)

            try:
                atype = ActionType(action["type"])
                params = action.get("params", {})
                result = await self._execute(atype, **params)
                results.append(result)
                if not result.success and action.get("stop_on_failure", True):
                    logger.info(f"Batch stopped at action {i} due to failure")
                    break
            except Exception as e:
                results.append(
                    ActionResult(
                        success=False,
                        action_type=ActionType(action.get("type", "screenshot")),
                        error=str(e),
                    )
                )
                break

        duration = (time.time() - start) * 1000
        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        await self._notify_progress(
            ActionProgress(
                total=len(actions),
                current=len(results),
                current_action="done",
                complete=True,
            )
        )

        return BatchResult(
            results=results,
            total_duration_ms=duration,
            succeeded=succeeded,
            failed=failed,
            completed=len(results) == len(actions),
        )

    async def run_workflow(self, workflow_actions: list[dict[str, Any]]) -> BatchResult:
        """Alias for run_actions for workflow compatibility."""
        return await self.run_actions(workflow_actions)

    async def navigate_and_extract(self, url: str) -> dict[str, Any]:
        """Convenience: navigate and extract text."""
        nav_result = await self.navigate(url)
        if not nav_result.success:
            return {"success": False, "error": nav_result.error}
        text_result = await self.extract_text()
        return {
            "success": True,
            "url": nav_result.data.get("url") if nav_result.data else url,
            "title": nav_result.data.get("title") if nav_result.data else "",
            "text": text_result.data.get("text", "") if text_result.success else "",
        }

    # ─── Internal ────────────────────────────────────────────────────

    async def _execute(self, action_type: ActionType, **params) -> ActionResult:
        if self._engine is None:
            raise ComputeForgeError("No active session. Call create_session() first.")

        try:
            result = await self._engine.execute(action_type, **params)
        except ComputeForgeError as e:
            result = ActionResult(success=False, action_type=action_type, error=str(e))

        if self._recorder and self._engine.session:
            from computeforge.core.actions import ActionRequest

            req = ActionRequest(type=action_type, params=params)
            await self._recorder.record_action(req, result=result)

        return result

    async def _notify_progress(self, progress: ActionProgress) -> None:
        for cb in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(progress)
                else:
                    cb(progress)
            except Exception:  # nosec
                pass

    # ─── Async Context Manager ───────────────────────────────────────

    async def __aenter__(self) -> ComputeForgeClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
