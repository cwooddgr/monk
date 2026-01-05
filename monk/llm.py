"""Anthropic API integration with tool use for music generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from anthropic import Anthropic

from .midi import (
    Note,
    create_midi_file,
    create_chord_progression,
    create_drum_pattern,
    GM_DRUMS,
)
from .project import MonkProject

# System prompt for the music assistant
SYSTEM_PROMPT = """You are Monk, an AI music production assistant. You help users create music by generating MIDI files and modifying Reaper project files.

## Your Capabilities
- Create MIDI files with melodies, chord progressions, drum patterns, and bass lines
- Modify project structure (add tracks, change tempo)
- Understand musical concepts: keys, scales, chords, rhythm, arrangement

## Workflow
1. User describes what they want in natural language
2. You use tools to create/modify MIDI and project files
3. The system automatically renders and plays the audio
4. User provides feedback, and you iterate

## Musical Reference
- Note names: C4 = middle C = MIDI note 60
- Octave numbers: C0=12, C1=24, C2=36, C3=48, C4=60, C5=72, C6=84
- Common chord types: maj, min (m), 7, maj7, m7, dim, aug, sus2, sus4
- Time: Beats are typically quarter notes. 4 beats = 1 bar in 4/4 time.
- GM Drum mapping: kick=36, snare=38, hihat_closed=42, hihat_open=46

## Guidelines
- Start simple, then add complexity based on feedback
- When creating melodies, consider the harmonic context
- Be specific about what you created so the user understands
- Use appropriate velocities (0-127) for dynamics - 80 is moderate, 100 is strong
- Create musically coherent progressions and patterns"""


# Tool definitions
TOOLS = [
    {
        "name": "create_midi",
        "description": "Create a MIDI file with individual notes. Use for melodies, bass lines, or any custom note sequences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name for the MIDI file (without .mid extension)",
                },
                "notes": {
                    "type": "array",
                    "description": "Array of notes to include",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pitch": {
                                "type": "integer",
                                "description": "MIDI note number (0-127). C4=60, D4=62, E4=64, etc.",
                            },
                            "start_beat": {
                                "type": "number",
                                "description": "When the note starts, in beats from the beginning",
                            },
                            "duration_beats": {
                                "type": "number",
                                "description": "How long the note lasts, in beats",
                            },
                            "velocity": {
                                "type": "integer",
                                "description": "Note velocity/volume (0-127). Default 100.",
                            },
                        },
                        "required": ["pitch", "start_beat", "duration_beats"],
                    },
                },
                "track_name": {
                    "type": "string",
                    "description": "Name for the track to add this MIDI to",
                },
            },
            "required": ["filename", "notes", "track_name"],
        },
    },
    {
        "name": "create_chord_progression",
        "description": "Create a MIDI file with a chord progression. Chords are played as block chords.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name for the MIDI file (without .mid extension)",
                },
                "chords": {
                    "type": "array",
                    "description": "Array of chord names like 'Cmaj7', 'Dm7', 'G7', 'Am'",
                    "items": {"type": "string"},
                },
                "beats_per_chord": {
                    "type": "number",
                    "description": "How many beats each chord lasts. Default 4 (one bar).",
                },
                "octave": {
                    "type": "integer",
                    "description": "Base octave for chords (3-5). Default 4.",
                },
                "track_name": {
                    "type": "string",
                    "description": "Name for the track to add this MIDI to",
                },
            },
            "required": ["filename", "chords", "track_name"],
        },
    },
    {
        "name": "create_drum_pattern",
        "description": "Create a MIDI drum pattern. Uses General MIDI drum mapping.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name for the MIDI file (without .mid extension)",
                },
                "pattern": {
                    "type": "object",
                    "description": "Object mapping drum names to arrays of beat positions within one bar. Valid drums: kick, snare, hihat_closed, hihat_open, crash, ride, tom_low, tom_mid, tom_high, clap, rimshot",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
                "bars": {
                    "type": "integer",
                    "description": "Number of bars to generate. Default 4.",
                },
                "track_name": {
                    "type": "string",
                    "description": "Name for the track to add this MIDI to",
                },
            },
            "required": ["filename", "pattern", "track_name"],
        },
    },
    {
        "name": "set_tempo",
        "description": "Change the project tempo (BPM).",
        "input_schema": {
            "type": "object",
            "properties": {
                "bpm": {
                    "type": "number",
                    "description": "Tempo in beats per minute (40-240)",
                },
            },
            "required": ["bpm"],
        },
    },
    {
        "name": "add_track",
        "description": "Add a new empty track to the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new track",
                },
            },
            "required": ["name"],
        },
    },
]


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool: str
    summary: str
    made_changes: bool
    error: str | None = None


class MusicLLM:
    """LLM integration for music generation."""

    def __init__(self, project: MonkProject):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.project = project
        self.messages: list[dict] = []

        # Load conversation history
        for msg in project.conversation:
            self.messages.append({"role": msg.role, "content": msg.content})

    def chat(self, user_message: str) -> Generator[str | ToolResult, None, None]:
        """Send a message and yield response chunks and tool results.

        Handles the tool use loop internally, continuing until the model
        produces a final text response.
        """
        # Add context to user message
        context = self.project.get_context()
        augmented_message = f"[Current Project State]\n{context}\n\n[User Request]\n{user_message}"

        self.messages.append({"role": "user", "content": augmented_message})

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
            ) as stream:
                response = stream.get_final_message()

            # Collect text and tool use from response
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                    yield block.text
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": response.content})

            # If no tool use, we're done
            if not tool_uses:
                break

            # Execute tools and collect results
            tool_results = []
            for tool_use in tool_uses:
                result = self._execute_tool(tool_use.name, tool_use.input)
                yield result

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result.summary if not result.error else f"Error: {result.error}",
                    }
                )

            # Add tool results to continue the conversation
            self.messages.append({"role": "user", "content": tool_results})

    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        try:
            if name == "create_midi":
                return self._create_midi(input_data)
            elif name == "create_chord_progression":
                return self._create_chord_progression(input_data)
            elif name == "create_drum_pattern":
                return self._create_drum_pattern(input_data)
            elif name == "set_tempo":
                return self._set_tempo(input_data)
            elif name == "add_track":
                return self._add_track(input_data)
            else:
                return ToolResult(
                    tool=name,
                    summary=f"Unknown tool: {name}",
                    made_changes=False,
                    error=f"Unknown tool: {name}",
                )
        except Exception as e:
            return ToolResult(
                tool=name,
                summary=str(e),
                made_changes=False,
                error=str(e),
            )

    def _create_midi(self, input_data: dict) -> ToolResult:
        """Create a MIDI file with notes."""
        filename = input_data["filename"]
        track_name = input_data["track_name"]
        notes_data = input_data["notes"]

        notes = [
            Note(
                pitch=n["pitch"],
                start_beat=n["start_beat"],
                duration_beats=n["duration_beats"],
                velocity=n.get("velocity", 100),
            )
            for n in notes_data
        ]

        midi_path = self.project.midi_dir / f"{filename}.mid"
        create_midi_file(midi_path, notes, tempo_bpm=int(self.project.rpp.tempo))

        # Find or create track
        track = self._get_or_create_track(track_name)
        self.project.rpp.add_midi_item(track.index, midi_path)
        self.project.save()

        return ToolResult(
            tool="create_midi",
            summary=f"Created {filename}.mid with {len(notes)} notes on '{track_name}'",
            made_changes=True,
        )

    def _create_chord_progression(self, input_data: dict) -> ToolResult:
        """Create a chord progression MIDI file."""
        filename = input_data["filename"]
        track_name = input_data["track_name"]
        chords = input_data["chords"]
        beats_per_chord = input_data.get("beats_per_chord", 4.0)
        octave = input_data.get("octave", 4)

        midi_path = self.project.midi_dir / f"{filename}.mid"
        create_chord_progression(
            midi_path,
            chords,
            beats_per_chord=beats_per_chord,
            tempo_bpm=int(self.project.rpp.tempo),
            octave=octave,
        )

        track = self._get_or_create_track(track_name)
        self.project.rpp.add_midi_item(track.index, midi_path)
        self.project.save()

        chord_str = " → ".join(chords)
        return ToolResult(
            tool="create_chord_progression",
            summary=f"Created {filename}.mid: {chord_str} on '{track_name}'",
            made_changes=True,
        )

    def _create_drum_pattern(self, input_data: dict) -> ToolResult:
        """Create a drum pattern MIDI file."""
        filename = input_data["filename"]
        track_name = input_data["track_name"]
        pattern = input_data["pattern"]
        bars = input_data.get("bars", 4)

        # Validate drum names
        for drum in pattern.keys():
            if drum not in GM_DRUMS:
                return ToolResult(
                    tool="create_drum_pattern",
                    summary=f"Unknown drum: {drum}",
                    made_changes=False,
                    error=f"Unknown drum: {drum}. Valid: {list(GM_DRUMS.keys())}",
                )

        midi_path = self.project.midi_dir / f"{filename}.mid"
        create_drum_pattern(
            midi_path,
            pattern,
            bars=bars,
            tempo_bpm=int(self.project.rpp.tempo),
        )

        track = self._get_or_create_track(track_name)
        self.project.rpp.add_midi_item(track.index, midi_path)
        self.project.save()

        drum_list = ", ".join(pattern.keys())
        return ToolResult(
            tool="create_drum_pattern",
            summary=f"Created {filename}.mid: {drum_list} ({bars} bars) on '{track_name}'",
            made_changes=True,
        )

    def _set_tempo(self, input_data: dict) -> ToolResult:
        """Set project tempo."""
        bpm = input_data["bpm"]

        if not 40 <= bpm <= 240:
            return ToolResult(
                tool="set_tempo",
                summary=f"Invalid tempo: {bpm}",
                made_changes=False,
                error="Tempo must be between 40 and 240 BPM",
            )

        self.project.rpp.set_tempo(bpm)
        self.project.save()

        return ToolResult(
            tool="set_tempo",
            summary=f"Set tempo to {bpm} BPM",
            made_changes=True,
        )

    def _add_track(self, input_data: dict) -> ToolResult:
        """Add a new track."""
        name = input_data["name"]

        self.project.rpp.add_track(name)
        self.project.save()

        return ToolResult(
            tool="add_track",
            summary=f"Added track '{name}'",
            made_changes=True,
        )

    def _get_or_create_track(self, name: str):
        """Get an existing track or create a new one."""
        for track in self.project.rpp.tracks:
            if track.name == name:
                return track
        return self.project.rpp.add_track(name)
