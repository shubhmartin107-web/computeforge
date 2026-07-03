from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from computeforge.core.actions import (
    ActionRequest,
    ActionResult,
    ActionType,
)
from computeforge.core.browser import BrowserManager, BrowserType
from computeforge.core.desktop import (
    DesktopController,
)
from computeforge.core.exceptions import (
    ActionFailed,
    ComputeForgeError,
    ElementNotFound,
    SafetyBlocked,
    SessionNotActive,
)
from computeforge.core.recovery import RecoveryManager
from computeforge.models.config import EngineConfig
from computeforge.models.session import Session, SessionConfig, SessionStatus

logger = logging.getLogger("computeforge.core.engine")


class EngineState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class EngineMetrics:
    """Performance metrics for the engine."""

    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    retried_actions: int = 0
    total_duration_ms: float = 0.0
    avg_action_duration_ms: float = 0.0
    start_time: float = 0.0
    last_action_time: float = 0.0

    def record_action(self, duration_ms: float, success: bool, retried: bool = False) -> None:
        self.total_actions += 1
        self.total_duration_ms += duration_ms
        if success:
            self.successful_actions += 1
        else:
            self.failed_actions += 1
        if retried:
            self.retried_actions += 1
        self.avg_action_duration_ms = self.total_duration_ms / max(self.total_actions, 1)
        self.last_action_time = time.time()


class ComputeEngine:
    """Core orchestration engine for computer-use sessions.

    Features:
    - Multi-browser support (Chromium, Firefox, WebKit)
    - Automatic recovery with configurable strategies
    - Action validation and pre-flight checks
    - Comprehensive metrics and monitoring
    - Plugin/hook integration
    - Concurrent action execution support
    """

    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._browser: BrowserManager | None = None
        self._desktop: DesktopController | None = None
        self._session: Session | None = None
        self._state = EngineState.STOPPED
        self._metrics = EngineMetrics()
        self._recovery_manager = RecoveryManager()

        # Hook registries
        self._safety_hooks: list[Callable] = []
        self._observability_hooks: list[Callable] = []
        self._pre_action_hooks: list[Callable] = []
        self._post_action_hooks: list[Callable] = []
        self._on_error_hooks: list[Callable] = []
        self._on_state_change_hooks: list[Callable] = []

        # Concurrency control
        self._action_lock = asyncio.Lock()
        self._max_concurrent_actions = config.max_concurrent_actions if config else 1
        self._action_semaphore: asyncio.Semaphore | None = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        # Session limits
        self._total_actions_executed = 0

    # ─── Properties ─────────────────────────────────────────────────────

    @property
    def session(self) -> Session:
        if self._session is None:
            raise SessionNotActive("No active session. Call create_session() first.")
        return self._session

    @property
    def browser(self) -> BrowserManager:
        if self._browser is None:
            raise SessionNotActive("Browser not initialized.")
        return self._browser

    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def metrics(self) -> EngineMetrics:
        return self._metrics

    @property
    def is_running(self) -> bool:
        return (
            self._state == EngineState.RUNNING
            and self._browser is not None
            and self._browser.is_running
        )

    @property
    def is_paused(self) -> bool:
        return self._state == EngineState.PAUSED

    # ─── Hook Registration ───────────────────────────────────────────────

    def register_safety_hook(self, hook: Callable) -> None:
        self._safety_hooks.append(hook)

    def register_observability_hook(self, hook: Callable) -> None:
        self._observability_hooks.append(hook)

    def register_pre_action_hook(self, hook: Callable) -> None:
        self._pre_action_hooks.append(hook)

    def register_post_action_hook(self, hook: Callable) -> None:
        self._post_action_hooks.append(hook)

    def register_on_error_hook(self, hook: Callable) -> None:
        self._on_error_hooks.append(hook)

    def register_on_state_change_hook(self, hook: Callable) -> None:
        self._on_state_change_hooks.append(hook)

    # ─── Session Lifecycle ──────────────────────────────────────────────

    async def create_session(self, config: SessionConfig | None = None) -> Session:
        if self._session is not None and self._state != EngineState.STOPPED:
            logger.warning("Existing session active. Stopping first.")
            await self.stop_session()

        self._session = Session(config=config or SessionConfig())
        self._state = EngineState.STOPPED
        self._metrics = EngineMetrics()
        self._total_actions_executed = 0
        self._action_semaphore = asyncio.Semaphore(self._max_concurrent_actions)

        logger.info(f"Session created: {self._session.id}")
        await self._dispatch_state_change(EngineState.STOPPED)
        return self._session

    async def start_session(self, browser_type: BrowserType = BrowserType.CHROMIUM) -> Session:
        if self._session is None:
            await self.create_session()
        assert self._session is not None

        self._state = EngineState.STARTING
        await self._dispatch_state_change(EngineState.STARTING)

        try:
            if self._browser is None:
                self._browser = BrowserManager(
                    headless=self.session.config.headless,
                    viewport={
                        "width": self.session.config.viewport_width,
                        "height": self.session.config.viewport_height,
                    },
                    browser_type=browser_type,
                )
                await self._browser.start()
                self._session.start()
                self._state = EngineState.RUNNING
                self._metrics.start_time = time.time()
                logger.info(f"Session started: {self._session.id} (browser={browser_type.value})")
                await self._dispatch_state_change(EngineState.RUNNING)
            return self._session
        except Exception as e:
            self._state = EngineState.ERROR
            self._session.fail(str(e))
            await self._dispatch_state_change(EngineState.ERROR)
            raise

    async def pause_session(self) -> None:
        if self._state != EngineState.RUNNING:
            raise ComputeForgeError("Cannot pause: engine not running")
        self._state = EngineState.PAUSED
        self._pause_event.clear()
        assert self._session is not None
        self._session.pause()
        logger.info(f"Session paused: {self._session.id}")
        await self._dispatch_state_change(EngineState.PAUSED)

    async def resume_session(self) -> None:
        if self._state != EngineState.PAUSED:
            raise ComputeForgeError("Cannot resume: engine not paused")
        self._state = EngineState.RUNNING
        self._pause_event.set()
        assert self._session is not None
        self._session.resume()
        logger.info(f"Session resumed: {self._session.id}")
        await self._dispatch_state_change(EngineState.RUNNING)

    async def stop_session(self) -> None:
        self._state = EngineState.STOPPING
        await self._dispatch_state_change(EngineState.STOPPING)
        try:
            if self._browser:
                await self._browser.stop()
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
        finally:
            self._browser = None
            self._state = EngineState.STOPPED
            if self._session and self._session.status in (
                SessionStatus.RUNNING,
                SessionStatus.PAUSED,
            ):
                self._session.complete()
            logger.info(f"Session stopped: {self._session.id if self._session else 'none'}")
            await self._dispatch_state_change(EngineState.STOPPED)

    async def get_state(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "session_id": self._session.id if self._session else None,
            "session_status": self._session.status.value if self._session else None,
            "metrics": {
                "total_actions": self._metrics.total_actions,
                "successful": self._metrics.successful_actions,
                "failed": self._metrics.failed_actions,
                "retried": self._metrics.retried_actions,
                "avg_duration_ms": round(self._metrics.avg_action_duration_ms, 2),
                "total_duration_ms": round(self._metrics.total_duration_ms, 2),
                "uptime_seconds": round(time.time() - self._metrics.start_time, 2)
                if self._metrics.start_time
                else 0,
            },
            "browser_running": self._browser is not None and self._browser.is_running
            if self._browser
            else False,
            "config": self.config.model_dump() if self.config else None,
        }

    # ─── Action Execution ───────────────────────────────────────────────

    async def execute(self, action_type: ActionType | str, **params) -> ActionResult:
        if isinstance(action_type, str):
            try:
                action_type = ActionType(action_type)
            except ValueError:
                raise ActionFailed(action_type, f"Unknown action type: {action_type}") from None

        if self._state == EngineState.STOPPED:
            raise SessionNotActive("No active session. Call start_session() first.")

        if self._state == EngineState.PAUSED:
            logger.info("Engine paused, waiting for resume...")
            await self._pause_event.wait()

        if self._state != EngineState.RUNNING:
            raise SessionNotActive(f"Engine not running (state={self._state.value})")

        request = ActionRequest(type=action_type, params=params)

        if self._action_semaphore:
            await self._action_semaphore.acquire()
        try:
            async with self._action_lock:
                if (
                    self.session.config.max_actions > 0
                    and self._total_actions_executed >= self.session.config.max_actions
                ):
                    raise ActionFailed(
                        action_type.value,
                        f"Max actions limit reached ({self.session.config.max_actions})",
                    )

                if self.session.config.timeout_seconds > 0:
                    elapsed = (
                        (time.time() - self._metrics.start_time) if self._metrics.start_time else 0
                    )
                    if elapsed > self.session.config.timeout_seconds:
                        raise ActionFailed(
                            action_type.value,
                            f"Session timeout exceeded ({self.session.config.timeout_seconds}s)",
                        )

                start_time = time.time()

                try:
                    for hook in self._pre_action_hooks:
                        try:
                            await self._run_hook(hook, request)
                        except SafetyBlocked:
                            raise
                        except Exception as e:  # pragma: no cover
                            logger.warning(f"Pre-action hook error: {e}")  # pragma: no cover

                    if self.config.safety.enabled:
                        for hook in self._safety_hooks:
                            try:
                                await self._run_hook(hook, request)
                            except SafetyBlocked:
                                raise
                            except Exception as e:  # pragma: no cover
                                logger.warning(f"Safety hook error: {e}")  # pragma: no cover

                    result = await self._execute_with_recovery(request)
                    duration_ms = (time.time() - start_time) * 1000
                    result.duration_ms = duration_ms

                    self._metrics.record_action(
                        duration_ms, result.success, self._metrics.retried_actions > 0
                    )
                    self._total_actions_executed += 1
                    assert self._session is not None
                    self._session.increment_actions()

                    for hook in self._post_action_hooks:
                        try:
                            await self._run_hook(hook, request, result)
                        except Exception as e:  # pragma: no cover
                            logger.warning(f"Post-action hook error: {e}")  # pragma: no cover

                    for hook in self._observability_hooks:
                        try:
                            await self._run_hook(hook, request, result)
                        except Exception as e:  # pragma: no cover
                            logger.warning(f"Observability hook error: {e}")  # pragma: no cover

                    return result

                except SafetyBlocked:
                    raise
                except ElementNotFound as e:
                    await self._handle_error(
                        e, {"action_type": action_type.value, "params": params}
                    )
                    raise
                except ActionFailed:
                    raise
                except Exception as e:
                    await self._handle_error(
                        e, {"action_type": action_type.value, "params": params}
                    )
                    raise ActionFailed(action_type.value, str(e), e) from e
        finally:
            if self._action_semaphore:
                self._action_semaphore.release()

    async def execute_action_request(self, request: ActionRequest) -> ActionResult:
        return await self.execute(request.type, **request.params)

    async def execute_batch(self, actions: list[dict[str, Any]]) -> list[ActionResult]:
        """Execute multiple actions sequentially with early stop on failure."""
        results = []
        for i, action in enumerate(actions):
            try:
                atype = ActionType(action["type"])
                params = action.get("params", {})
                result = await self.execute(atype, **params)
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
        return results

    # ─── Convenience Methods ────────────────────────────────────────────

    async def navigate(self, url: str, **kwargs) -> ActionResult:
        return await self.execute(ActionType.NAVIGATE, url=url, **kwargs)

    async def click(self, selector: str, **kwargs) -> ActionResult:
        return await self.execute(ActionType.CLICK, selector=selector, **kwargs)

    async def type_text(self, text: str, selector: str | None = None, **kwargs) -> ActionResult:
        return await self.execute(ActionType.TYPE, text=text, selector=selector, **kwargs)

    async def scroll(self, delta_y: int = 300, **kwargs) -> ActionResult:
        return await self.execute(ActionType.SCROLL, delta_y=delta_y, **kwargs)

    async def screenshot(self, **kwargs) -> ActionResult:
        return await self.execute(ActionType.SCREENSHOT, **kwargs)

    async def extract_text(self, selector: str | None = None, **kwargs) -> ActionResult:
        return await self.execute(ActionType.EXTRACT_TEXT, selector=selector, **kwargs)

    async def get_page_info(self) -> dict[str, Any]:
        url_result = await self.execute(ActionType.GET_URL)
        title_result = await self.execute(ActionType.GET_TITLE)
        return {
            "url": url_result.data.get("url") if url_result.data else None,
            "title": title_result.data.get("title") if title_result.data else None,
        }

    # ─── Internal ────────────────────────────────────────────────────────

    async def _execute_with_recovery(self, request: ActionRequest) -> ActionResult:
        strategy = self._recovery_manager.get_strategy(request.type)
        max_retries = strategy.max_retries if strategy else 2

        for attempt in range(max_retries + 1):
            try:
                assert self._browser is not None
                return await self._browser.execute_action(request)
            except (ElementNotFound, ActionFailed) as e:
                if attempt < max_retries:
                    delay = strategy.get_delay(attempt) if strategy else (2**attempt)
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {request.type} after {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
            except Exception as e:
                if attempt < max_retries:
                    delay = 2**attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {request.type} after {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise ActionFailed(request.type.value, str(e), e) from e
        raise RuntimeError("Unreachable")

    async def _run_hook(self, hook: Callable, *args, **kwargs) -> None:
        try:
            if asyncio.iscoroutinefunction(hook):
                await hook(*args, **kwargs)
            else:
                hook(*args, **kwargs)
        except SafetyBlocked:
            raise
        except Exception as e:
            logger.debug(f"Hook execution error (non-fatal): {e}")

    async def _handle_error(self, error: Exception, context: dict[str, Any]) -> None:
        for hook in self._on_error_hooks:
            with contextlib.suppress(Exception):
                await self._run_hook(hook, error, context)

    async def _dispatch_state_change(self, new_state: EngineState) -> None:
        for hook in self._on_state_change_hooks:
            with contextlib.suppress(Exception):
                await self._run_hook(hook, new_state)

    # ─── Async Context Manager ───────────────────────────────────────────

    async def __aenter__(self) -> ComputeEngine:
        await self.start_session()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop_session()
