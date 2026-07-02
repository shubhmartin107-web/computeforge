from unittest.mock import AsyncMock, MagicMock

import pytest

from computeforge.models.action import ActionStatus
from computeforge.models.session import SessionStatus
from computeforge.observability.recorder import SessionRecorder
from tests.factories import make_action_request, make_action_result, make_session


@pytest.fixture
def mock_storage():
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.save_session = AsyncMock()
    mock.save_action = AsyncMock()
    mock.save_event = AsyncMock()
    mock.add_annotation = AsyncMock(return_value="ann-id")
    return mock


@pytest.mark.asyncio
async def test_recorder_initialization():
    recorder = SessionRecorder()
    assert recorder._connected is False
    assert recorder._current_session is None
    assert recorder._observers == []
    assert recorder._action_buffer == []
    assert recorder._buffer_size == 10


@pytest.mark.asyncio
async def test_recorder_initialization_with_storage(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    assert recorder.storage is mock_storage


@pytest.mark.asyncio
async def test_connect_and_close(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    await recorder.connect()
    mock_storage.connect.assert_awaited_once()
    assert recorder._connected is True
    await recorder.close()
    mock_storage.close.assert_awaited_once()
    assert recorder._connected is False


@pytest.mark.asyncio
async def test_record_session_create(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.save_session.assert_awaited_once_with(session)
    mock_storage.save_event.assert_awaited_once()
    assert recorder.current_session is session


@pytest.mark.asyncio
async def test_record_session_update(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.reset_mock()
    updated = make_session(id=session.id, status=SessionStatus.COMPLETED)
    await recorder.record_session_update(updated)
    mock_storage.save_session.assert_awaited_once_with(updated)
    assert recorder.current_session is updated


@pytest.mark.asyncio
async def test_record_session_end(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.reset_mock()
    await recorder.record_session_end(session)
    mock_storage.save_session.assert_awaited_once_with(session)
    mock_storage.save_event.assert_awaited_once()
    assert recorder._action_buffer == []


@pytest.mark.asyncio
async def test_record_action_with_success(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.reset_mock()
    request = make_action_request()
    result = make_action_result(success=True, duration_ms=50.0)
    record = await recorder.record_action(request=request, result=result)
    assert record.status == ActionStatus.SUCCEEDED
    assert record.duration_ms == 50.0
    assert record.session_id == session.id
    assert record.result == result.data
    mock_storage.save_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_action_with_failure(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.reset_mock()
    request = make_action_request()
    result = make_action_result(success=False, error="Something went wrong", duration_ms=10.0)
    record = await recorder.record_action(request=request, result=result)
    assert record.status == ActionStatus.FAILED
    assert record.error == "Something went wrong"
    assert record.duration_ms == 10.0


@pytest.mark.asyncio
async def test_record_action_blocked_by_safety(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    request = make_action_request()
    record = await recorder.record_action(
        request=request,
        result=None,
        safety_decision="deny",
        risk_score=0.9,
    )
    assert record.status == ActionStatus.BLOCKED
    assert record.safety_decision == "deny"
    assert record.risk_score == 0.9


@pytest.mark.asyncio
async def test_record_safety_block(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    request = make_action_request()
    record = await recorder.record_safety_block(request=request, reason="Dangerous action", risk_score=0.95)
    assert record.status == ActionStatus.FAILED
    assert record.safety_decision == "deny"
    assert record.error == "Dangerous action"
    assert record.risk_score == 0.95


@pytest.mark.asyncio
async def test_observer_notification(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    observed = []

    async def observer(rec, res):
        observed.append((rec, res))

    recorder.add_observer(observer)
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    assert len(observed) == 1
    assert observed[0][0] is not None
    assert observed[0][1] is result


@pytest.mark.asyncio
async def test_observer_remove(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    observed = []

    async def observer(rec, res):
        observed.append(1)

    recorder.add_observer(observer)
    recorder.remove_observer(observer)
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    assert len(observed) == 0


@pytest.mark.asyncio
async def test_buffer_auto_flush(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    recorder._buffer_size = 3
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.save_action.reset_mock()
    for _ in range(3):
        request = make_action_request()
        result = make_action_result()
        await recorder.record_action(request=request, result=result)
    assert mock_storage.save_action.await_count >= 3


@pytest.mark.asyncio
async def test_add_annotation(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    ann_id = await recorder.add_annotation(content="Test annotation", atype="note")
    mock_storage.add_annotation.assert_awaited_once_with(session.id, "Test annotation", None, "note")
    assert ann_id == "ann-id"


@pytest.mark.asyncio
async def test_add_annotation_no_session(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    ann_id = await recorder.add_annotation(content="Test")
    assert ann_id is None


@pytest.mark.asyncio
async def test_event_streaming(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.save_event.reset_mock()
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    mock_storage.save_event.assert_awaited_once()
    call = mock_storage.save_event.await_args
    assert call.args[1] == "action_completed"


@pytest.mark.asyncio
async def test_record_actions_batch(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    mock_storage.save_action.reset_mock()
    pairs = [(make_action_request(), make_action_result()) for _ in range(3)]
    records = await recorder.record_actions_batch(pairs)
    assert len(records) == 3
    assert mock_storage.save_action.await_count >= 3


@pytest.mark.asyncio
async def test_observer_error_isolation(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    observed = []

    async def failing_observer(rec, res):
        raise ValueError("Observer error")

    async def good_observer(rec, res):
        observed.append(1)

    recorder.add_observer(failing_observer)
    recorder.add_observer(good_observer)
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    assert len(observed) == 1


@pytest.mark.asyncio
async def test_flush_explicit(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    assert len(recorder._action_buffer) == 1
    await recorder.flush()
    assert len(recorder._action_buffer) == 0
    mock_storage.save_action.assert_awaited()


@pytest.mark.asyncio
async def test_observer_sync_notification(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    observed = []

    def observer(rec, res):
        observed.append((rec, res))

    recorder.add_observer(observer)
    request = make_action_request()
    result = make_action_result()
    await recorder.record_action(request=request, result=result)
    assert len(observed) == 1
    assert observed[0][0] is not None
    assert observed[0][1] is result


@pytest.mark.asyncio
async def test_make_recorder_hooks(mock_storage):
    recorder = SessionRecorder(storage=mock_storage)
    session = make_session()
    await recorder.record_session_create(session)
    pre_hook, post_hook, safety_hook = recorder.make_recorder_hooks()
    request = make_action_request()
    result = make_action_result()
    await pre_hook(request)
    await post_hook(request, result)
    await safety_hook(request)
    assert len(recorder._action_buffer) == 1
