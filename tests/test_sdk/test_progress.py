"""Tests for SDK progress tracking."""
from computeforge.sdk.progress import ActionProgress


class TestActionProgress:
    def test_defaults(self):
        p = ActionProgress()
        assert p.total == 0
        assert p.current == 0
        assert p.current_action == ""
        assert p.complete is False
        assert p.duration_ms == 0.0
        assert p.error is None
        assert p.metadata == {}

    def test_custom_values(self):
        p = ActionProgress(
            total=10,
            current=5,
            current_action="click",
            complete=False,
            duration_ms=123.45,
            error=None,
            metadata={"key": "value"},
        )
        assert p.total == 10
        assert p.current == 5
        assert p.current_action == "click"
        assert p.duration_ms == 123.45
        assert p.metadata == {"key": "value"}

    def test_error_field(self):
        p = ActionProgress(
            total=1, current=0, error="Something went wrong"
        )
        assert p.error == "Something went wrong"

    def test_complete_flag(self):
        p = ActionProgress(total=5, current=5, current_action="done", complete=True)
        assert p.complete is True
        assert p.current == p.total

    def test_progress_percentage(self):
        p = ActionProgress(total=100, current=25)
        pct = (p.current / p.total) * 100 if p.total > 0 else 0.0
        assert pct == 25.0

        p2 = ActionProgress(total=0, current=0)
        pct2 = (p2.current / p2.total) * 100 if p2.total > 0 else 0.0
        assert pct2 == 0.0

        p3 = ActionProgress(total=200, current=150)
        pct3 = (p3.current / p3.total) * 100 if p3.total > 0 else 0.0
        assert pct3 == 75.0


class TestProgressCallback:
    def test_sync_callback(self):
        results = []

        def callback(p: ActionProgress):
            results.append(p)

        progress = ActionProgress(total=5, current=2, current_action="navigate")
        callback(progress)
        assert len(results) == 1
        assert results[0].current == 2
        assert results[0].total == 5

    def test_async_callback_signature(self):
        async def callback(p: ActionProgress):
            pass

        assert callable(callback)
