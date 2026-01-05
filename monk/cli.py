"""Monk Music CLI entry points."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
from rich.console import Console

from . import __version__

console = Console()

# Path to templates directory (inside the monk package)
TEMPLATES_DIR = Path(__file__).parent / "templates"


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Monk Music - LLM-driven music production."""
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--template",
    "-t",
    default="minimal",
    help="Template to use (default: minimal)",
)
def init(name: str, template: str) -> None:
    """Create a new Monk project."""
    project_dir = Path.cwd() / name

    if project_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{name}' already exists")
        raise SystemExit(1)

    # Find template
    template_path = TEMPLATES_DIR / f"{template}.rpp"
    if not template_path.exists():
        console.print(f"[red]Error:[/red] Template '{template}' not found")
        raise SystemExit(1)

    # Create project structure
    project_dir.mkdir(parents=True)
    (project_dir / "midi").mkdir()
    (project_dir / "audio").mkdir()
    (project_dir / "renders").mkdir()

    # Copy template
    project_rpp = project_dir / f"{name}.rpp"
    shutil.copy(template_path, project_rpp)

    # Update render path in project
    from .rpp import ReaperProject

    project = ReaperProject.load(project_rpp)
    project.set_render_file(f"renders/{name}")
    project.save()

    console.print(f"[green]Created project at[/green] {project_dir}/")
    console.print(f"  Project file: {name}.rpp")
    console.print(f"  MIDI files:   midi/")
    console.print(f"  Renders:      renders/")
    console.print()
    console.print(f"Run [cyan]cd {name} && monk chat[/cyan] to start creating music.")


@cli.command()
@click.option(
    "--project",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    help="Path to project directory or .rpp file",
)
def chat(project: Path | None) -> None:
    """Start an interactive music creation session."""
    from .chat import run_chat

    # Find project
    if project is None:
        # Look for .rpp file in current directory
        rpp_files = list(Path.cwd().glob("*.rpp"))
        if not rpp_files:
            console.print("[red]Error:[/red] No .rpp file found in current directory")
            console.print("Run [cyan]monk init <name>[/cyan] to create a new project,")
            console.print("or use [cyan]--project[/cyan] to specify a project path.")
            raise SystemExit(1)
        if len(rpp_files) > 1:
            console.print("[red]Error:[/red] Multiple .rpp files found. Please specify one with --project")
            raise SystemExit(1)
        project = rpp_files[0]
    elif project.is_dir():
        # Look for .rpp file in directory
        rpp_files = list(project.glob("*.rpp"))
        if not rpp_files:
            console.print(f"[red]Error:[/red] No .rpp file found in {project}")
            raise SystemExit(1)
        project = rpp_files[0]

    run_chat(project)


@cli.command()
def version() -> None:
    """Show version information."""
    console.print(f"Monk Music v{__version__}")


if __name__ == "__main__":
    cli()
