from __future__ import annotations

from collections.abc import Callable

import gradio as gr

from computeforge.observability.storage import StorageBackend


def create_monitor_tab(storage: StorageBackend, run_async: Callable) -> None:
    """Create the live session monitoring tab."""

    def format_status(status: str) -> str:
        colors = {
            "running": "🟢 Running",
            "paused": "🟡 Paused",
            "completed": "✅ Completed",
            "failed": "❌ Failed",
            "pending": "⏳ Pending",
            "cancelled": "🚫 Cancelled",
        }
        return colors.get(status, status)

    def refresh_sessions() -> tuple[list[list[str]], str]:
        try:
            sessions = run_async(storage.list_sessions(limit=20))
            if not sessions:
                return [], "No active sessions"
            rows = []
            for s in sessions:
                rows.append([
                    s.id[:8] + "...",
                    format_status(s.status.value),
                    str(s.action_count),
                    s.started_at.strftime("%H:%M:%S") if s.started_at else "-",
                    s.config.base_url or "-",
                ])
            return rows, f"{len(sessions)} session(s) loaded"
        except Exception as e:
            return [], f"Error: {e}"

    def view_session_details(session_id_prefix: str, state: dict) -> tuple[str, str, str, str, str]:
        try:
            sessions = run_async(storage.list_sessions(limit=50))
            for s in sessions:
                if s.id.startswith(session_id_prefix):
                    actions = run_async(storage.load_actions(s.id, limit=5))
                    action_text = ""
                    for a in actions:
                        action_text += f"  • {a.type} → {a.status.value}"
                        if a.duration_ms:
                            action_text += f" ({a.duration_ms:.0f}ms)"
                        if a.error:
                            action_text += f" [error: {a.error}]"
                        action_text += "\n"
                    return (
                        s.id,
                        s.status.value,
                        f"{s.action_count} actions",
                        action_text or "No actions yet",
                        str(s.config.model_dump_json(indent=2)),
                    )
            return "Not found", "", "", "", ""
        except Exception as e:
            return f"Error: {e}", "", "", ""

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Active Sessions")

            refresh_btn = gr.Button("🔄 Refresh", variant="primary", size="sm")
            status_display = gr.Markdown("Ready")

            sessions_table = gr.Dataframe(
                headers=["ID", "Status", "Actions", "Started", "Base URL"],
                label="Sessions",
                interactive=False,
                row_count=10,
            )

        with gr.Column(scale=1):
            gr.Markdown("### 📋 Session Details")
            session_id_display = gr.Textbox(label="Session ID", interactive=False)
            session_status = gr.Textbox(label="Status", interactive=False)
            session_summary = gr.Textbox(label="Summary", interactive=False)
            recent_actions = gr.Textbox(label="Recent Actions", lines=6, interactive=False)
            session_config = gr.Textbox(label="Config", lines=4, interactive=False)

    session_input = gr.Textbox(
        label="Enter Session ID prefix to view details",
        placeholder="Paste session ID...",
    )

    session_input.submit(
        fn=view_session_details,
        inputs=[session_input, gr.State({})],
        outputs=[session_id_display, session_status, session_summary, recent_actions, session_config],
    )

    refresh_btn.click(
        fn=refresh_sessions,
        inputs=[],
        outputs=[sessions_table, status_display],
    )
