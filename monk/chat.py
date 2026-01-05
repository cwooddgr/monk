"""Interactive chat session for music creation."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import __version__
from .llm import MusicLLM, ToolResult
from .preview import play_audio, PreviewError
from .project import MonkProject
from .render import RenderError, ReaperNotFoundError

console = Console()


def run_chat(rpp_path: Path) -> None:
    """Run an interactive chat session."""
    console.print(Panel(f"[bold]Monk Music[/bold] v{__version__}", expand=False))

    # Load project
    try:
        project = MonkProject.load(rpp_path)
    except Exception as e:
        console.print(f"[red]Error loading project:[/red] {e}")
        raise SystemExit(1)

    console.print(f"Project: [cyan]{rpp_path.stem}[/cyan]")
    console.print(f"Tempo: {project.rpp.tempo} BPM")
    console.print(f"Tracks: {len(project.rpp.tracks)}")
    console.print()
    console.print("Type your music ideas, or use commands:")
    console.print("  [dim]/render[/dim]  - Render and play current project")
    console.print("  [dim]/status[/dim]  - Show project status")
    console.print("  [dim]/quit[/dim]    - Exit")
    console.print()

    # Initialize LLM
    try:
        llm = MusicLLM(project)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("Set the ANTHROPIC_API_KEY environment variable to enable AI features.")
        console.print("You can still use /render and /status commands.")
        llm = None

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.startswith("/"):
            handle_command(user_input, project)
            continue

        # Handle natural language with LLM
        if llm is None:
            console.print("[yellow]AI not available.[/yellow] Use /render to render the project.")
            continue

        project.add_message("user", user_input)

        console.print()
        console.print("[bold blue]Monk:[/bold blue] ", end="")

        try:
            response_text = ""
            tool_results: list[ToolResult] = []

            for chunk in llm.chat(user_input):
                if isinstance(chunk, str):
                    console.print(chunk, end="")
                    response_text += chunk
                elif isinstance(chunk, ToolResult):
                    tool_results.append(chunk)
                    console.print(f"\n[dim]  → {chunk.tool}: {chunk.summary}[/dim]", end="")

            console.print()  # End the response line

            if response_text:
                project.add_message("assistant", response_text)

            # Auto-render if we made changes
            if any(r.made_changes for r in tool_results):
                console.print()
                auto_render(project)

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")

        console.print()


def handle_command(command: str, project: MonkProject) -> None:
    """Handle a slash command."""
    cmd = command.lower().split()[0]

    if cmd in ("/quit", "/exit", "/q"):
        console.print("Goodbye!")
        raise SystemExit(0)

    elif cmd == "/render":
        render_and_play(project)

    elif cmd == "/status":
        show_status(project)

    elif cmd == "/help":
        console.print("Commands:")
        console.print("  /render  - Render and play current project")
        console.print("  /status  - Show project status")
        console.print("  /quit    - Exit")

    else:
        console.print(f"[yellow]Unknown command:[/yellow] {cmd}")


def show_status(project: MonkProject) -> None:
    """Show project status."""
    console.print(Panel(project.get_context(), title="Project Status", expand=False))


def render_and_play(project: MonkProject) -> None:
    """Render the project and play the result."""
    console.print("[dim]Rendering...[/dim]")

    try:
        project.save()
        audio_path = project.render_preview()
        console.print(f"[green]Rendered:[/green] {audio_path}")

        console.print("[dim]Playing... (Ctrl+C to stop)[/dim]")
        try:
            play_audio(audio_path)
        except PreviewError as e:
            console.print(f"[yellow]Playback error:[/yellow] {e}")
            console.print(f"Audio saved to: {audio_path}")

    except ReaperNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except RenderError as e:
        console.print(f"[red]Render failed:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def auto_render(project: MonkProject) -> None:
    """Automatically render after changes."""
    try:
        render_and_play(project)
    except Exception as e:
        console.print(f"[dim]Auto-render skipped: {e}[/dim]")
