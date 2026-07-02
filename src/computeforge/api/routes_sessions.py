from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from computeforge.core.engine import ComputeEngine
from computeforge.models.session import Session, SessionConfig

router = APIRouter()

_engines: dict[str, ComputeEngine] = {}
_MAX_ENGINES = 100


def _get_engine(session_id: str) -> ComputeEngine:
    engine = _engines.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return engine


def _cleanup_stale_engines() -> None:
    stale = [sid for sid, eng in list(_engines.items()) if eng.state.value in ("stopped", "error")]
    for sid in stale:
        _engines.pop(sid, None)
    if len(_engines) > _MAX_ENGINES:
        sorted_engines = sorted(_engines.items(), key=lambda x: x[1].session.created_at or "")
        for sid, _ in sorted_engines[:len(_engines) - _MAX_ENGINES]:
            _engines.pop(sid, None)


@router.post("", response_model=Session, summary="Create a new session")
async def create_session(config: SessionConfig | None = None):
    """Create a new computer-use session."""
    engine = ComputeEngine()
    session = await engine.create_session(config or SessionConfig())
    _engines[session.id] = engine
    _cleanup_stale_engines()
    return session


@router.get("", summary="List all active sessions")
async def list_sessions():
    """List all active sessions in memory."""
    return {
        "sessions": [
            {
                "id": e.session.id,
                "status": e.session.status.value if e.session else "unknown",
                "action_count": e.session.action_count if e.session else 0,
                "created_at": e.session.created_at.isoformat() if e.session and e.session.created_at else None,
                "state": e.state.value if hasattr(e, "state") else "unknown",
            }
            for e in _engines.values()
        ],
        "count": len(_engines),
    }


@router.get("/{session_id}", response_model=Session, summary="Get session details")
async def get_session(session_id: str):
    """Get session details."""
    engine = _get_engine(session_id)
    return engine.session


@router.post("/{session_id}/start", summary="Start a session")
async def start_session(session_id: str):
    """Start a session (launch browser)."""
    engine = _get_engine(session_id)
    try:
        session = await engine.start_session()
        return {"status": "started", "session_id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/stop", summary="Stop a session")
async def stop_session(session_id: str):
    """Stop a session."""
    engine = _get_engine(session_id)
    await engine.stop_session()
    _engines.pop(session_id, None)
    return {"status": "stopped", "session_id": session_id}


@router.post("/{session_id}/pause", summary="Pause a session")
async def pause_session(session_id: str):
    """Pause a session."""
    engine = _get_engine(session_id)
    await engine.pause_session()
    return {"status": "paused", "session_id": session_id}


@router.post("/{session_id}/resume", summary="Resume a session")
async def resume_session(session_id: str):
    """Resume a paused session."""
    engine = _get_engine(session_id)
    await engine.resume_session()
    return {"status": "resumed", "session_id": session_id}


@router.get("/{session_id}/state", summary="Get engine state")
async def get_session_state(session_id: str):
    """Get detailed engine state including metrics."""
    engine = _get_engine(session_id)
    return await engine.get_state()


@router.get("/{session_id}/actions", summary="Get session actions from storage")
async def get_session_actions(
    session_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get actions for a session from persistent storage."""
    from computeforge.observability.storage import StorageBackend
    storage = StorageBackend()
    try:
        await storage.connect()
        actions = await storage.load_actions(session_id, limit=limit, offset=offset)
        total = await storage.get_action_count(session_id)
        return {
            "actions": [a.model_dump() for a in actions],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await storage.close()


@router.post("/{session_id}/annotate", summary="Add annotation to session")
async def annotate_session(session_id: str, content: str, action_id: str | None = None):
    """Add an annotation to a session."""
    from computeforge.observability.storage import StorageBackend
    storage = StorageBackend()
    try:
        await storage.connect()
        aid = await storage.add_annotation(session_id, content, action_id)
        return {"status": "ok", "annotation_id": aid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await storage.close()
