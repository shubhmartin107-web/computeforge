from __future__ import annotations

import asyncio

import gradio as gr

from computeforge._version import __version__
from computeforge.dashboard.intervention import create_intervention_tab
from computeforge.dashboard.monitor import create_monitor_tab
from computeforge.dashboard.replay_view import create_replay_tab
from computeforge.dashboard.session_manager import create_session_manager_tab
from computeforge.observability.storage import StorageBackend


def create_dashboard(storage: StorageBackend | None = None) -> gr.Blocks:
    """Create the main ComputeForge dashboard application."""
    if storage is None:
        storage = StorageBackend()

    _loop = asyncio.new_event_loop()

    def run_async(coro):
        return _loop.run_until_complete(coro)

    async def init_storage():
        await storage.connect()

    run_async(init_storage())

    with gr.Blocks(title="ComputeForge Dashboard") as dashboard:
        gr.HTML(f"""
        <div class="computeforge-header">
            <h1>🔧 ComputeForge</h1>
            <p>Computer-Use Agent Platform v{__version__} — Monitor, Replay & Control</p>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("📊 Monitor"):
                create_monitor_tab(storage, run_async)

            with gr.Tab("🎞️ Replay"):
                create_replay_tab(storage, run_async)

            with gr.Tab("📋 Sessions"):
                create_session_manager_tab(storage, run_async)

            with gr.Tab("🛡️ Intervention"):
                create_intervention_tab()

            with gr.Tab("About"):
                gr.Markdown(f"""
                ## ComputeForge v{__version__}

                **Open-source, extensible Computer-Use Agent Platform**

                ### Architecture
                - **Core Engine**: Playwright-based browser automation
                - **Desktop Control**: PyAutoGUI + MSS backends
                - **Safety Layer**: Capability registry, risk assessment, policy enforcement
                - **Observability**: Full session recording, screenshot capture, replay
                - **Storage**: SQLite (metadata) + File system (screenshots)

                ### Key Features
                - Browser automation with smart element finding
                - Desktop-level control (click, type, screenshot)
                - Full session recording with visual replay
                - Safety guardrails with configurable policies
                - Plugin system for extensibility
                - Multiple LLM provider support

                ### Integrations
                - **FlowLens**: Observability pipeline
                - **GuardWeave**: Governance & safety
                - **SkillForge**: Reusable skills registry

                ### Resources
                - [Documentation](https://computeforge.ai/docs)
                - [GitHub](https://github.com/anomalyco/computeforge)
                - [Issues](https://github.com/anomalyco/computeforge/issues)
                """)

    return dashboard


def launch_dashboard(
    storage: StorageBackend | None = None,
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
    debug: bool = False,
) -> gr.Blocks:
    """Launch the ComputeForge dashboard."""
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="cyan",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    )
    css = """
    .computeforge-header { text-align: center; margin-bottom: 1rem; }
    .computeforge-header h1 { font-size: 2rem; font-weight: 700; }
    .computeforge-header p { color: #666; }
    """
    dashboard = create_dashboard(storage)
    dashboard.launch(
        server_name=host,
        server_port=port,
        share=share,
        debug=debug,
        theme=theme,
        css=css,
    )
    return dashboard


if __name__ == "__main__":
    launch_dashboard(debug=True)
