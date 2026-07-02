from datetime import datetime

from computeforge.models.action import ActionRecord, ActionStatus


def test_action_status_values():
    assert ActionStatus.PENDING.value == "pending"
    assert ActionStatus.RUNNING.value == "running"
    assert ActionStatus.SUCCEEDED.value == "succeeded"
    assert ActionStatus.FAILED.value == "failed"
    assert ActionStatus.BLOCKED.value == "blocked"
    assert ActionStatus.CANCELLED.value == "cancelled"


def test_action_record_defaults():
    record = ActionRecord()
    assert record.status == ActionStatus.PENDING
    assert record.type == ""
    assert record.params == {}
    assert record.result is None
    assert record.error is None
    assert record.duration_ms == 0.0
    assert record.metadata == {}


def test_action_record_creation():
    now = datetime.utcnow()
    record = ActionRecord(
        id="test-id",
        session_id="session-1",
        type="navigate",
        params={"url": "https://example.com"},
        status=ActionStatus.RUNNING,
        result={"success": True},
        error=None,
        risk_score=0.5,
        safety_decision="approved",
        screenshot_before="base64...",
        screenshot_after="base64...",
        created_at=now,
        completed_at=now,
        duration_ms=150.0,
        metadata={"source": "test"},
    )
    assert record.id == "test-id"
    assert record.session_id == "session-1"
    assert record.type == "navigate"
    assert record.params == {"url": "https://example.com"}
    assert record.status == ActionStatus.RUNNING
    assert record.result == {"success": True}
    assert record.risk_score == 0.5
    assert record.safety_decision == "approved"
    assert record.duration_ms == 150.0
    assert record.metadata == {"source": "test"}


def test_action_record_mark_succeeded():
    record = ActionRecord()
    record.mark_succeeded(result="done", duration_ms=200.0)
    assert record.status == ActionStatus.SUCCEEDED
    assert record.result == "done"
    assert record.duration_ms == 200.0
    assert record.completed_at is not None


def test_action_record_mark_failed():
    record = ActionRecord()
    record.mark_failed(error="something went wrong", duration_ms=50.0)
    assert record.status == ActionStatus.FAILED
    assert record.error == "something went wrong"
    assert record.duration_ms == 50.0
    assert record.completed_at is not None


def test_action_record_mark_blocked():
    record = ActionRecord()
    record.mark_blocked(reason="permission denied")
    assert record.status == ActionStatus.BLOCKED
    assert record.error == "permission denied"
    assert record.completed_at is not None


def test_action_record_serialization():
    record = ActionRecord(
        id="ser-id",
        session_id="ser-session",
        type="click",
        status=ActionStatus.SUCCEEDED,
        duration_ms=100.0,
    )
    dumped = record.model_dump()
    assert dumped["id"] == "ser-id"
    assert dumped["session_id"] == "ser-session"
    assert dumped["type"] == "click"
    assert dumped["status"] == "succeeded"
    assert dumped["duration_ms"] == 100.0

    restored = ActionRecord.model_validate(dumped)
    assert restored.id == "ser-id"
    assert restored.status == ActionStatus.SUCCEEDED
    assert restored.type == "click"
