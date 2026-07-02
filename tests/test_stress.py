"""Stress and performance tests.

These tests verify the system can handle concurrent operations
and large data volumes without issues.
"""

import os
import tempfile
import time

import pytest

from computeforge.models.action import ActionRecord, ActionStatus
from computeforge.models.session import Session
from computeforge.observability.storage import StorageBackend


@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_bulk_action_save():
    """Save 1000 actions and verify retrieval."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "stress.db")
    storage = StorageBackend(db_path=db_path)
    await storage.connect()

    session = Session()
    await storage.save_session(session)

    start = time.time()
    for i in range(1000):
        action = ActionRecord(
            session_id=session.id,
            type="click" if i % 2 == 0 else "navigate",
            status=ActionStatus.SUCCEEDED,
            duration_ms=float(i),
        )
        await storage.save_action(action)
    elapsed = time.time() - start
    print(f"\nBulk save 1000 actions: {elapsed:.2f}s ({1000/elapsed:.0f} actions/s)")

    count = await storage.get_action_count(session.id)
    assert count == 1000

    actions = await storage.load_actions(session.id, limit=1000)
    assert len(actions) == 1000

    await storage.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_multiple_sessions():
    """Create 100 sessions with actions each."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "multi.db")
    storage = StorageBackend(db_path=db_path)
    await storage.connect()

    start = time.time()
    for i in range(100):
        session = Session()
        session.metadata = {"index": i}
        await storage.save_session(session)
        for j in range(10):
            action = ActionRecord(
                session_id=session.id,
                type="screenshot",
                status=ActionStatus.SUCCEEDED,
                duration_ms=float(j) * 10,
            )
            await storage.save_action(action)
    elapsed = time.time() - start
    print(f"\nBulk 100 sessions x 10 actions: {elapsed:.2f}s")

    stats = await storage.get_session_stats()
    assert stats["total_sessions"] == 100
    assert stats["total_actions"] == 1000

    await storage.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_search():
    """Test search performance with many sessions."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "search.db")
    storage = StorageBackend(db_path=db_path)
    await storage.connect()

    for i in range(50):
        session = Session()
        session.metadata = {"task": f"searchable task {i}"}
        await storage.save_session(session)

    start = time.time()
    results = await storage.list_sessions(search="searchable", limit=50)
    elapsed = time.time() - start
    print(f"\nSearch 50 sessions: {elapsed*1000:.1f}ms, found {len(results)}")

    assert len(results) >= 50
    await storage.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_concurrent_storage():
    """Test basic concurrent storage operations."""
    import asyncio
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "concurrent.db")
    storage = StorageBackend(db_path=db_path)
    await storage.connect()

    async def create_session_and_actions(idx: int) -> int:
        session = Session()
        session.metadata = {"concurrent_idx": idx}
        await storage.save_session(session)
        for _j in range(5):
            a = ActionRecord(session_id=session.id, type="click", status=ActionStatus.SUCCEEDED, duration_ms=1.0)
            await storage.save_action(a)
        return idx

    # Run 20 concurrent tasks
    tasks = [create_session_and_actions(i) for i in range(20)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 20

    stats = await storage.get_session_stats()
    assert stats["total_sessions"] >= 20
    assert stats["total_actions"] >= 100

    await storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--slow"])
