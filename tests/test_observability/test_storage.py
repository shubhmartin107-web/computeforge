"""Tests for the storage backend."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from computeforge.core.exceptions import SessionNotFound
from computeforge.models.action import ActionRecord, ActionStatus
from computeforge.models.session import Session, SessionStatus
from computeforge.observability.storage import StorageBackend


@pytest.fixture
async def storage():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    screenshot_dir = os.path.join(tmpdir, "screenshots")
    s = StorageBackend(db_path=db_path, screenshot_dir=screenshot_dir)
    await s.connect()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_save_and_load_session(storage):
    session = Session()
    await storage.save_session(session)
    loaded = await storage.load_session(session.id)
    assert loaded.id == session.id
    assert loaded.status.value == "pending"


@pytest.mark.asyncio
async def test_list_sessions(storage):
    s1 = Session()
    s2 = Session()
    await storage.save_session(s1)
    await storage.save_session(s2)
    sessions = await storage.list_sessions()
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_save_and_load_action(storage):
    session = Session()
    await storage.save_session(session)
    action = ActionRecord(session_id=session.id, type="navigate", params={"url": "https://example.com"}, status=ActionStatus.SUCCEEDED, duration_ms=100.0)
    await storage.save_action(action)
    loaded = await storage.load_action(action.id)
    assert loaded is not None
    assert loaded.type == "navigate"
    assert loaded.duration_ms == 100.0


@pytest.mark.asyncio
async def test_get_action_count(storage):
    session = Session()
    await storage.save_session(session)
    for _i in range(3):
        action = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
        await storage.save_action(action)
    count = await storage.get_action_count(session.id)
    assert count == 3


@pytest.mark.asyncio
async def test_get_session_stats(storage):
    s1 = Session()
    s2 = Session()
    await storage.save_session(s1)
    await storage.save_session(s2)
    stats = await storage.get_session_stats()
    assert stats["total_sessions"] >= 2


@pytest.mark.asyncio
async def test_delete_session(storage):
    session = Session()
    await storage.save_session(session)
    await storage.delete_session(session.id)
    with pytest.raises(SessionNotFound):
        await storage.load_session(session.id)


# ─── Properties ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_db_path_property(storage):
    assert isinstance(storage.db_path, Path)
    assert str(storage.db_path).endswith("test.db")


@pytest.mark.asyncio
async def test_connected_property(storage):
    assert storage.connected is True


# ─── Connection Management ───────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_already_connected(storage):
    await storage.connect()
    assert storage.connected is True


@pytest.mark.asyncio
async def test_connect_error():
    s = StorageBackend(db_path="/tmp/test_connect_err.db")
    s._connected = False
    with patch("aiosqlite.connect", side_effect=Exception("conn failed")):
        with pytest.raises(ConnectionError):
            await s.connect()
    await s.close()


@pytest.mark.asyncio
async def test_reconnect(storage):
    await storage.reconnect()
    assert storage.connected is True


# ─── Session Listing with Filters ────────────────────────────────

@pytest.mark.asyncio
async def test_list_sessions_status_filter(storage):
    s1 = Session(status=SessionStatus.COMPLETED)
    s2 = Session(status=SessionStatus.FAILED)
    await storage.save_session(s1)
    await storage.save_session(s2)
    sessions = await storage.list_sessions(status="completed")
    assert len(sessions) == 1
    assert sessions[0].id == s1.id


@pytest.mark.asyncio
async def test_list_sessions_search_filter(storage):
    session = Session()
    await storage.save_session(session)
    sessions = await storage.list_sessions(search=session.id[:8])
    assert len(sessions) >= 1


@pytest.mark.asyncio
async def test_list_sessions_date_filters(storage):
    s1 = Session()
    s2 = Session()
    await storage.save_session(s1)
    await storage.save_session(s2)
    sessions = await storage.list_sessions(date_from="2000-01-01")
    assert len(sessions) >= 2
    sessions = await storage.list_sessions(date_to="2100-01-01")
    assert len(sessions) >= 2
    sessions = await storage.list_sessions(date_from="2100-01-01", date_to="2100-01-02")
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_list_sessions_sorting(storage):
    s1 = Session()
    s2 = Session()
    await storage.save_session(s1)
    await storage.save_session(s2)
    sessions = await storage.list_sessions(sort_by="status", sort_desc=False)
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_list_sessions_pagination(storage):
    sessions_to_save = [Session() for _ in range(5)]
    for s in sessions_to_save:
        await storage.save_session(s)
    result = await storage.list_sessions(limit=2, offset=0)
    assert len(result) == 2


# ─── Count Sessions ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_count_sessions_no_filters(storage):
    s1 = Session()
    s2 = Session()
    await storage.save_session(s1)
    await storage.save_session(s2)
    count = await storage.count_sessions()
    assert count >= 2


@pytest.mark.asyncio
async def test_count_sessions_with_status(storage):
    s1 = Session(status=SessionStatus.COMPLETED)
    s2 = Session(status=SessionStatus.PENDING)
    await storage.save_session(s1)
    await storage.save_session(s2)
    count = await storage.count_sessions(status="completed")
    assert count == 1


@pytest.mark.asyncio
async def test_count_sessions_with_search(storage):
    session = Session()
    await storage.save_session(session)
    count = await storage.count_sessions(search=session.id[:8])
    assert count >= 1


@pytest.mark.asyncio
async def test_count_sessions_empty_db(storage):
    count = await storage.count_sessions()
    assert count == 0


# ─── Update Session Status ───────────────────────────────────────

@pytest.mark.asyncio
async def test_update_session_status_terminal(storage):
    session = Session()
    await storage.save_session(session)
    await storage.update_session_status(session.id, SessionStatus.COMPLETED)
    loaded = await storage.load_session(session.id)
    assert loaded.status == SessionStatus.COMPLETED
    assert loaded.ended_at is not None


@pytest.mark.asyncio
async def test_update_session_status_non_terminal(storage):
    session = Session()
    await storage.save_session(session)
    await storage.update_session_status(session.id, SessionStatus.RUNNING)
    loaded = await storage.load_session(session.id)
    assert loaded.status == SessionStatus.RUNNING


@pytest.mark.asyncio
async def test_update_session_status_with_error(storage):
    session = Session()
    await storage.save_session(session)
    await storage.update_session_status(session.id, SessionStatus.FAILED, error="oops")
    loaded = await storage.load_session(session.id)
    assert loaded.status == SessionStatus.FAILED
    assert loaded.error == "oops"


# ─── Delete Session with Screenshots ─────────────────────────────

@pytest.mark.asyncio
async def test_delete_session_with_screenshots(storage):
    session = Session()
    await storage.save_session(session)
    session_dir = storage._screenshot_dir / session.id
    session_dir.mkdir(parents=True)
    (session_dir / "test.png").write_text("fake")
    await storage.delete_session(session.id)
    with pytest.raises(SessionNotFound):
        await storage.load_session(session.id)
    assert not session_dir.exists()


# ─── Get Sessions by Tag ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_sessions_by_tag(storage):
    session = Session(tags=["important", "test"])
    await storage.save_session(session)
    results = await storage.get_sessions_by_tag("important")
    assert len(results) == 1
    assert results[0].id == session.id


@pytest.mark.asyncio
async def test_get_sessions_by_tag_no_match(storage):
    results = await storage.get_sessions_by_tag("nonexistent")
    assert len(results) == 0


# ─── Save Action (Full Coverage) ─────────────────────────────────

@pytest.mark.asyncio
async def test_save_action_all_fields(storage):
    session = Session()
    await storage.save_session(session)
    action = ActionRecord(
        session_id=session.id,
        type="file_operation",
        params={"path": "/tmp/test"},
        status=ActionStatus.FAILED,
        result={"error": "permission denied"},
        error="Permission denied",
        risk_score=0.8,
        safety_decision="blocked",
        screenshot_before="/tmp/before.png",
        screenshot_after="/tmp/after.png",
        duration_ms=1500.0,
        metadata={"source": "cli"},
    )
    await storage.save_action(action)
    loaded = await storage.load_action(action.id)
    assert loaded is not None
    assert loaded.type == "file_operation"
    assert loaded.error == "Permission denied"
    assert loaded.risk_score == 0.8
    assert loaded.safety_decision == "blocked"
    assert loaded.screenshot_before == "/tmp/before.png"
    assert loaded.screenshot_after == "/tmp/after.png"


# ─── Load Actions ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_actions_no_filters(storage):
    session = Session()
    await storage.save_session(session)
    a1 = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    a2 = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.FAILED, duration_ms=20.0)
    await storage.save_action(a1)
    await storage.save_action(a2)
    actions = await storage.load_actions(session.id)
    assert len(actions) == 2


@pytest.mark.asyncio
async def test_load_actions_with_status_filter(storage):
    session = Session()
    await storage.save_session(session)
    a1 = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    a2 = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.FAILED, duration_ms=20.0)
    await storage.save_action(a1)
    await storage.save_action(a2)
    actions = await storage.load_actions(session.id, status="failed")
    assert len(actions) == 1
    assert actions[0].id == a2.id


@pytest.mark.asyncio
async def test_load_actions_with_type_filter(storage):
    session = Session()
    await storage.save_session(session)
    a1 = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    a2 = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.FAILED, duration_ms=20.0)
    await storage.save_action(a1)
    await storage.save_action(a2)
    actions = await storage.load_actions(session.id, action_type="click")
    assert len(actions) == 1


@pytest.mark.asyncio
async def test_load_actions_pagination(storage):
    session = Session()
    await storage.save_session(session)
    for i in range(5):
        a = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=float(i))
        await storage.save_action(a)
    actions = await storage.load_actions(session.id, limit=2, offset=0)
    assert len(actions) == 2


# ─── Load Action ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_action_not_found(storage):
    result = await storage.load_action("nonexistent-id")
    assert result is None


# ─── Stream Actions ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_actions(storage):
    session = Session()
    await storage.save_session(session)
    for i in range(3):
        a = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=float(i))
        await storage.save_action(a)
    collected = [a async for a in storage.stream_actions(session.id)]
    assert len(collected) == 3


@pytest.mark.asyncio
async def test_stream_actions_empty(storage):
    session = Session()
    await storage.save_session(session)
    collected = [a async for a in storage.stream_actions(session.id)]
    assert len(collected) == 0


# ─── Search Actions ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_actions(storage):
    session = Session()
    await storage.save_session(session)
    a1 = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    a2 = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.FAILED, error="timeout", duration_ms=20.0)
    await storage.save_action(a1)
    await storage.save_action(a2)
    results = await storage.search_actions("click")
    assert len(results) == 1
    results = await storage.search_actions("timeout")
    assert len(results) == 1
    results = await storage.search_actions("nonexistent")
    assert len(results) == 0


# ─── Action Timeline ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_action_timeline(storage):
    session = Session()
    await storage.save_session(session)
    a1 = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    a2 = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.FAILED, duration_ms=20.0)
    await storage.save_action(a1)
    await storage.save_action(a2)
    timeline = await storage.get_action_timeline(session.id)
    assert len(timeline) == 2
    assert timeline[0]["type"] == "click"
    assert timeline[1]["type"] == "navigate"


# ─── Events ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_events(storage):
    session = Session()
    await storage.save_session(session)
    await storage.save_event(session.id, "test_event", {"key": "value"})
    events = await storage.get_events(session.id)
    assert len(events) == 1
    assert events[0]["type"] == "test_event"


# ─── Annotations ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_and_get_annotations(storage):
    session = Session()
    await storage.save_session(session)
    aid = await storage.add_annotation(session.id, "test annotation")
    annotations = await storage.get_annotations(session.id)
    assert len(annotations) == 1
    assert annotations[0]["content"] == "test annotation"
    assert annotations[0]["id"] == aid


# ─── Screenshot Operations ───────────────────────────────────────

@pytest.mark.asyncio
async def test_save_screenshot(storage):
    session = Session()
    await storage.save_session(session)
    path = storage.save_screenshot(session.id, "action-1", b"fake_image_data", label="before")
    expected = str(storage._screenshot_dir / session.id / "action-1_before.png")
    assert path == expected
    assert Path(expected).exists()


@pytest.mark.asyncio
async def test_save_screenshot_no_label(storage):
    session = Session()
    await storage.save_session(session)
    path = storage.save_screenshot(session.id, "action-1", b"fake_image_data")
    expected = str(storage._screenshot_dir / session.id / "action-1.png")
    assert path == expected


@pytest.mark.asyncio
async def test_load_screenshot(storage):
    session = Session()
    await storage.save_session(session)
    path = storage.save_screenshot(session.id, "action-1", b"image_data")
    loaded = storage.load_screenshot(path)
    assert loaded == b"image_data"


@pytest.mark.asyncio
async def test_load_screenshot_not_found(storage):
    result = storage.load_screenshot("/nonexistent/path.png")
    assert result is None


@pytest.mark.asyncio
async def test_list_screenshots(storage):
    session = Session()
    await storage.save_session(session)
    storage.save_screenshot(session.id, "a1", b"d1")
    storage.save_screenshot(session.id, "a2", b"d2")
    screenshots = storage.list_screenshots(session.id)
    assert len(screenshots) == 2


@pytest.mark.asyncio
async def test_list_screenshots_empty(storage):
    session = Session()
    await storage.save_session(session)
    screenshots = storage.list_screenshots(session.id)
    assert len(screenshots) == 0


# ─── Daily Stats ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_daily_stats(storage):
    session = Session()
    await storage.save_session(session)
    stats = await storage.get_daily_stats(days=30)
    assert len(stats) >= 1
    assert stats[0]["sessions"] >= 1


@pytest.mark.asyncio
async def test_get_daily_stats_empty(storage):
    stats = await storage.get_daily_stats(days=0)
    assert len(stats) == 0


# ─── Auto Cleanup ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_cleanup():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    screenshot_dir = os.path.join(tmpdir, "screenshots")
    s = StorageBackend(db_path=db_path, screenshot_dir=screenshot_dir, auto_cleanup_days=0)
    await s.connect()
    old_session = Session(status=SessionStatus.COMPLETED, created_at=datetime(2020, 1, 1), updated_at=datetime(2020, 1, 1))
    active_session = Session(status=SessionStatus.RUNNING)
    await s.save_session(old_session)
    await s.save_session(active_session)
    count = await s.auto_cleanup()
    assert count == 1
    with pytest.raises(SessionNotFound):
        await s.load_session(old_session.id)
    loaded = await s.load_session(active_session.id)
    assert loaded.id == active_session.id
    await s.close()


@pytest.mark.asyncio
async def test_auto_cleanup_nothing_to_clean(storage):
    session = Session(status=SessionStatus.RUNNING)
    await storage.save_session(session)
    count = await storage.auto_cleanup()
    assert count == 0


# ─── Export / Import ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_session_json(storage):
    session = Session()
    await storage.save_session(session)
    a = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    await storage.save_action(a)
    exported = await storage.export_session_json(session.id)
    data = json.loads(exported)
    assert data["version"] == "1.0"
    assert data["total_actions"] == 1
    assert data["session"]["id"] == session.id
    assert len(data["actions"]) == 1


@pytest.mark.asyncio
async def test_import_session_json(storage):
    session = Session()
    a = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=10.0)
    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "session": session.model_dump(),
        "actions": [a.model_dump()],
        "total_actions": 1,
    }
    json_str = json.dumps(export_data, default=str)
    imported_id = await storage.import_session_json(json_str)
    assert imported_id == session.id
    loaded = await storage.load_session(session.id)
    assert loaded.id == session.id


# ─── Error / Edge Cases ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sessions_empty_result(storage):
    sessions = await storage.list_sessions(status="nonexistent")
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_get_action_count_no_actions(storage):
    session = Session()
    await storage.save_session(session)
    count = await storage.get_action_count(session.id)
    assert count == 0


@pytest.mark.asyncio
async def test_update_session_status_cancelled(storage):
    session = Session()
    await storage.save_session(session)
    await storage.update_session_status(session.id, SessionStatus.CANCELLED, error="cancelled by user")
    loaded = await storage.load_session(session.id)
    assert loaded.status == SessionStatus.CANCELLED
    assert loaded.error == "cancelled by user"
