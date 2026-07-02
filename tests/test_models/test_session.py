from datetime import datetime

from computeforge.models.session import Session, SessionConfig, SessionStatus


def test_session_status_values():
    assert SessionStatus.PENDING.value == "pending"
    assert SessionStatus.RUNNING.value == "running"
    assert SessionStatus.PAUSED.value == "paused"
    assert SessionStatus.COMPLETED.value == "completed"
    assert SessionStatus.FAILED.value == "failed"
    assert SessionStatus.CANCELLED.value == "cancelled"


def test_session_defaults():
    session = Session()
    assert session.status == SessionStatus.PENDING
    assert session.action_count == 0
    assert session.error is None
    assert session.started_at is None
    assert session.ended_at is None
    assert session.metadata == {}
    assert session.tags == []
    assert isinstance(session.config, SessionConfig)


def test_session_creation():
    config = SessionConfig(headless=False, base_url="https://example.com")
    now = datetime.utcnow()
    session = Session(
        id="session-1",
        status=SessionStatus.RUNNING,
        config=config,
        created_at=now,
        updated_at=now,
        started_at=now,
        action_count=5,
        metadata={"env": "test"},
        tags=["integration"],
    )
    assert session.id == "session-1"
    assert session.status == SessionStatus.RUNNING
    assert session.config.base_url == "https://example.com"
    assert session.config.headless is False
    assert session.action_count == 5
    assert session.metadata == {"env": "test"}
    assert session.tags == ["integration"]


def test_session_config_defaults():
    config = SessionConfig()
    assert config.headless is True
    assert config.viewport_width == 1280
    assert config.viewport_height == 720
    assert config.base_url is None
    assert config.max_actions == 0
    assert config.timeout_seconds == 300
    assert config.record_screenshots is True
    assert config.safety_enabled is True
    assert config.metadata == {}


def test_session_config_creation():
    config = SessionConfig(
        headless=False,
        viewport_width=1920,
        viewport_height=1080,
        base_url="https://example.com",
        max_actions=50,
        timeout_seconds=600,
        record_screenshots=False,
        safety_enabled=False,
        metadata={"custom": "value"},
    )
    assert config.headless is False
    assert config.viewport_width == 1920
    assert config.viewport_height == 1080
    assert config.base_url == "https://example.com"
    assert config.max_actions == 50
    assert config.timeout_seconds == 600
    assert config.record_screenshots is False
    assert config.safety_enabled is False
    assert config.metadata == {"custom": "value"}


def test_session_status_lifecycle():
    session = Session()
    assert session.status == SessionStatus.PENDING
    assert session.started_at is None

    session.start()
    assert session.status == SessionStatus.RUNNING
    assert session.started_at is not None

    session.complete()
    assert session.status == SessionStatus.COMPLETED
    assert session.ended_at is not None

    session2 = Session()
    session2.start()
    session2.fail("unexpected error")
    assert session2.status == SessionStatus.FAILED
    assert session2.error == "unexpected error"
    assert session2.ended_at is not None


def test_session_pause_resume():
    session = Session()
    session.start()
    assert session.status == SessionStatus.RUNNING

    session.pause()
    assert session.status == SessionStatus.PAUSED

    session.resume()
    assert session.status == SessionStatus.RUNNING


def test_session_action_count_tracking():
    session = Session()
    assert session.action_count == 0

    session.increment_actions()
    assert session.action_count == 1

    session.increment_actions()
    session.increment_actions()
    assert session.action_count == 3


def test_session_serialization():
    session = Session(id="ser-session", tags=["a", "b"])
    dumped = session.model_dump()
    assert dumped["id"] == "ser-session"
    assert dumped["status"] == "pending"
    assert dumped["tags"] == ["a", "b"]
    assert "config" in dumped

    restored = Session.model_validate(dumped)
    assert restored.id == "ser-session"
    assert restored.status == SessionStatus.PENDING
    assert restored.tags == ["a", "b"]
