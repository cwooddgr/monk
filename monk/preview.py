"""Audio preview playback."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


class PreviewError(Exception):
    """Raised when audio preview fails."""

    pass


def find_player() -> tuple[str, list[str]]:
    """Find an available audio player.

    Returns:
        Tuple of (player_name, base_args) for the player.

    Raises:
        PreviewError: If no suitable player is found.
    """
    # Try ffplay first (comes with ffmpeg)
    if shutil.which("ffplay"):
        return ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"])

    # Try mpv
    if shutil.which("mpv"):
        return ("mpv", ["mpv", "--no-video", "--really-quiet"])

    # Try afplay on macOS
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ("afplay", ["afplay"])

    raise PreviewError(
        "No audio player found. Please install ffmpeg (for ffplay) or mpv."
    )


def play_audio(audio_path: Path, blocking: bool = True) -> subprocess.Popen | None:
    """Play an audio file.

    Args:
        audio_path: Path to the audio file to play.
        blocking: If True, wait for playback to complete. If False,
            return immediately with the subprocess handle.

    Returns:
        If blocking=False, returns the subprocess.Popen object.
        Otherwise returns None.

    Raises:
        PreviewError: If playback fails or no player is available.
        FileNotFoundError: If the audio file doesn't exist.
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    player_name, args = find_player()
    args = args + [str(audio_path)]

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if blocking:
            proc.wait()
            return None
        return proc

    except subprocess.SubprocessError as e:
        raise PreviewError(f"Failed to play audio with {player_name}: {e}") from e


def stop_playback(proc: subprocess.Popen) -> None:
    """Stop audio playback.

    Args:
        proc: The subprocess handle returned by play_audio(blocking=False).
    """
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
