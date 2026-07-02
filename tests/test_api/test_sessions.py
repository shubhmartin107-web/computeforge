from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from computeforge.api.server import create_app
from computeforge.models.session import SessionStatus
from tests.factories import make_session


@pytest.fixture(autouse=True)
def _clean_engines():
    from computeforge.api.routes_sessions import _engines
    _engines.clear()
    yield
    _engines.clear()


@pytest.mark.asyncio
async def test_create_session():
    app = create_app()
    session = make_session()
    mock_engine = MagicMock()
    mock_engine.create_session = AsyncMock(return_value=session)
    mock_engine.state = MagicMock()
    mock_engine.state.value = "stopped"

    with patch("computeforge.api.routes_sessions.ComputeEngine", return_value=mock_engine):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/sessions", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session.id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_session_with_config():
    app = create_app()
    session = make_session()
    mock_engine = MagicMock()
    mock_engine.create_session = AsyncMock(return_value=session)
    mock_engine.state = MagicMock()
    mock_engine.state.value = "running"

    with patch("computeforge.api.routes_sessions.ComputeEngine", return_value=mock_engine):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/sessions",
                json={"headless": True, "max_actions": 50},
            )

    assert resp.status_code == 200
    assert resp.json()["id"] == session.id


@pytest.mark.asyncio
async def test_list_sessions_empty():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["sessions"] == []


@pytest.mark.asyncio
async def test_list_sessions():
    app = create_app()
    session = make_session(status=SessionStatus.RUNNING)
    mock_engine = MagicMock()
    mock_engine.session = session
    mock_engine.state = MagicMock()
    mock_engine.state.value = "running"

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["sessions"][0]["id"] == session.id
    assert data["sessions"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_get_session():
    app = create_app()
    session = make_session(status=SessionStatus.RUNNING)
    mock_engine = MagicMock()
    mock_engine.session = session

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/sessions/{session.id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == session.id


@pytest.mark.asyncio
async def test_get_session_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/sessions/nonexistent")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_session():
    app = create_app()
    session = make_session(status=SessionStatus.RUNNING)
    mock_engine = MagicMock()
    mock_engine.start_session = AsyncMock(return_value=session)

    from computeforge.api.routes_sessions import _engines
    _engines[session.id] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/sessions/{session.id}/start")

    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert resp.json()["session_id"] == session.id


@pytest.mark.asyncio
async def test_start_session_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/sessions/nonexistent/start")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_session():
    app = create_app()
    sid = str(uuid.uuid4())
    mock_engine = MagicMock()
    mock_engine.stop_session = AsyncMock()

    from computeforge.api.routes_sessions import _engines
    _engines[sid] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/sessions/{sid}/stop")

    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert resp.json()["session_id"] == sid
    assert sid not in _engines


@pytest.mark.asyncio
async def test_pause_session():
    app = create_app()
    sid = str(uuid.uuid4())
    mock_engine = MagicMock()
    mock_engine.pause_session = AsyncMock()

    from computeforge.api.routes_sessions import _engines
    _engines[sid] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/sessions/{sid}/pause")

    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_resume_session():
    app = create_app()
    sid = str(uuid.uuid4())
    mock_engine = MagicMock()
    mock_engine.resume_session = AsyncMock()

    from computeforge.api.routes_sessions import _engines
    _engines[sid] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/sessions/{sid}/resume")

    assert resp.status_code == 200
    assert resp.json()["status"] == "resumed"


@pytest.mark.asyncio
async def test_start_session_error():
    app = create_app()
    sid = str(uuid.uuid4())
    mock_engine = MagicMock()
    mock_engine.start_session = AsyncMock(side_effect=ValueError("start failed"))

    from computeforge.api.routes_sessions import _engines
    _engines[sid] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/sessions/{sid}/start")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_session_state():
    app = create_app()
    sid = str(uuid.uuid4())
    mock_engine = MagicMock()
    mock_engine.get_state = AsyncMock(return_value={"state": "running", "session_id": sid})

    from computeforge.api.routes_sessions import _engines
    _engines[sid] = mock_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/sessions/{sid}/state")

    assert resp.status_code == 200
    assert resp.json()["state"] == "running"


@pytest.mark.asyncio
async def test_get_session_actions():
    app = create_app()
    from computeforge.api.routes_sessions import _engines
    from tests.factories import make_action_record
    sid = str(uuid.uuid4())

    action = make_action_record(session_id=sid)
    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(return_value=[action])
    mock_storage.get_action_count = AsyncMock(return_value=1)

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/sessions/{sid}/actions?limit=10&offset=0")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["actions"]) == 1
    assert data["actions"][0]["id"] == action.id


@pytest.mark.asyncio
async def test_get_session_actions_error():
    app = create_app()
    sid = str(uuid.uuid4())

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(side_effect=RuntimeError("storage error"))

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/sessions/{sid}/actions")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_annotate_session():
    app = create_app()
    sid = str(uuid.uuid4())

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.add_annotation = AsyncMock(return_value="annotation-1")

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/sessions/{sid}/annotate",
                params={"content": "test note"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["annotation_id"] == "annotation-1"


@pytest.mark.asyncio
async def test_annotate_session_error():
    app = create_app()
    sid = str(uuid.uuid4())

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.add_annotation = AsyncMock(side_effect=RuntimeError("annotate error"))

    with patch("computeforge.observability.storage.StorageBackend", return_value=mock_storage):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/sessions/{sid}/annotate",
                params={"content": "test note"},
            )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_create_session_with_many_engines():
    from datetime import datetime
    app = create_app()
    session = make_session()
    mock_engine = MagicMock()
    mock_engine.create_session = AsyncMock(return_value=session)
    mock_engine.state = MagicMock()
    mock_engine.state.value = "stopped"

    from computeforge.api.routes_sessions import _engines, _MAX_ENGINES
    for i in range(_MAX_ENGINES):
        eid = str(uuid.uuid4())
        e = MagicMock()
        e.state = MagicMock()
        e.state.value = "running"
        e.session = make_session(created_at=datetime.utcnow())
        _engines[eid] = e

    mock_engine.state.value = "running"
    mock_engine.session = make_session(created_at=datetime.utcnow())

    with patch("computeforge.api.routes_sessions.ComputeEngine", return_value=mock_engine):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/sessions", json={})

    assert resp.status_code == 200
    assert len(_engines) <= _MAX_ENGINES
