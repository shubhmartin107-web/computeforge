from __future__ import annotations

import asyncio
import cmd
import shlex
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from computeforge._version import __version__
from computeforge.models.session import SessionConfig
from computeforge.sdk.client import ComputeForgeClient

console = Console()


class InteractiveShell(cmd.Cmd):
    """Interactive command shell for ComputeForge."""

    intro = Panel.fit(
        f"[bold cyan]ComputeForge Interactive Shell[/bold cyan] v{__version__}\n\n"
        "Type [bold]help[/bold] for commands or [bold]start[/bold] to begin a session.\n"
        "Type [bold]exit[/bold] or [bold]quit[/bold] to leave.",
        border_style="cyan",
    )
    prompt = "(computeforge) " if sys.stdout.isatty() else ">>> "

    def __init__(self):
        super().__init__()
        self._client: ComputeForgeClient | None = None
        self._loop = asyncio.new_event_loop()
        self._session_active = False

    def _run_async(self, coro):
        return self._loop.run_until_complete(coro)

    # ─── Session Commands ─────────────────────────────────────────────

    def do_start(self, arg):
        """Start a new session: start [url] [--headless]"""
        args = shlex.split(arg) if arg else []
        url = None
        headless = True
        for a in args:
            if a == "--visible":
                headless = False
            elif a.startswith("--"):
                continue
            else:
                url = a

        try:
            self._client = ComputeForgeClient()
            self._run_async(self._client.connect())
            config = SessionConfig(headless=headless)
            session = self._run_async(self._client.create_session(config=config))
            self._session_active = True
            console.print(f"[green]Session started:[/green] {session.id[:8]}...")

            if url:
                console.print(f"[yellow]Navigating to:[/yellow] {url}")
                result = self._run_async(self._client.navigate(url))
                if result.success:
                    page_info = self._run_async(self._client._engine.get_page_info())
                    console.print(f"[green]Title:[/green] {page_info.get('title', '')}")
                else:
                    console.print(f"[red]Navigation failed:[/red] {result.error}")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def do_stop(self, arg):
        """Stop the current session."""
        if self._client:
            self._run_async(self._client.close())
            self._session_active = False
            self._client = None
            console.print("[green]Session stopped.[/green]")
        else:
            console.print("[yellow]No active session.[/yellow]")

    def do_status(self, arg):
        """Show current session status."""
        if not self._client or not self._session_active:
            console.print("[yellow]No active session.[/yellow]")
            return
        state = self._run_async(self._client.get_engine_state())
        table = Table(title="Session Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        for k, v in state.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    table.add_row(f"{k}.{sk}", str(sv))
            else:
                table.add_row(k, str(v))
        console.print(table)

    # ─── Action Commands ──────────────────────────────────────────────

    def do_navigate(self, arg):
        """Navigate to a URL: navigate <url>"""
        if not self._ensure_session():
            return
        if not arg:
            console.print("[red]Usage: navigate <url>[/red]")
            return
        result = self._run_async(self._client.navigate(arg.strip()))
        if result.success:
            console.print(f"[green]Navigated to[/green] {result.data.get('url', arg)}")
        else:
            console.print(f"[red]Failed:[/red] {result.error}")

    def do_click(self, arg):
        """Click an element: click <selector>"""
        if not self._ensure_session():
            return
        if not arg:
            console.print("[red]Usage: click <selector>[/red]")
            return
        result = self._run_async(self._client.click(arg.strip()))
        console.print(
            "[green]Clicked[/green]" if result.success else f"[red]Failed: {result.error}[/red]"
        )

    def do_type(self, arg):
        """Type text: type <text> [--selector <sel>]"""
        if not self._ensure_session():
            return
        args = shlex.split(arg) if arg else []
        if not args:
            console.print("[red]Usage: type <text> [--selector <sel>][/red]")
            return
        text = args[0]
        selector = None
        if "--selector" in args:
            idx = args.index("--selector")
            if idx + 1 < len(args):
                selector = args[idx + 1]
        result = self._run_async(self._client.type_text(text, selector=selector))
        console.print(
            "[green]Typed[/green]" if result.success else f"[red]Failed: {result.error}[/red]"
        )

    def do_ss(self, arg):
        """Take a screenshot: ss"""
        if not self._ensure_session():
            return
        result = self._run_async(self._client.screenshot())
        if result.success:
            img = result.data.get("image") if result.data else None
            console.print(
                f"[green]Screenshot captured:[/green] {len(img)} bytes"
                if img
                else "[green]Screenshot captured[/green]"
            )
        else:
            console.print(f"[red]Failed: {result.error}[/red]")

    def do_scroll(self, arg):
        """Scroll: scroll [delta_y]"""
        if not self._ensure_session():
            return
        delta = int(arg) if arg else 300
        result = self._run_async(self._client.scroll(delta_y=delta))
        console.print(
            f"[green]Scrolled {delta}px[/green]"
            if result.success
            else f"[red]Failed: {result.error}[/red]"
        )

    def do_extract(self, arg):
        """Extract text: extract [selector]"""
        if not self._ensure_session():
            return
        selector = arg.strip() if arg else None
        result = self._run_async(self._client.extract_text(selector=selector))
        if result.success:
            text = result.data.get("text", "") if result.data else ""
            console.print(Markdown(text[:2000]))
        else:
            console.print(f"[red]Failed: {result.error}[/red]")

    def do_eval(self, arg):
        """Evaluate JavaScript: eval <script>"""
        if not self._ensure_session():
            return
        if not arg:
            console.print("[red]Usage: eval <script>[/red]")
            return
        result = self._run_async(self._client.evaluate(arg.strip()))
        if result.success:
            console.print(f"[green]Result:[/green] {result.data.get('result', '')}")
        else:
            console.print(f"[red]Failed: {result.error}[/red]")

    # ─── Session Management Commands ──────────────────────────────────

    def do_sessions(self, arg):
        """List all sessions: sessions [limit]"""
        limit = int(arg) if arg and arg.isdigit() else 20
        sessions = self._run_async(self._client.list_sessions(limit=limit))
        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return
        table = Table(title=f"Recent Sessions ({len(sessions)})")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Actions", style="blue")
        table.add_column("Created", style="white")
        for s in sessions:
            table.add_row(
                s.id[:12] + "...",
                s.status.value,
                str(s.action_count),
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            )
        console.print(table)

    def do_replay(self, arg):
        """Replay a session: replay <session_id>"""
        if not arg:
            console.print("[red]Usage: replay <session_id>[/red]")
            return
        session_id = arg.strip()
        from computeforge.observability.replay import ReplayEngine

        replay = ReplayEngine(storage=self._client.storage)
        summary = self._run_async(replay.get_session_summary(session_id))
        console.print(
            Panel.fit(
                f"[bold]Session Summary[/bold]\n\n"
                f"Status: {summary['status']}\n"
                f"Actions: {summary['total_actions']} "
                f"(✅ {summary['succeeded']} ❌ {summary['failed']} 🚫 {summary['blocked']})\n"
                f"Success Rate: {summary['success_rate']}%\n"
                f"Duration: {summary['total_duration_ms']:.0f}ms\n"
                f"Avg: {summary['avg_action_duration_ms']:.0f}ms/action",
                border_style="cyan",
            )
        )

    def do_export(self, arg):
        """Export a session: export <session_id> [output_file]"""
        args = shlex.split(arg) if arg else []
        if not args:
            console.print("[red]Usage: export <session_id> [output_file][/red]")
            return
        session_id = args[0]
        output = args[1] if len(args) > 1 else None
        json_str = self._run_async(self._client.export_session(session_id, output_path=output))
        if output:
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(json_str[:500] + "\n...[truncated]")

    # ─── Utility Commands ─────────────────────────────────────────────

    def do_help(self, arg):
        """Show help for commands."""
        if arg:
            super().do_help(arg)
            return
        table = Table(title="ComputeForge Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Usage", style="dim")
        commands = [
            ("start", "Start a new session", "start [url] [--visible]"),
            ("stop", "Stop current session", "stop"),
            ("status", "Show session status", "status"),
            ("navigate", "Navigate to URL", "navigate <url>"),
            ("click", "Click element", "click <selector>"),
            ("type", "Type text", "type <text> [--selector <sel>]"),
            ("ss", "Take screenshot", "ss"),
            ("scroll", "Scroll page", "scroll [delta_y]"),
            ("extract", "Extract text", "extract [selector]"),
            ("eval", "Run JavaScript", "eval <script>"),
            ("sessions", "List sessions", "sessions [limit]"),
            ("replay", "Replay session", "replay <session_id>"),
            ("export", "Export session", "export <session_id> [file]"),
            ("help", "Show this help", "help [command]"),
            ("exit/quit", "Exit shell", "exit"),
        ]
        for cmd_name, desc, usage in commands:
            table.add_row(cmd_name, desc, usage)
        console.print(table)

    def do_exit(self, arg):
        """Exit the interactive shell."""
        if self._client and self._session_active:
            self._run_async(self._client.close())
        self._loop.close()
        console.print("[cyan]Goodbye![/cyan]")
        return True

    def do_quit(self, arg):
        """Exit the interactive shell."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Exit on Ctrl+D."""
        return self.do_exit(arg)

    def emptyline(self) -> bool:
        return False

    def _ensure_session(self) -> bool:
        if not self._client or not self._session_active:
            console.print("[yellow]No active session. Use 'start' first.[/yellow]")
            return False
        return True
