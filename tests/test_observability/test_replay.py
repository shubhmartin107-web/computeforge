import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.models.action import ActionRecord, ActionStatus
from computeforge.models.session import Session
from computeforge.observability.replay import ReplayEngine


class TestReplayEngine:
    @pytest.mark.asyncio
    async def test_get_session_summary(self, storage):
        session = Session()
        await storage.save_session(session)
        for i in range(5):
            action = ActionRecord(
                session_id=session.id,
                type="click" if i % 2 == 0 else "navigate",
                status=ActionStatus.SUCCEEDED,
                duration_ms=100.0 + i * 10,
            )
            await storage.save_action(action)

        replay = ReplayEngine(storage)
        summary = await replay.get_session_summary(session.id)
        assert summary["total_actions"] == 5
        assert summary["succeeded"] == 5
        assert summary["success_rate"] == 100.0
        assert "type_breakdown" in summary
        assert "timeline" in summary

    @pytest.mark.asyncio
    async def test_get_session_summary_with_failures(self, storage):
        session = Session()
        await storage.save_session(session)
        actions = [
            ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0),
            ActionRecord(session_id=session.id, type="click", status=ActionStatus.FAILED, duration_ms=50.0, error="Not found"),
            ActionRecord(session_id=session.id, type="screenshot", status=ActionStatus.BLOCKED, duration_ms=0.0),
        ]
        for a in actions:
            await storage.save_action(a)

        replay = ReplayEngine(storage)
        summary = await replay.get_session_summary(session.id)
        assert summary["total_actions"] == 3
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1
        assert summary["blocked"] == 1
        assert summary["success_rate"] == pytest.approx(33.33, rel=0.1)

    @pytest.mark.asyncio
    async def test_export_markdown(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0, params={"url": "https://example.com"})
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        md = await replay.export_markdown(session.id)
        assert "Session Report" in md
        assert "navigate" in md

    @pytest.mark.asyncio
    async def test_export_html(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0)
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        html = await replay.export_html(session.id)
        assert "DOCTYPE html" in html
        assert "Session Report" in html
        assert "navigate" in html

    @pytest.mark.asyncio
    async def test_search(self, storage):
        session = Session()
        session.metadata = {"task": "test search"}
        await storage.save_session(session)

        replay = ReplayEngine(storage)
        results = await replay.search("test")
        assert len(results) >= 1
        assert results[0]["id"] == session.id

    @pytest.mark.asyncio
    async def test_compare_sessions(self, storage):
        s1, s2 = Session(), Session()
        await storage.save_session(s1)
        await storage.save_session(s2)
        for s in [s1, s2]:
            a = ActionRecord(session_id=s.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0)
            await storage.save_action(a)

        replay = ReplayEngine(storage)
        comparisons = await replay.compare_sessions([s1.id, s2.id])
        assert len(comparisons) == 2

    @pytest.mark.asyncio
    async def test_get_action(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED)
        await storage.save_action(action)
        replay = ReplayEngine(storage)
        result = await replay.get_action(action.id)
        assert result is not None
        assert result.id == action.id

    @pytest.mark.asyncio
    async def test_get_action_not_found(self, storage):
        replay = ReplayEngine(storage)
        result = await replay.get_action("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_stream_actions(self, storage):
        session = Session()
        await storage.save_session(session)
        for i in range(3):
            action = ActionRecord(session_id=session.id, type=f"action_{i}", status=ActionStatus.SUCCEEDED)
            await storage.save_action(action)
        replay = ReplayEngine(storage)
        gen = await replay.stream_actions(session.id)
        actions = [a async for a in gen]
        assert len(actions) == 3

    @pytest.mark.asyncio
    async def test_get_screenshot(self, storage):
        replay = ReplayEngine(storage)
        screenshot_path = storage.save_screenshot("session1", "action1", b"fake_image_data")
        result = await replay.get_screenshot(screenshot_path)
        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_get_screenshot_not_found(self, storage):
        replay = ReplayEngine(storage)
        result = await replay.get_screenshot("/nonexistent/path_12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_action_at_index(self, storage):
        session = Session()
        await storage.save_session(session)
        for i in range(5):
            action = ActionRecord(session_id=session.id, type=f"action_{i}", status=ActionStatus.SUCCEEDED)
            await storage.save_action(action)
        replay = ReplayEngine(storage)
        result = await replay.get_action_at_index(session.id, 2)
        assert result is not None
        assert result.type == "action_2"

    @pytest.mark.asyncio
    async def test_get_action_at_index_out_of_range(self, storage):
        session = Session()
        await storage.save_session(session)
        replay = ReplayEngine(storage)
        result = await replay.get_action_at_index(session.id, 0)
        assert result is None

    @pytest.mark.asyncio
    async def test_session_exists(self, storage):
        session = Session()
        await storage.save_session(session)
        replay = ReplayEngine(storage)
        assert await replay.session_exists(session.id) is True

    @pytest.mark.asyncio
    async def test_session_not_exists(self, storage):
        replay = ReplayEngine(storage)
        assert await replay.session_exists("nonexistent_session_id") is False

    @pytest.mark.asyncio
    async def test_compare_sessions_with_exceptions(self, storage):
        replay = ReplayEngine(storage)
        results = await replay.compare_sessions(["nonexistent1", "nonexistent2"])
        assert results == []

    @pytest.mark.asyncio
    async def test_generate_gif_no_frames(self, storage):
        session = Session()
        await storage.save_session(session)
        replay = ReplayEngine(storage)
        result = await replay.generate_gif(session.id)
        assert result == b""

    @pytest.mark.asyncio
    async def test_generate_gif_with_frames(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            screenshot_after=str(tmp_path / "screenshot.png"),
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 50
        mock_img.resize.return_value = mock_img
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"gif_data")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id, fps=2, max_width=800)

        assert result == b"gif_data"

    @pytest.mark.asyncio
    async def test_generate_gif_with_output_path(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            screenshot_after=str(tmp_path / "screenshot.png"),
        )
        await storage.save_action(action)

        output_path = tmp_path / "output.gif"
        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 50
        mock_img.resize.return_value = mock_img
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"gif_data")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id, output_path=str(output_path))

        assert result == b"gif_data"
        assert output_path.read_bytes() == b"gif_data"

    @pytest.mark.asyncio
    async def test_generate_gif_uses_screenshot_before_fallback(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            screenshot_before=str(tmp_path / "before.png"),
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 50
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"gif_data")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id)

        assert result == b"gif_data"

    @pytest.mark.asyncio
    async def test_export_html_with_screenshot(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            duration_ms=100.0,
            params={"url": "https://example.com"},
            screenshot_after=str(tmp_path / "screenshot.png"),
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        with patch.object(storage, "load_screenshot", return_value=b"fake_png_bytes"):
            html = await replay.export_html(session.id)

        assert "img src=" in html
        assert "base64" in html

    @pytest.mark.asyncio
    async def test_export_html_with_error(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="click",
            status=ActionStatus.FAILED,
            duration_ms=50.0,
            error="Element not found",
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        html = await replay.export_html(session.id)

        assert "Failed" in html or "Error" in html

    @pytest.mark.asyncio
    async def test_export_html_without_screenshot(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            duration_ms=100.0,
            params={"url": "https://example.com"},
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        html = await replay.export_html(session.id)

        assert "Session Report" in html
        assert "navigate" in html

    @pytest.mark.asyncio
    async def test_export_markdown_with_error(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="click",
            status=ActionStatus.FAILED,
            duration_ms=50.0,
            error="Element not found",
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        md = await replay.export_markdown(session.id)

        assert "Element not found" in md

    @pytest.mark.asyncio
    async def test_export_markdown_with_params(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            duration_ms=100.0,
            params={"url": "https://example.com"},
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        md = await replay.export_markdown(session.id)

        assert "https://example.com" in md

    @pytest.mark.asyncio
    async def test_export_markdown_blocked_status(self, storage):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="click",
            status=ActionStatus.BLOCKED,
            duration_ms=0.0,
            error="Blocked by policy",
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        md = await replay.export_markdown(session.id)

        assert "Blocked by policy" in md

    @pytest.mark.asyncio
    async def test_generate_gif_import_error(self, storage):
        session = Session()
        await storage.save_session(session)
        replay = ReplayEngine(storage)
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == 'PIL':
                raise ImportError("No module named PIL")
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            with pytest.raises(ImportError, match="Pillow is required for GIF generation"):
                await replay.generate_gif(session.id)

    @pytest.mark.asyncio
    async def test_generate_gif_resize(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            screenshot_after=str(tmp_path / "screenshot.png"),
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 1600
        mock_img.height = 900
        mock_img.resize.return_value = mock_img
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"resized_gif")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id, max_width=800)

        assert result == b"resized_gif"
        mock_img.resize.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_gif_multiple_frames(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        for i in range(3):
            action = ActionRecord(
                session_id=session.id,
                type=f"step_{i}",
                status=ActionStatus.SUCCEEDED,
                screenshot_after=str(tmp_path / f"screenshot_{i}.png"),
            )
            await storage.save_action(action)

        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 50
        mock_img.resize.return_value = mock_img
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"multi_gif")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id)

        assert result == b"multi_gif"

    @pytest.mark.asyncio
    async def test_export_html_with_all_statuses(self, storage):
        session = Session()
        await storage.save_session(session)
        actions = [
            ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0),
            ActionRecord(session_id=session.id, type="click", status=ActionStatus.FAILED, duration_ms=50.0, error="Not found"),
            ActionRecord(session_id=session.id, type="screenshot", status=ActionStatus.BLOCKED, duration_ms=0.0),
        ]
        for a in actions:
            await storage.save_action(a)

        replay = ReplayEngine(storage)
        html = await replay.export_html(session.id)
        assert "succeeded" in html
        assert "failed" in html
        assert "blocked" in html
        assert "Not found" in html
        assert "Session Report" in html

    @pytest.mark.asyncio
    async def test_export_markdown_different_statuses(self, storage):
        session = Session()
        await storage.save_session(session)
        actions = [
            ActionRecord(session_id=session.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0),
            ActionRecord(session_id=session.id, type="click", status=ActionStatus.FAILED, duration_ms=50.0, error="Error"),
            ActionRecord(session_id=session.id, type="eval", status=ActionStatus.BLOCKED, duration_ms=0.0),
        ]
        for a in actions:
            await storage.save_action(a)

        replay = ReplayEngine(storage)
        md = await replay.export_markdown(session.id)
        assert "Step 0" in md
        assert "Step 1" in md
        assert "Step 2" in md
        assert "Error" in md

    @pytest.mark.asyncio
    async def test_compare_sessions_mixed(self, storage):
        s1, s2 = Session(), Session()
        await storage.save_session(s1)
        await storage.save_session(s2)
        for s in [s1]:
            a = ActionRecord(session_id=s.id, type="navigate", status=ActionStatus.SUCCEEDED, duration_ms=100.0)
            await storage.save_action(a)

        replay = ReplayEngine(storage)
        results = await replay.compare_sessions([s1.id, s2.id, "nonexistent"])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_session_existence_and_access(self, storage):
        replay = ReplayEngine(storage)
        exists = await replay.session_exists("not_a_real_session")
        assert exists is False
        result = await replay.get_action("not_a_real_action")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_action_at_index_with_offset(self, storage):
        session = Session()
        await storage.save_session(session)
        for i in range(5):
            action = ActionRecord(session_id=session.id, type=f"action_{i}", status=ActionStatus.SUCCEEDED)
            await storage.save_action(action)
        replay = ReplayEngine(storage)
        result = await replay.get_action_at_index(session.id, 3)
        assert result is not None
        assert result.type == "action_3"

    @pytest.mark.asyncio
    async def test_generate_gif_with_fps_setting(self, storage, tmp_path):
        session = Session()
        await storage.save_session(session)
        action = ActionRecord(
            session_id=session.id,
            type="navigate",
            status=ActionStatus.SUCCEEDED,
            screenshot_after=str(tmp_path / "screenshot.png"),
        )
        await storage.save_action(action)

        replay = ReplayEngine(storage)
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 50
        mock_img.save.side_effect = lambda buf, **kw: buf.write(b"fps_gif")

        with patch.object(storage, "load_screenshot", return_value=b"png_data"):
            with patch("PIL.Image.open", return_value=mock_img):
                result = await replay.generate_gif(session.id, fps=10)

        assert result == b"fps_gif"
