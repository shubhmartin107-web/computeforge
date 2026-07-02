from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from computeforge.observability.replay import ReplayEngine
from computeforge.observability.storage import StorageBackend

logger = logging.getLogger("computeforge.api.websocket")
router = APIRouter()


@router.websocket("/sessions/{session_id}")
async def websocket_session_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session streaming.

    Streams actions as they are recorded, including screenshots.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id[:8]}...")

    storage = StorageBackend()
    await storage.connect()
    replay = ReplayEngine(storage)

    # Send initial session state
    try:
        session = await replay.get_session(session_id)
        summary = await replay.get_session_summary(session_id)
        await websocket.send_json({
            "type": "session_state",
            "data": {
                "session_id": session.id,
                "status": session.status.value,
                "action_count": session.action_count,
                **summary,
            },
        })
    except Exception as e:
        await websocket.send_json({"type": "error", "data": {"message": str(e)}})
        await websocket.close()
        return

    # Stream actions
    try:
        offset = 0
        while True:
            actions = await storage.load_actions(session_id, limit=10, offset=offset)
            for action in actions:
                action_data = {
                    "id": action.id,
                    "type": action.type,
                    "status": action.status.value,
                    "params": action.params,
                    "error": action.error,
                    "duration_ms": action.duration_ms,
                    "risk_score": action.risk_score,
                    "safety_decision": action.safety_decision,
                    "created_at": action.created_at.isoformat() if action.created_at else None,
                }
                await websocket.send_json({"type": "action", "data": action_data})

                # Send screenshot if available
                if action.screenshot_after:
                    img = storage.load_screenshot(action.screenshot_after)
                    if img:
                        import base64
                        await websocket.send_json({
                            "type": "screenshot",
                            "data": {
                                "action_id": action.id,
                                "image": base64.b64encode(img).decode("utf-8"),
                                "format": "png",
                            },
                        })

            offset += len(actions)

            # Wait for new data or client message
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(), timeout=1.0
                )
                msg_data = json.loads(message)
                if msg_data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_data.get("type") == "seek":
                    offset = msg_data.get("offset", 0)
            except TimeoutError:
                continue
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id[:8]}...")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "data": {"message": str(e)}})
        except Exception:
            pass
    finally:
        await storage.close()
