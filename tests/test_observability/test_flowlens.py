from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from computeforge.observability.flowlens import FlowLensAdapter
from tests.factories import make_action_record


@pytest.mark.asyncio
async def test_init_no_endpoint():
    adapter = FlowLensAdapter()
    assert adapter._endpoint is None
    assert adapter._api_key is None
    assert adapter._enabled is False
    assert adapter._httpx_client is None


@pytest.mark.asyncio
async def test_init_with_endpoint():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080", api_key="test-key")
    assert adapter._endpoint == "http://localhost:8080"
    assert adapter._api_key == "test-key"


@pytest.mark.asyncio
async def test_connect_no_endpoint():
    adapter = FlowLensAdapter()
    await adapter.connect()
    assert adapter._enabled is False
    assert adapter._httpx_client is None


@pytest.mark.asyncio
async def test_connect_with_endpoint():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
    assert adapter._enabled is True
    assert adapter._httpx_client is not None


@pytest.mark.asyncio
async def test_push_action_disabled():
    adapter = FlowLensAdapter()
    await adapter.connect()
    action = make_action_record()
    result = await adapter.push_action(action, "session-1")
    assert result is None


@pytest.mark.asyncio
async def test_push_action_enabled():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        action = make_action_record()
        await adapter.push_action(action, "session-1")
    mock_instance.post.assert_awaited_once_with("/api/v1/events", json=ANY)


@pytest.mark.asyncio
async def test_push_session_start():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        await adapter.push_session_start("session-1", {"key": "value"})
    mock_instance.post.assert_awaited_once_with("/api/v1/spans", json=ANY)


@pytest.mark.asyncio
async def test_push_session_end():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        await adapter.push_session_end("session-1", "completed", {"actions": 10})
    mock_instance.post.assert_awaited_once_with("/api/v1/spans", json=ANY)


@pytest.mark.asyncio
async def test_close():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock()
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        await adapter.close()
    mock_instance.aclose.assert_awaited_once()
    assert adapter._enabled is False
    assert adapter._httpx_client is None


def test_build_event():
    adapter = FlowLensAdapter()
    action = make_action_record()
    event = adapter._build_event(action, "session-1")
    assert event["event_id"] == action.id
    assert event["span_id"] == "session_session-1"
    assert event["name"] == f"action.{action.type}"
    assert event["type"] == "action"
    assert event["status"] == action.status.value
    assert event["duration_ms"] == action.duration_ms
    assert "timestamp" in event


@pytest.mark.asyncio
async def test_push_action_error_handling():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        action = make_action_record()
        await adapter.push_action(action, "session-1")
    mock_instance.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_push_session_start_disabled():
    adapter = FlowLensAdapter()
    await adapter.connect()
    result = await adapter.push_session_start("session-1")
    assert result is None


@pytest.mark.asyncio
async def test_push_session_end_disabled():
    adapter = FlowLensAdapter()
    await adapter.connect()
    result = await adapter.push_session_end("session-1", "completed")
    assert result is None


def test_enabled_property():
    adapter = FlowLensAdapter()
    assert adapter.enabled is False
    adapter._enabled = True
    assert adapter.enabled is True


@pytest.mark.asyncio
async def test_connect_failure():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient", side_effect=Exception("Connection refused")):
        await adapter.connect()
    assert adapter._enabled is False
    assert adapter._httpx_client is None


@pytest.mark.asyncio
async def test_push_session_start_error():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        await adapter.push_session_start("session-1")
    mock_instance.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_push_session_end_error():
    adapter = FlowLensAdapter(endpoint="http://localhost:8080")
    with patch("httpx.AsyncClient") as mock_async_client:
        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_instance.aclose = AsyncMock()
        mock_async_client.return_value = mock_instance
        await adapter.connect()
        await adapter.push_session_end("session-1", "completed")
    mock_instance.post.assert_awaited_once()
