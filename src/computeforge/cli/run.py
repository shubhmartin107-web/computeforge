from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from computeforge.core.engine import ComputeEngine
from computeforge.models.config import EngineConfig

console = Console()


def run_command(
    url: str = typer.Argument(..., help="URL to navigate to"),
    headless: bool = typer.Option(True, "--headless", help="Run browser in headless mode"),
    visible: bool = typer.Option(
        False, "--visible", help="Show browser window (overrides --headless)"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file for session data"),
    max_actions: int = typer.Option(10, "--max-actions", "-n", help="Maximum actions to execute"),
):
    """Navigate to a URL and perform basic computer-use actions."""
    is_headless = not visible if visible else headless

    async def _run():
        config = EngineConfig()
        config.browser.headless = is_headless
        engine = ComputeEngine(config)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Starting browser...", total=None)

                await engine.create_session()
                await engine.start_session()

                progress.update(task, description=f"Navigating to {url}")
                result = await engine.navigate(url)
                if not result.success:
                    console.print(f"[red]Navigation failed: {result.error}[/red]")
                    return

                page_info = await engine.get_page_info()
                console.print(f"[green]Navigated to[/green] {page_info['url']}")
                console.print(f"[green]Title:[/green] {page_info['title']}")

                progress.update(task, description="Taking screenshot")
                screenshot_result = await engine.screenshot()
                if screenshot_result.success:
                    console.print("[green]Screenshot captured[/green]")

                progress.update(task, description="Extracting page text")
                text_result = await engine.extract_text()
                if text_result.success and text_result.data:
                    text = text_result.data.get("text", "")
                    console.print(f"[green]Page text[/green] ({len(text)} chars)")

                progress.update(task, description="Scrolling")
                await engine.scroll(delta_y=500)

                progress.update(task, description="Taking post-scroll screenshot")
                await engine.screenshot()

            console.print("\n[bold green]Session complete![/bold green]")
            console.print(f"  Actions executed: {engine.session.action_count}")
            console.print(f"  Status: {engine.session.status.value}")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        finally:
            await engine.stop_session()

    asyncio.run(_run())
