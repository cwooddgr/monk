"""Headless Reaper rendering pipeline."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class ReaperNotFoundError(Exception):
    """Raised when Reaper executable cannot be found."""

    pass


class RenderError(Exception):
    """Raised when rendering fails."""

    pass


def find_reaper() -> Path:
    """Locate the Reaper executable on the system.

    Returns:
        Path to the Reaper executable.

    Raises:
        ReaperNotFoundError: If Reaper cannot be found.
    """
    # Check environment variable first
    env_path = os.environ.get("REAPER_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # macOS paths
    mac_paths = [
        Path("/Applications/REAPER.app/Contents/MacOS/REAPER"),
        Path.home() / "Applications/REAPER.app/Contents/MacOS/REAPER",
    ]

    for path in mac_paths:
        if path.exists():
            return path

    # Try PATH
    reaper_in_path = shutil.which("reaper") or shutil.which("REAPER")
    if reaper_in_path:
        return Path(reaper_in_path)

    raise ReaperNotFoundError(
        "Reaper not found. Please install from https://www.reaper.fm/ "
        "or set REAPER_PATH environment variable."
    )


def get_render_path(rpp_path: Path) -> Path:
    """Extract the render output path from an RPP file.

    Looks for RENDER_FILE in the project. If relative, resolves
    relative to the project directory.

    Args:
        rpp_path: Path to the Reaper project file.

    Returns:
        Path where rendered audio will be written.
    """
    project_dir = rpp_path.parent
    render_file = "render"  # default

    with open(rpp_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("RENDER_FILE"):
                # Format: RENDER_FILE "filename"
                parts = line.split('"')
                if len(parts) >= 2 and parts[1]:
                    render_file = parts[1]
                break

    render_path = Path(render_file)
    if not render_path.is_absolute():
        render_path = project_dir / render_path

    # Reaper typically adds .wav extension
    if not render_path.suffix:
        render_path = render_path.with_suffix(".wav")

    return render_path


def render_project(rpp_path: Path, timeout: int = 60) -> Path:
    """Render a Reaper project headlessly.

    Args:
        rpp_path: Path to the Reaper project file.
        timeout: Maximum time to wait for render in seconds.

    Returns:
        Path to the rendered audio file.

    Raises:
        ReaperNotFoundError: If Reaper cannot be found.
        RenderError: If rendering fails.
        FileNotFoundError: If the project file doesn't exist.
    """
    rpp_path = Path(rpp_path).resolve()

    if not rpp_path.exists():
        raise FileNotFoundError(f"Project file not found: {rpp_path}")

    reaper = find_reaper()
    output_path = get_render_path(rpp_path)

    # Remove existing output to detect if render succeeds
    if output_path.exists():
        output_path.unlink()

    try:
        result = subprocess.run(
            [str(reaper), "-renderproject", str(rpp_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RenderError(f"Render timed out after {timeout} seconds") from e

    # Check if output was created
    if not output_path.exists():
        error_msg = result.stderr or result.stdout or "Unknown error"
        raise RenderError(f"Render failed, no output created: {error_msg}")

    return output_path
