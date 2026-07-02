from __future__ import annotations

from collections.abc import Callable

import gradio as gr

from computeforge.observability.storage import StorageBackend


def create_replay_tab(storage: StorageBackend, run_async: Callable) -> None:
    """Create the replay viewer tab with step-by-step navigation."""

    def load_session_list() -> list[list[str]]:
        try:
            sessions = run_async(storage.list_sessions(limit=50))
            return [
                [s.id[:8] + "...", s.status.value, str(s.action_count), s.created_at.strftime("%Y-%m-%d %H:%M")]
                for s in sessions
            ]
        except Exception:
            return []

    def load_replay_data(session_id_prefix: str, state: dict) -> tuple:
        try:
            sessions = run_async(storage.list_sessions(limit=50))
            target = None
            for s in sessions:
                if s.id.startswith(session_id_prefix):
                    target = s
                    break
            if target is None:
                return "Session not found", "", gr.Slider(minimum=0, maximum=1, value=0, step=1, label="Step"), "No actions", None, ""

            actions = run_async(storage.load_actions(target.id))
            action_texts = []
            for i, a in enumerate(actions):
                icon = "✅" if a.status.value == "succeeded" else "❌" if a.status.value == "failed" else "🚫"
                action_texts.append(f"**Step {i}:** {icon} `{a.type}` ({a.duration_ms:.0f}ms)\n> Params: {a.params}")

            replay_text = "\n\n".join(action_texts) if action_texts else "No actions recorded"

            max_step = max(0, len(actions) - 1)
            state["session_id"] = target.id
            state["actions"] = actions

            return target.id, target.status.value, gr.Slider(minimum=0, maximum=max(1, max_step), value=0, step=1, label="Step"), replay_text, None, ""
        except Exception as e:
            return f"Error: {e}", "", gr.Slider(minimum=0, maximum=1, value=0, step=1, label="Step"), "Error loading", None, ""

    def update_step_view(step_index: int, state: dict) -> tuple:
        actions = state.get("actions", [])
        if not actions or step_index >= len(actions):
            return "No data for this step", "N/A", "N/A"

        action = actions[step_index]
        icon = "✅" if action.status.value == "succeeded" else "❌" if action.status.value == "failed" else "🚫"
        detail = f"### Step {step_index}: {icon} `{action.type}`\n\n"
        detail += f"**Status:** {action.status.value}\n"
        detail += f"**Duration:** {action.duration_ms:.0f}ms\n"
        if action.params:
            detail += f"**Params:** ```json\n{action.params}\n```\n"
        if action.result:
            detail += f"**Result:** ```json\n{action.result}\n```\n"
        if action.error:
            detail += f"**Error:** {action.error}\n"
        if action.safety_decision:
            detail += f"**Safety:** {action.safety_decision}\n"

        screenshot_img = None
        screenshot_path = action.screenshot_after or action.screenshot_before
        if screenshot_path:
            try:
                img_data = storage.load_screenshot(screenshot_path)
                if img_data:
                    screenshot_img = img_data
            except Exception:
                pass

        risk_info = f"Risk: {action.risk_score}" if action.risk_score else "Risk: N/A"

        return detail, risk_info, screenshot_img

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎞️ Session Replay")
            session_list = gr.Dataframe(
                headers=["ID", "Status", "Actions", "Created"],
                label="Available Sessions",
                interactive=False,
                row_count=8,
            )
            refresh_btn = gr.Button("🔄 Refresh List", variant="secondary", size="sm")

        with gr.Column(scale=2):
            session_input = gr.Textbox(
                label="Session ID (or prefix)",
                placeholder="Paste session ID...",
            )
            load_btn = gr.Button("🎬 Load Session", variant="primary")

            with gr.Row():
                session_id_display = gr.Textbox(label="Session ID", interactive=False, scale=2)
                session_status_display = gr.Textbox(label="Status", interactive=False, scale=1)

            step_slider = gr.Slider(minimum=0, maximum=1, value=0, step=1, label="Step", interactive=True)

            with gr.Row():
                with gr.Column(scale=1):
                    risk_info = gr.Markdown("### Risk Assessment")
                    step_actions = gr.Textbox(label="All Steps", lines=8, max_lines=20, interactive=False)

                with gr.Column(scale=1):
                    screenshot_display = gr.Image(label="Screenshot", type="pil", height=400)

            step_detail = gr.Markdown("### Step Details")

    state = gr.State({})

    refresh_btn.click(fn=load_session_list, inputs=[], outputs=[session_list])

    load_btn.click(
        fn=load_replay_data,
        inputs=[session_input, state],
        outputs=[session_id_display, session_status_display, step_slider, step_actions, screenshot_display, risk_info],
    )

    step_slider.change(
        fn=update_step_view,
        inputs=[step_slider, state],
        outputs=[step_detail, risk_info, screenshot_display],
    )
