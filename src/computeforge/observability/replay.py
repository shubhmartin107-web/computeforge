from __future__ import annotations

import io
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from computeforge.models.action import ActionRecord, ActionStatus
from computeforge.models.session import Session
from computeforge.observability.storage import StorageBackend


class ReplayEngine:
    """Advanced replay engine with step-by-step navigation, video generation, and export.

    Features:
    - Step-by-step action replay with screenshots
    - Video generation from session screenshots (GIF)
    - Session comparison
    - Performance analysis and statistics
    - Export to multiple formats (JSON, HTML, Markdown)
    - Action search and filtering
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    # ─── Session Access ───────────────────────────────────────────────

    async def get_session(self, session_id: str) -> Session:
        return await self._storage.load_session(session_id)

    async def get_actions(self, session_id: str) -> list[ActionRecord]:
        return await self._storage.load_actions(session_id)

    async def get_action(self, action_id: str) -> ActionRecord | None:
        return await self._storage.load_action(action_id)

    async def stream_actions(self, session_id: str) -> AsyncGenerator[ActionRecord, None]:
        return self._storage.stream_actions(session_id)

    async def get_screenshot(self, path: str) -> bytes | None:
        return self._storage.load_screenshot(path)

    async def get_action_at_index(self, session_id: str, index: int) -> ActionRecord | None:
        actions = await self._storage.load_actions(session_id, limit=1, offset=index)
        return actions[0] if actions else None

    async def session_exists(self, session_id: str) -> bool:
        try:
            await self._storage.load_session(session_id)
            return True
        except Exception:
            return False

    # ─── Summary ──────────────────────────────────────────────────────

    async def get_session_summary(self, session_id: str) -> dict[str, Any]:
        session = await self.get_session(session_id)
        actions = await self.get_actions(session_id)
        succeeded = sum(1 for a in actions if a.status == ActionStatus.SUCCEEDED)
        failed = sum(1 for a in actions if a.status == ActionStatus.FAILED)
        blocked = sum(1 for a in actions if a.status == ActionStatus.BLOCKED)
        total_duration = sum(a.duration_ms for a in actions)

        # Action type breakdown
        type_breakdown: dict[str, int] = {}
        for a in actions:
            type_breakdown[a.type] = type_breakdown.get(a.type, 0) + 1

        # Timeline
        timeline = [
            {
                "index": i,
                "type": a.type,
                "status": a.status.value,
                "duration_ms": a.duration_ms,
                "error": a.error,
                "timestamp": a.created_at.isoformat() if a.created_at else None,
            }
            for i, a in enumerate(actions)
        ]

        return {
            "session_id": session.id,
            "status": session.status.value,
            "total_actions": len(actions),
            "succeeded": succeeded,
            "failed": failed,
            "blocked": blocked,
            "success_rate": round(succeeded / max(len(actions), 1) * 100, 1),
            "total_duration_ms": round(total_duration, 2),
            "avg_action_duration_ms": round(total_duration / max(len(actions), 1), 2),
            "type_breakdown": type_breakdown,
            "timeline": timeline,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "error": session.error,
            "has_screenshots": any(a.screenshot_after for a in actions),
        }

    # ─── Screenshot GIF Generation ───────────────────────────────────

    async def generate_gif(
        self,
        session_id: str,
        output_path: str | Path | None = None,
        fps: int = 2,
        max_width: int = 800,
    ) -> bytes:
        """Generate an animated GIF from session screenshots."""
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("Pillow is required for GIF generation") from None

        actions = await self.get_actions(session_id)
        frames = []
        for action in actions:
            screenshot_path = action.screenshot_after or action.screenshot_before
            if screenshot_path:
                img_bytes = self._storage.load_screenshot(screenshot_path)
                if img_bytes:
                    img = Image.open(io.BytesIO(img_bytes))
                    if max_width and img.width > max_width:
                        ratio = max_width / img.width
                        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)  # type: ignore[assignment]
                    frames.append(img)

        if not frames:
            return b""

        buf = io.BytesIO()
        duration = max(100, int(1000 / fps))
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=True,
        )

        if output_path:
            Path(output_path).write_bytes(buf.getvalue())

        return buf.getvalue()

    # ─── Export ───────────────────────────────────────────────────────

    async def export_html(self, session_id: str) -> str:
        """Export session to a standalone HTML report."""
        summary = await self.get_session_summary(session_id)
        actions = await self.get_actions(session_id)

        html_parts = [
            f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Session Report - {session_id[:8]}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
h1 {{ color: #333; }}
.summary {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.action {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #ddd; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
.action.succeeded {{ border-left-color: #4CAF50; }}
.action.failed {{ border-left-color: #f44336; }}
.action.blocked {{ border-left-color: #FF9800; }}
.meta {{ color: #666; font-size: 0.9em; }}
pre {{ background: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto; }}
img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
</style></head><body>
<h1>📊 ComputeForge Session Report</h1>
<div class="summary">
<h2>Session Summary</h2>
<table>
<tr><td>ID</td><td>{summary["session_id"]}</td></tr>
<tr><td>Status</td><td>{summary["status"]}</td></tr>
<tr><td>Total Actions</td><td>{summary["total_actions"]}</td></tr>
<tr><td>Success Rate</td><td>{summary["success_rate"]}%</td></tr>
<tr><td>Total Duration</td><td>{summary["total_duration_ms"]}ms</td></tr>
</table>
</div>
"""
        ]

        for i, a in enumerate(actions):
            css_class = (
                a.status.value if a.status.value in ("succeeded", "failed", "blocked") else ""
            )
            html_parts.append(f'<div class="action {css_class}">')
            html_parts.append(
                f'<h3>Step {i}: {a.type} <span class="meta">({a.duration_ms:.0f}ms)</span></h3>'
            )
            html_parts.append(f'<p class="meta">Status: {a.status.value}')
            if a.error:
                html_parts.append(f" | Error: {a.error}")
            html_parts.append("</p>")
            if a.params:
                html_parts.append(f"<pre>{json.dumps(a.params, indent=2)}</pre>")
            if a.screenshot_after:
                img_bytes = self._storage.load_screenshot(a.screenshot_after)
                if img_bytes:
                    import base64

                    b64 = base64.b64encode(img_bytes).decode()
                    html_parts.append(f'<img src="data:image/png;base64,{b64}" />')
            html_parts.append("</div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    async def export_markdown(self, session_id: str) -> str:
        """Export session to Markdown."""
        summary = await self.get_session_summary(session_id)
        actions = await self.get_actions(session_id)

        lines = [
            f"# Session Report: {session_id[:8]}",
            "",
            "## Summary",
            f"- **Status:** {summary['status']}",
            f"- **Total Actions:** {summary['total_actions']}",
            f"- **Success Rate:** {summary['success_rate']}%",
            f"- **Duration:** {summary['total_duration_ms']}ms",
            "",
            "## Action Timeline",
            "",
        ]

        for i, a in enumerate(actions):
            icon = {"succeeded": "✅", "failed": "❌", "blocked": "🚫"}.get(a.status.value, "➡️")
            lines.append(f"### Step {i}: {icon} `{a.type}`")
            lines.append(f"- Status: {a.status.value} ({a.duration_ms:.0f}ms)")
            if a.error:
                lines.append(f"- Error: {a.error}")
            if a.params:
                lines.append(f"- Params: `{json.dumps(a.params)}`")
            lines.append("")

        return "\n".join(lines)

    # ─── Comparison ────────────────────────────────────────────────────

    async def compare_sessions(self, session_ids: list[str]) -> list[dict[str, Any]]:
        """Compare multiple sessions side by side."""
        summaries = []
        for sid in session_ids:
            try:
                summary = await self.get_session_summary(sid)
                summaries.append(summary)
            except Exception:  # nosec
                continue
        return summaries

    # ─── Search ────────────────────────────────────────────────────────

    async def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search across all sessions."""
        results = []
        sessions = await self._storage.list_sessions(search=query, limit=limit)
        for s in sessions:
            results.append(
                {
                    "id": s.id,
                    "status": s.status.value,
                    "action_count": s.action_count,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "error": s.error,
                }
            )
        return results
