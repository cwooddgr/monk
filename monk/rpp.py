"""Reaper project file (.rpp) parsing and manipulation."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MidiItem:
    """A MIDI item in a track."""

    path: Path
    position: float  # Position in seconds
    length: float  # Length in seconds


@dataclass
class Track:
    """A track in the project."""

    name: str
    index: int
    guid: str = field(default_factory=lambda: str(uuid.uuid4()))
    midi_items: list[MidiItem] = field(default_factory=list)


class ReaperProject:
    """Represents a Reaper project file."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.tempo: float = 120.0
        self.time_signature: tuple[int, int] = (4, 4)
        self.sample_rate: int = 44100
        self.render_file: str = "render"
        self.tracks: list[Track] = []
        self._raw_lines: list[str] = []

        if path and path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        """Load a project from an RPP file."""
        self.path = path

        with open(path) as f:
            self._raw_lines = f.readlines()

        # Parse tempo
        for line in self._raw_lines:
            line = line.strip()
            if line.startswith("TEMPO "):
                parts = line.split()
                if len(parts) >= 2:
                    self.tempo = float(parts[1])
            elif line.startswith("SAMPLERATE "):
                parts = line.split()
                if len(parts) >= 2:
                    self.sample_rate = int(parts[1])
            elif line.startswith("RENDER_FILE "):
                match = re.search(r'"([^"]*)"', line)
                if match:
                    self.render_file = match.group(1)

        # Parse tracks
        self.tracks = []
        in_track = False
        current_track: Track | None = None
        track_idx = 0

        for line in self._raw_lines:
            stripped = line.strip()

            if stripped.startswith("<TRACK"):
                in_track = True
                guid_match = re.search(r"\{([^}]+)\}", stripped)
                guid = guid_match.group(1) if guid_match else str(uuid.uuid4())
                current_track = Track(name=f"Track {track_idx + 1}", index=track_idx, guid=guid)
                track_idx += 1

            elif in_track and stripped.startswith("NAME "):
                match = re.search(r'"([^"]*)"', stripped)
                if match and current_track:
                    current_track.name = match.group(1)

            elif in_track and stripped == ">":
                if current_track:
                    self.tracks.append(current_track)
                current_track = None
                in_track = False

    @classmethod
    def load(cls, path: str | Path) -> "ReaperProject":
        """Load a project from an RPP file."""
        return cls(Path(path))

    def save(self, path: str | Path | None = None) -> None:
        """Save the project to an RPP file."""
        save_path = Path(path) if path else self.path
        if not save_path:
            raise ValueError("No path specified for saving")

        # Rebuild the file content
        lines = self._rebuild_content()

        with open(save_path, "w") as f:
            f.writelines(lines)

        self.path = save_path

    def _rebuild_content(self) -> list[str]:
        """Rebuild the RPP file content with modifications.

        For simplicity and reliability, we always generate a fresh project
        file based on the current state rather than patching the original.
        """
        return self._generate_new_project()

    def _generate_new_project(self) -> list[str]:
        """Generate a complete new project file."""
        lines = [
            '<REAPER_PROJECT 0.1 "7.0" 1704067200\n',
            "  RIPPLE 0\n",
            "  GROUPOVERRIDE 0 0 0\n",
            "  AUTOXFADE 1\n",
            f"  SAMPLERATE {self.sample_rate} 0 0\n",
            f"  TEMPO {self.tempo} 4 4\n",
            "  PLAYRATE 1 0 0.25 4\n",
            "  MASTERTRACKHEIGHT 0 0\n",
            "  MASTERTRACKVIEW 0 0.6667 0.5 0.5 -1 -1 -1 0 0 0 -1 -1 0\n",
            "  MASTERHWOUT 0 0 1 0 0 0 0 -1\n",
            "  MASTER_NCH 2 2\n",
            "  MASTER_VOLUME 1 0 -1 -1 1\n",
            "  MASTER_FX 1\n",
            "  MASTER_SEL 0\n",
            f'  RENDER_FILE "{self.render_file}"\n',
            '  RENDER_PATTERN ""\n',
            "  RENDER_FMT 0 2 0\n",
            "  RENDER_1X 0\n",
            "  RENDER_RANGE 1 0 0 18 1000\n",
            "  RENDER_RESAMPLE 3 0 1\n",
            "  RENDER_ADDTOPROJ 0\n",
            "  RENDER_STEMS 0\n",
            "  RENDER_DITHER 0\n",
        ]

        # Add tracks
        for track in self.tracks:
            lines.extend(self._generate_track(track))

        # Close the project
        lines.append(">\n")
        return lines

    def _generate_track(self, track: Track, add_synth: bool = True) -> list[str]:
        """Generate RPP content for a track."""
        guid = f"{{{track.guid}}}"
        lines = [
            f"  <TRACK {guid}\n",
            f'    NAME "{track.name}"\n',
            "    PEAKCOL 16576\n",
            "    BEAT -1\n",
            "    AUTOMODE 0\n",
            "    VOLPAN 1 0 -1 -1 1\n",
            "    REC 0 0 1 0 0 0 0 0\n",
            "    VU 2\n",
            "    NCHAN 2\n",
            "    FX 1\n",
            f"    TRACKID {guid}\n",
            "    PERF 0\n",
            "    MIDIOUT -1\n",
            "    MAINSEND 1 0\n",
        ]

        # Add ReaSynth if track has MIDI items
        if add_synth and track.midi_items:
            lines.extend(self._generate_reasynth_fx())

        # Add MIDI items
        for item in track.midi_items:
            lines.extend(self._generate_midi_item(item))

        lines.append("  >\n")
        return lines

    def _generate_reasynth_fx(self) -> list[str]:
        """Generate an FX chain with ReaSynth for MIDI playback."""
        # ReaSynth preset data (simple saw wave)
        # This is a minimal ReaSynth configuration that produces audible sound
        return [
            "    <FXCHAIN\n",
            "      SHOW 0\n",
            "      LASTSEL 0\n",
            "      DOCKED 0\n",
            "      BYPASS 0 0 0\n",
            "      <VST \"VSTi: ReaSynth (Cockos)\" reasynth.vst.dylib 0 \"\" 1919251321<5653546872736E7265617379>\n",
            "        eXNlcu5e7f4CAAAAAQAAAAAAAAACAAAAAAAAAAIAAAABAAAAAAAAAAIAAAAAAAAAPAAAAAAAAAAAABA\n",
            "        AAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
            "        AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
            "        AAAQAAAA\n",
            "      >\n",
            "      FLOATPOS 0 0 0 0\n",
            "      FXID {" + str(uuid.uuid4()) + "}\n",
            "      WAK 0 0\n",
            "    >\n",
        ]

    def _generate_midi_item(self, item: MidiItem) -> list[str]:
        """Generate RPP content for a MIDI item."""
        item_guid = str(uuid.uuid4())
        # Use relative path if possible
        midi_path = str(item.path)

        return [
            "    <ITEM\n",
            f"      POSITION {item.position}\n",
            "      SNAPOFFS 0\n",
            f"      LENGTH {item.length}\n",
            "      LOOP 1\n",
            "      ALLTAKES 0\n",
            "      FADEIN 1 0.01 0 1 0 0 0\n",
            "      FADEOUT 1 0.01 0 1 0 0 0\n",
            "      MUTE 0 0\n",
            "      SEL 0\n",
            f"      IGUID {{{item_guid}}}\n",
            "      IID 1\n",
            f'      NAME "{item.path.stem}"\n',
            "      VOLPAN 1 0 1 -1\n",
            "      PLAYRATE 1 1 0 -1 0 0.0025\n",
            "      CHANMODE 0\n",
            "      GUID {" + str(uuid.uuid4()) + "}\n",
            "      <SOURCE MIDI\n",
            "        HASDATA 1 960 QN\n",
            f'        FILE "{midi_path}"\n',
            "      >\n",
            "    >\n",
        ]

    def set_tempo(self, bpm: float) -> None:
        """Set the project tempo."""
        self.tempo = bpm

    def set_render_file(self, filename: str) -> None:
        """Set the render output filename (without extension)."""
        self.render_file = filename

    def add_track(self, name: str) -> Track:
        """Add a new track to the project."""
        track = Track(name=name, index=len(self.tracks))
        self.tracks.append(track)
        return track

    def add_midi_item(
        self,
        track_index: int,
        midi_path: Path,
        position: float = 0.0,
        length: float | None = None,
    ) -> None:
        """Add a MIDI item to a track.

        Args:
            track_index: Index of the track to add to.
            midi_path: Path to the MIDI file.
            position: Position in seconds.
            length: Length in seconds (auto-calculated if None).
        """
        if track_index >= len(self.tracks):
            raise IndexError(f"Track index {track_index} out of range")

        # Calculate length from MIDI file if not specified
        if length is None:
            import mido

            mid = mido.MidiFile(str(midi_path))
            length = mid.length

        item = MidiItem(path=midi_path, position=position, length=length)
        self.tracks[track_index].midi_items.append(item)

    def get_context_string(self) -> str:
        """Get a string representation of the project for LLM context."""
        lines = [
            f"Tempo: {self.tempo} BPM",
            f"Time Signature: {self.time_signature[0]}/{self.time_signature[1]}",
            f"Tracks: {len(self.tracks)}",
        ]

        for track in self.tracks:
            lines.append(f"  - {track.name}")
            for item in track.midi_items:
                lines.append(f"      MIDI: {item.path.name} at {item.position}s")

        return "\n".join(lines)
