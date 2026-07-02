from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from computeforge.models.action import ActionRecord

logger = logging.getLogger("computeforge.observability.flowlens")


class FlowLensAdapter:
    """Adapter to push observability events to FlowLens.

    FlowLens is an observability pipeline for AI agents. This adapter
    formats ComputeForge events into FlowLens-compatible spans/events
    and pushes them via HTTP if the FlowLens agent is available.
    """

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self._endpoint = endpoint
        self._api_key = api_key
        self._enabled = False
        self._httpx_client: Any | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def connect(self) -> None:
        if self._endpoint:
            try:
                import httpx
                self._httpx_client = httpx.AsyncClient(
                    base_url=self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
                    timeout=5.0,
                )
                self._enabled = True
                logger.info(f"Connected to FlowLens at {self._endpoint}")
            except Exception as e:
                logger.warning(f"Failed to connect to FlowLens: {e}")
        else:
            logger.info("FlowLens not configured (no endpoint). Use COMPUTEFORGE_FLOWLENS_ENDPOINT env var.")

    async def close(self) -> None:
        if self._httpx_client:
            await self._httpx_client.aclose()
            self._httpx_client = None
        self._enabled = False

    async def push_action(self, action: ActionRecord, session_id: str) -> None:
        if not self._enabled or not self._httpx_client:
            return
        try:
            event = self._build_event(action, session_id)
            await self._httpx_client.post("/api/v1/events", json=event)
        except Exception as e:
            logger.debug(f"FlowLens push failed: {e}")

    async def push_session_start(self, session_id: str, metadata: dict[str, Any] | None = None) -> None:
        if not self._enabled or not self._httpx_client:
            return
        try:
            await self._httpx_client.post("/api/v1/spans", json={
                "span_id": f"session_{session_id}",
                "name": "computeforge.session",
                "type": "session",
                "status": "started",
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.debug(f"FlowLens push_session_start failed: {e}")

    async def push_session_end(self, session_id: str, status: str, summary: dict[str, Any] | None = None) -> None:
        if not self._enabled or not self._httpx_client:
            return
        try:
            await self._httpx_client.post("/api/v1/spans", json={
                "span_id": f"session_{session_id}",
                "name": "computeforge.session",
                "type": "session",
                "status": status,
                "metadata": summary or {},
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.debug(f"FlowLens push_session_end failed: {e}")

    def _build_event(self, action: ActionRecord, session_id: str) -> dict[str, Any]:
        return {
            "event_id": action.id,
            "span_id": f"session_{session_id}",
            "name": f"action.{action.type}",
            "type": "action",
            "status": action.status.value,
            "action_type": action.type,
            "duration_ms": action.duration_ms,
            "error": action.error,
            "risk_score": action.risk_score,
            "safety_decision": action.safety_decision,
            "timestamp": action.created_at.isoformat() if action.created_at else datetime.utcnow().isoformat(),
            "metadata": action.metadata,
        }
