from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from computeforge.core.actions import ActionRequest, ActionResult, ActionType
from computeforge.models.action import ActionRecord, ActionStatus
from computeforge.models.capability import Capability, ParameterDef, RiskLevel
from computeforge.models.config import EngineConfig
from computeforge.models.session import Session, SessionConfig, SessionStatus


def make_session(**overrides: Any) -> Session:
    data = dict(
        id=str(uuid.uuid4()),
        status=SessionStatus.PENDING,
        config=SessionConfig(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    data.update(overrides)
    return Session(**data)


def make_session_config(**overrides: Any) -> SessionConfig:
    data = dict(headless=True, max_actions=100, timeout_seconds=60)
    data.update(overrides)
    return SessionConfig(**data)


def make_engine_config(**overrides: Any) -> EngineConfig:
    return EngineConfig(**overrides)


def make_action_record(**overrides: Any) -> ActionRecord:
    data = dict(
        id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        type="navigate",
        params={"url": "https://example.com"},
        status=ActionStatus.SUCCEEDED,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        duration_ms=100.0,
    )
    data.update(overrides)
    return ActionRecord(**data)


def make_action_request(**overrides: Any) -> ActionRequest:
    data = dict(
        type=ActionType.NAVIGATE,
        params={"url": "https://example.com"},
    )
    data.update(overrides)
    return ActionRequest(**data)


def make_action_result(**overrides: Any) -> ActionResult:
    data = dict(
        success=True,
        action_id=str(uuid.uuid4()),
        action_type=ActionType.NAVIGATE,
        data={"url": "https://example.com"},
        duration_ms=50.0,
    )
    data.update(overrides)
    return ActionResult(**data)


def make_capability(**overrides: Any) -> Capability:
    data = dict(
        name="test.capability",
        description="A test capability",
        action_type="navigate",
        risk_level=RiskLevel.LOW,
        required_permissions=["test.permission"],
        category="test",
    )
    data.update(overrides)
    return Capability(**data)


def make_parameter_def(**overrides: Any) -> ParameterDef:
    data = dict(name="param1", type="string", description="A test parameter", required=False)
    data.update(overrides)
    return ParameterDef(**data)
