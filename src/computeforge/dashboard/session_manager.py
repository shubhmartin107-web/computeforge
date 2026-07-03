from __future__ import annotations

from collections.abc import Callable

import gradio as gr

from computeforge.observability.storage import StorageBackend


def create_session_manager_tab(storage: StorageBackend, run_async: Callable) -> None:
    """Create the session management tab."""

    def list_all_sessions() -> list[list[str]]:
        try:
            sessions = run_async(storage.list_sessions(limit=100))
            return [
                [
                    s.id[:8] + "...",
                    s.status.value,
                    str(s.action_count),
                    s.created_at.strftime("%Y-%m-%d %H:%M"),
                    s.ended_at.strftime("%Y-%m-%d %H:%M") if s.ended_at else "-",
                    s.error or "-",
                ]
                for s in sessions
            ]
        except Exception:
            return []

    def get_stats() -> str:
        try:
            stats = run_async(storage.get_session_stats())
            by_status = stats.get("by_status", {})
            parts = [f"**Total Sessions:** {stats.get('total_sessions', 0)}"]
            parts.append(f"**Total Actions:** {stats.get('total_actions', 0)}")
            if by_status:
                parts.append(
                    "**By Status:** " + ", ".join(f"{k}: {v}" for k, v in by_status.items())
                )
            return "\n\n".join(parts)
        except Exception as e:
            return f"Error: {e}"

    def delete_session(session_id_prefix: str) -> str:
        try:
            sessions = run_async(storage.list_sessions(limit=100))
            for s in sessions:
                if s.id.startswith(session_id_prefix):
                    run_async(storage.delete_session(s.id))
                    return f"✅ Deleted session {s.id[:8]}..."
            return "❌ Session not found"
        except Exception as e:
            return f"Error: {e}"

    def export_session(session_id_prefix: str) -> str:
        try:
            sessions = run_async(storage.list_sessions(limit=100))
            for s in sessions:
                if s.id.startswith(session_id_prefix):
                    actions = run_async(storage.load_actions(s.id))
                    import json

                    export = {
                        "session": s.model_dump(),
                        "actions": [a.model_dump() for a in actions],
                    }
                    return f"```json\n{json.dumps(export, indent=2)}\n```"
            return "Session not found"
        except Exception as e:
            return f"Error: {e}"

    refresh_btn = gr.Button("🔄 Refresh All", variant="primary")

    stats_md = gr.Markdown("Loading...")

    sessions_table = gr.Dataframe(
        headers=["ID", "Status", "Actions", "Created", "Ended", "Error"],
        label="All Sessions",
        interactive=False,
        row_count=15,
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🗑️ Delete Session")
            delete_input = gr.Textbox(
                label="Session ID prefix",
                placeholder="Enter session ID prefix to delete",
            )
            delete_btn = gr.Button("🗑️ Delete", variant="stop")
            delete_result = gr.Markdown("")

        with gr.Column(scale=1):
            gr.Markdown("### 📤 Export Session")
            export_input = gr.Textbox(
                label="Session ID prefix",
                placeholder="Enter session ID prefix to export",
            )
            export_btn = gr.Button("📤 Export", variant="secondary")
            export_result = gr.Markdown("")

    def refresh_all():
        return get_stats(), list_all_sessions()

    refresh_btn.click(fn=refresh_all, inputs=[], outputs=[stats_md, sessions_table])

    delete_btn.click(fn=delete_session, inputs=[delete_input], outputs=[delete_result])
    export_btn.click(fn=export_session, inputs=[export_input], outputs=[export_result])

    # Initial load
    stats_md.value = get_stats()
    sessions_table.value = list_all_sessions()
