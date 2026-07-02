from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from computeforge.api.server import create_app
from tests.factories import make_action_record, make_session


def test_websocket_connect():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(return_value=[])

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            data = ws.receive_json()
            assert data["type"] == "session_state"
            assert data["data"]["session_id"] == session.id


def test_websocket_session_stream():
    app = create_app()
    session = make_session()
    action1 = make_action_record(session_id=session.id)
    action2 = make_action_record(session_id=session.id)

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock()
    mock_storage.load_actions.side_effect = [
        [action1, action2],
        [],
    ]
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 2})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"
            assert state["data"]["session_id"] == session.id

            msg1 = ws.receive_json()
            assert msg1["type"] == "action"
            assert msg1["data"]["id"] == action1.id

            msg2 = ws.receive_json()
            assert msg2["type"] == "action"
            assert msg2["data"]["id"] == action2.id


def test_websocket_session_error():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(side_effect=ValueError("session error"))
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "session error" in data["data"]["message"]


def test_websocket_with_screenshot():
    app = create_app()
    session = make_session()
    action = make_action_record(session_id=session.id, screenshot_after="screenshot_001.png")

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock()
    mock_storage.load_actions.side_effect = [
        [action],
        [],
    ]
    mock_storage.load_screenshot = MagicMock(return_value=b"fake_image_data")

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 1})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"

            action_msg = ws.receive_json()
            assert action_msg["type"] == "action"
            assert action_msg["data"]["id"] == action.id

            screenshot_msg = ws.receive_json()
            assert screenshot_msg["type"] == "screenshot"
            assert screenshot_msg["data"]["action_id"] == action.id
            assert screenshot_msg["data"]["format"] == "png"
            assert screenshot_msg["data"]["image"] == "ZmFrZV9pbWFnZV9kYXRh"


def test_websocket_ping_pong():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(return_value=[])
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"

            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


def test_websocket_seek():
    app = create_app()
    session = make_session()
    action = make_action_record(session_id=session.id)

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock()
    mock_storage.load_actions.side_effect = [
        [action],
        [],
        [],
        [],
    ]
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 1})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"

            action_msg = ws.receive_json()
            assert action_msg["type"] == "action"

            ws.send_json({"type": "seek", "offset": 0})


def test_websocket_timeout_continue():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(return_value=[])
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"

            import time
            time.sleep(1.1)


def test_websocket_outer_disconnect():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(side_effect=WebSocketDisconnect())
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"


def test_websocket_stream_error():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(side_effect=RuntimeError("stream error"))
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"

            error = ws.receive_json()
            assert error["type"] == "error"
            assert "stream error" in error["data"]["message"]


def test_websocket_error_handler_send_fails():
    app = create_app()
    session = make_session()

    mock_storage = MagicMock()
    mock_storage.connect = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.load_actions = AsyncMock(side_effect=RuntimeError("stream error"))
    mock_storage.load_screenshot = MagicMock(return_value=None)

    mock_replay = MagicMock()
    mock_replay.get_session = AsyncMock(return_value=session)
    mock_replay.get_session_summary = AsyncMock(return_value={"total_actions": 0})
    mock_replay._storage = mock_storage

    from starlette.websockets import WebSocket

    original_send_json = WebSocket.send_json
    send_call_count = [0]

    async def mock_send_json(self, *args, **kwargs):
        send_call_count[0] += 1
        if send_call_count[0] == 2:
            raise RuntimeError("mock send failure")
        return await original_send_json(self, *args, **kwargs)

    with (
        patch("computeforge.api.routes_websocket.StorageBackend", return_value=mock_storage),
        patch("computeforge.api.routes_websocket.ReplayEngine", return_value=mock_replay),
        patch.object(WebSocket, "send_json", mock_send_json),
    ):
        client = TestClient(app)
        with client.websocket_connect(f"/api/v1/ws/sessions/{session.id}") as ws:
            state = ws.receive_json()
            assert state["type"] == "session_state"
