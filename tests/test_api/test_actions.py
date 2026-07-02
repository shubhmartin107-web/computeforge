from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from computeforge.api.server import create_app
from computeforge.core.actions import ActionType
from computeforge.core.exceptions import ActionFailed, ElementNotFound, SafetyBlocked
from tests.factories import make_action_result, make_session


@pytest.fixture(autouse=True)
def _clean_engines():
    from computeforge.api.routes_sessions import _engines
    _engines.clear()
    yield
    _engines.clear()


@pytest.mark.asyncio
async def test_execute_action():
    app = create_app()
    session = make_session()
    result = make_action_result(success=True, action_type=ActionType.NAVIGATE)

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(return_value=result)

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": session.id,
                "action_type": "navigate",
                "params": {"url": "https://example.com"},
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["duration_ms"] == result.duration_ms


@pytest.mark.asyncio
async def test_execute_action_invalid_type():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": session.id,
                "action_type": "invalid_action_type_xyz",
                "params": {},
            },
        )

    assert resp.status_code == 400
    assert "invalid_action_type_xyz" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_execute_action_session_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": "nonexistent",
                "action_type": "navigate",
                "params": {},
            },
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_execute_batch():
    app = create_app()
    session = make_session()
    result = make_action_result(success=True, action_type=ActionType.NAVIGATE, duration_ms=50.0)

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(return_value=result)

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/batch",
            json={
                "session_id": session.id,
                "actions": [
                    {"type": "navigate", "params": {"url": "https://example.com"}},
                    {"type": "screenshot", "params": {}},
                ],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["success"] is True
    assert data["results"][1]["success"] is True
    assert mock_engine.execute.call_count == 2


@pytest.mark.asyncio
async def test_execute_batch_error():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(side_effect=Exception("Execution failed"))

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/batch",
            json={
                "session_id": session.id,
                "actions": [
                    {"type": "navigate", "params": {"url": "https://example.com"}},
                    {"type": "screenshot", "params": {}},
                ],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["success"] is False
    assert data["results"][0]["error"] is not None


@pytest.mark.asyncio
async def test_execute_batch_invalid_action_type():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/batch",
            json={
                "session_id": session.id,
                "actions": [
                    {"type": "not_valid_type", "params": {}},
                ],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["success"] is False
    assert "not_valid_type" in data["results"][0]["error"]


@pytest.mark.asyncio
async def test_execute_action_safety_blocked():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(side_effect=SafetyBlocked("navigate", "Blocked"))

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": session.id,
                "action_type": "navigate",
                "params": {"url": "https://example.com"},
            },
        )

    assert resp.status_code == 403
    assert "Blocked" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_execute_action_element_not_found():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(side_effect=ElementNotFound("click", "css", ".missing"))

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": session.id,
                "action_type": "click",
                "params": {"selector": ".missing"},
            },
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_execute_action_action_failed():
    app = create_app()
    session = make_session()

    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(side_effect=ActionFailed("navigate", "Navigation failed"))

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/actions/execute",
            json={
                "session_id": session.id,
                "action_type": "navigate",
                "params": {"url": "https://example.com"},
            },
        )

    assert resp.status_code == 500
    assert "Navigation failed" in resp.json()["detail"]
