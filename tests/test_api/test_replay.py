from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from computeforge.api.server import create_app
from tests.factories import make_action_record


@pytest.mark.asyncio
async def test_get_replay_data():
    app = create_app()
    session_id = "test-session-id"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(return_value=True)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay.get_actions = AsyncMock(return_value=[])
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["total_actions"] == 0


@pytest.mark.asyncio
async def test_get_replay_data_not_found():
    app = create_app()
    session_id = "nonexistent-session"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(return_value=False)
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_replay_data_error():
    app = create_app()
    session_id = "error-session"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(side_effect=RuntimeError("db crash"))
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_replay_step():
    app = create_app()
    session_id = "test-session-id"
    action = make_action_record(session_id=session_id)

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(return_value=True)
    mock_replay.get_action_at_index = AsyncMock(return_value=action)
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}/step/0")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["step_index"] == 0
    assert data["action"]["id"] == action.id


@pytest.mark.asyncio
async def test_get_replay_step_session_not_found():
    app = create_app()
    session_id = "nonexistent"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(return_value=False)
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}/step/0")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_replay_step_not_found():
    app = create_app()
    session_id = "test-session-id"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(return_value=True)
    mock_replay.get_action_at_index = AsyncMock(return_value=None)
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}/step/999")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_replay_step_error():
    app = create_app()
    session_id = "test-session-id"

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.session_exists = AsyncMock(side_effect=RuntimeError("db error"))
    mock_replay._storage = mock_storage

    with patch("computeforge.api.routes_replay.ReplayEngine", return_value=mock_replay):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/replay/{session_id}/step/0")

    assert resp.status_code == 500
