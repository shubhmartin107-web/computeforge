from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from computeforge.observability.replay import ReplayEngine
from computeforge.observability.storage import StorageBackend

console = Console()


def replay_command(
    session_id: str = typer.Argument(..., help="Session ID to replay"),
    step: int | None = typer.Option(None, "--step", "-s", help="Jump to specific step"),
    list_actions: bool = typer.Option(False, "--list", "-l", help="List all actions in session"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Step through actions interactively"),
):
    """Replay a recorded session step by step."""
    async def _replay():
        storage = StorageBackend()
        await storage.connect()
        replay = ReplayEngine(storage)

        if not await replay.session_exists(session_id):
            console.print(f"[red]Session not found: {session_id}[/red]")
            return

        summary = await replay.get_session_summary(session_id)
        console.print(Panel.fit(
            f"[bold]Session Replay[/bold]\n\n"
            f"ID: {summary['session_id']}\n"
            f"Status: {summary['status']}\n"
            f"Actions: {summary['total_actions']} "
            f"(✅ {summary['succeeded']} ❌ {summary['failed']} 🚫 {summary['blocked']})\n"
            f"Duration: {summary['total_duration_ms']:.0f}ms",
            title="Replay Summary",
            border_style="cyan",
        ))

        actions = await replay.get_actions(session_id)

        if list_actions:
            table = Table(title="Session Actions")
            table.add_column("#", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Duration", style="blue")
            table.add_column("Error", style="red")

            for i, a in enumerate(actions):
                status_icon = {
                    "succeeded": "✅",
                    "failed": "❌",
                    "blocked": "🚫",
                }.get(a.status.value, "⏳")
                table.add_row(
                    str(i),
                    a.type,
                    f"{status_icon} {a.status.value}",
                    f"{a.duration_ms:.0f}ms",
                    a.error or "-",
                )
            console.print(table)
            return

        if interactive:
            console.print("\n[bold]Interactive Replay[/bold] (press Enter for each step)")
            for i, a in enumerate(actions):
                status_icon = "✅" if a.status.value == "succeeded" else "❌"
                console.print(f"\n[yellow]Step {i}:[/yellow] {status_icon} [green]{a.type}[/green] ({a.duration_ms:.0f}ms)")
                if a.params:
                    console.print(f"  Params: {a.params}")
                if a.error:
                    console.print(f"  [red]Error: {a.error}[/red]")
                if a.screenshot_after:
                    img = await replay.get_screenshot(a.screenshot_after)
                    if img:
                        console.print(f"  [dim]Screenshot: {len(img)} bytes[/dim]")
                try:
                    input("  Press Enter to continue...")
                except (EOFError, KeyboardInterrupt):
                    break

            console.print("\n[bold green]Replay complete![/bold green]")
            return

        # Summary mode
        for i, a in enumerate(actions[:10]):
            status_icon = "✅" if a.status.value == "succeeded" else "❌" if a.status.value == "failed" else "🚫"
            console.print(f"  {status_icon} Step {i}: [bold]{a.type}[/bold] ({a.duration_ms:.0f}ms)")

        if len(actions) > 10:
            console.print(f"  ... and {len(actions) - 10} more actions (use --list to see all)")

        await storage.close()

    asyncio.run(_replay())
