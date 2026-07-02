from __future__ import annotations

import sys
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Mock pyautogui before any tests to avoid X11 display connection in headless CI
if "pyautogui" not in sys.modules:
    sys.modules["pyautogui"] = MagicMock()

# Mock mss for the same reason (headless env)
if "mss" not in sys.modules:
    sys.modules["mss"] = MagicMock()

from computeforge.core.actions import ActionResult, ActionType
from computeforge.core.engine import ComputeEngine
from computeforge.models.config import EngineConfig
from computeforge.models.session import SessionConfig
from tests.mocks.playwright_mock import (
    MockElementHandle,
    MockPage,
    MockPlaywright,
)


@pytest.fixture
def engine_config() -> EngineConfig:
    config = EngineConfig()
    config.browser.headless = True
    return config


@pytest_asyncio.fixture
async def engine(engine_config: EngineConfig) -> AsyncGenerator[ComputeEngine, None]:
    eng = ComputeEngine(config=engine_config)
    await eng.create_session(SessionConfig(headless=True))
    with patch("computeforge.core.browser.async_playwright") as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=MockPlaywright())
        await eng.start_session()
        yield eng
        await eng.stop_session()


@pytest.fixture
def sample_url() -> str:
    return "https://example.com"


@pytest.fixture
def mock_storage():
    with patch("computeforge.observability.storage.StorageBackend") as mock:
        instance = mock.return_value
        instance.connect = AsyncMock()
        instance.close = AsyncMock()
        instance.save_session = AsyncMock(return_value=None)
        instance.save_action = AsyncMock(return_value=None)
        instance.list_sessions = AsyncMock(return_value=[])
        instance.load_actions = AsyncMock(return_value=[])
        instance.get_action_count = AsyncMock(return_value=0)
        instance.export_session_json = AsyncMock(return_value="{}")
        instance.import_session_json = AsyncMock(return_value="session-id")
        instance.delete_session = AsyncMock(return_value=None)
        instance.get_session_stats = AsyncMock(return_value={
            "total_sessions": 0, "by_status": {}, "top_action_types": [],
            "total_actions": 0, "avg_duration_ms": 0.0,
        })
        instance.db_path = ":memory:"
        instance.connected = True
        yield instance


@pytest.fixture
def mock_page():
    return MockPage()


@pytest.fixture
def mock_element():
    return MockElementHandle()


@pytest.fixture
def action_result_success() -> ActionResult:
    return ActionResult(
        success=True,
        action_id=str(uuid.uuid4()),
        action_type=ActionType.NAVIGATE,
        data={"url": "https://example.com"},
        duration_ms=50.0,
    )


@pytest.fixture
def action_result_failure() -> ActionResult:
    return ActionResult(
        success=False,
        action_id=str(uuid.uuid4()),
        action_type=ActionType.NAVIGATE,
        error="Test error",
        duration_ms=10.0,
    )


@pytest.fixture
def mock_browser_manager():
    with patch("computeforge.core.engine.BrowserManager") as mock:
        instance = mock.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        instance.is_running = True
        instance.execute_action = AsyncMock(return_value=ActionResult(
            success=True, action_type=ActionType.SCREENSHOT, data={}
        ))
        instance.browser_type_name = "chromium"
        instance.metrics = {"pages_loaded": 0, "actions_executed": 0, "errors": 0, "total_navigation_ms": 0}
        yield instance


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        instance = mock.return_value
        instance.post = AsyncMock()
        instance.get = AsyncMock()
        instance.aclose = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock()
        yield instance
