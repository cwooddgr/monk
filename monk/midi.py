"""MIDI file generation and manipulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack

# Standard ticks per beat
TICKS_PER_BEAT = 480

# Note name to MIDI number mapping (C4 = 60 = middle C)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Chord quality intervals (semitones from root)
CHORD_INTERVALS = {
    "": [0, 4, 7],  # major
    "maj": [0, 4, 7],
    "m": [0, 3, 7],  # minor
    "min": [0, 3, 7],
    "7": [0, 4, 7, 10],  # dominant 7
    "maj7": [0, 4, 7, 11],  # major 7
    "m7": [0, 3, 7, 10],  # minor 7
    "min7": [0, 3, 7, 10],
    "dim": [0, 3, 6],  # diminished
    "dim7": [0, 3, 6, 9],
    "aug": [0, 4, 8],  # augmented
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 4, 7, 14],
    "9": [0, 4, 7, 10, 14],  # dominant 9
}

# GM drum mapping
GM_DRUMS = {
    "kick": 36,
    "snare": 38,
    "rimshot": 37,
    "clap": 39,
    "hihat_closed": 42,
    "hihat_open": 46,
    "hihat_pedal": 44,
    "tom_low": 45,
    "tom_mid": 47,
    "tom_high": 50,
    "crash": 49,
    "ride": 51,
    "ride_bell": 53,
}


@dataclass
class Note:
    """A single MIDI note."""

    pitch: int  # MIDI note number (0-127)
    start_beat: float  # Position in beats from start
    duration_beats: float  # Duration in beats
    velocity: int = 100  # Note velocity (0-127)

    def start_ticks(self, ticks_per_beat: int = TICKS_PER_BEAT) -> int:
        """Get start position in ticks."""
        return int(self.start_beat * ticks_per_beat)

    def duration_ticks(self, ticks_per_beat: int = TICKS_PER_BEAT) -> int:
        """Get duration in ticks."""
        return int(self.duration_beats * ticks_per_beat)


def note_name_to_midi(name: str) -> int:
    """Convert a note name to MIDI number.

    Args:
        name: Note name like "C4", "F#3", "Bb5".

    Returns:
        MIDI note number (0-127).

    Raises:
        ValueError: If the note name is invalid.
    """
    name = name.strip()

    # Handle flats by converting to sharps
    name = name.replace("b", "")
    if "b" in name:
        # Find the note and lower it
        pass

    # Parse note and octave
    if len(name) < 2:
        raise ValueError(f"Invalid note name: {name}")

    if name[1] == "#":
        note_part = name[:2]
        octave_part = name[2:]
    else:
        note_part = name[0]
        octave_part = name[1:]

    # Handle flats
    if "b" in octave_part:
        octave_part = octave_part.replace("b", "")
        note_idx = NOTE_NAMES.index(note_part.upper())
        note_idx = (note_idx - 1) % 12
        note_part = NOTE_NAMES[note_idx]

    try:
        note_idx = NOTE_NAMES.index(note_part.upper())
        octave = int(octave_part)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid note name: {name}") from e

    midi_num = (octave + 1) * 12 + note_idx

    if not 0 <= midi_num <= 127:
        raise ValueError(f"Note {name} is out of MIDI range (0-127)")

    return midi_num


def midi_to_note_name(midi_num: int) -> str:
    """Convert a MIDI number to note name.

    Args:
        midi_num: MIDI note number (0-127).

    Returns:
        Note name like "C4".
    """
    octave = (midi_num // 12) - 1
    note_idx = midi_num % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"


def parse_chord(chord_name: str, octave: int = 4) -> list[int]:
    """Parse a chord name into MIDI note numbers.

    Args:
        chord_name: Chord name like "Cmaj7", "Dm", "F#7".
        octave: Base octave for the root note.

    Returns:
        List of MIDI note numbers for the chord.

    Raises:
        ValueError: If the chord name is invalid.
    """
    chord_name = chord_name.strip()

    # Extract root note
    if len(chord_name) >= 2 and chord_name[1] in "#b":
        root = chord_name[:2]
        quality = chord_name[2:]
    else:
        root = chord_name[0]
        quality = chord_name[1:]

    # Get root MIDI number
    root_midi = note_name_to_midi(f"{root}{octave}")

    # Get chord intervals
    if quality not in CHORD_INTERVALS:
        raise ValueError(f"Unknown chord quality: {quality} in {chord_name}")

    intervals = CHORD_INTERVALS[quality]

    return [root_midi + interval for interval in intervals]


def create_midi_file(
    output_path: str | Path,
    notes: list[Note],
    tempo_bpm: int = 120,
    ticks_per_beat: int = TICKS_PER_BEAT,
) -> None:
    """Create a MIDI file from a list of notes.

    Args:
        output_path: Path to write the MIDI file.
        notes: List of Note objects.
        tempo_bpm: Tempo in beats per minute.
        ticks_per_beat: Resolution in ticks per beat.
    """
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)

    # Set tempo
    tempo = mido.bpm2tempo(tempo_bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    # Convert notes to events with absolute times
    events: list[tuple[int, str, int, int]] = []
    for note in notes:
        start = note.start_ticks(ticks_per_beat)
        end = start + note.duration_ticks(ticks_per_beat)
        events.append((start, "note_on", note.pitch, note.velocity))
        events.append((end, "note_off", note.pitch, 0))

    # Sort by time
    events.sort(key=lambda e: (e[0], e[1] == "note_on"))

    # Convert to delta times
    current_time = 0
    for abs_time, msg_type, pitch, velocity in events:
        delta = abs_time - current_time
        track.append(Message(msg_type, note=pitch, velocity=velocity, time=delta))
        current_time = abs_time

    # End of track
    track.append(MetaMessage("end_of_track", time=0))

    mid.save(str(output_path))


def create_chord_progression(
    output_path: str | Path,
    chords: list[str],
    beats_per_chord: float = 4.0,
    tempo_bpm: int = 120,
    velocity: int = 80,
    octave: int = 4,
) -> None:
    """Create a MIDI file with a chord progression.

    Args:
        output_path: Path to write the MIDI file.
        chords: List of chord names like ["Dm7", "G7", "Cmaj7", "Am7"].
        beats_per_chord: Duration of each chord in beats.
        tempo_bpm: Tempo in beats per minute.
        velocity: Note velocity.
        octave: Base octave for chords.
    """
    notes: list[Note] = []

    for i, chord_name in enumerate(chords):
        chord_notes = parse_chord(chord_name, octave=octave)
        start_beat = i * beats_per_chord

        for pitch in chord_notes:
            notes.append(
                Note(
                    pitch=pitch,
                    start_beat=start_beat,
                    duration_beats=beats_per_chord - 0.1,  # slight gap
                    velocity=velocity,
                )
            )

    create_midi_file(output_path, notes, tempo_bpm=tempo_bpm)


def create_drum_pattern(
    output_path: str | Path,
    pattern: dict[str, list[float]],
    bars: int = 4,
    tempo_bpm: int = 120,
    velocity: int = 100,
) -> None:
    """Create a MIDI drum pattern.

    Args:
        output_path: Path to write the MIDI file.
        pattern: Dict mapping drum names to beat positions within one bar.
            Example: {"kick": [0, 2], "snare": [1, 3], "hihat_closed": [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]}
        bars: Number of bars to generate.
        tempo_bpm: Tempo in beats per minute.
        velocity: Note velocity.
    """
    notes: list[Note] = []

    for drum_name, beats in pattern.items():
        if drum_name not in GM_DRUMS:
            raise ValueError(f"Unknown drum: {drum_name}. Valid: {list(GM_DRUMS.keys())}")

        pitch = GM_DRUMS[drum_name]

        for bar in range(bars):
            bar_offset = bar * 4  # 4 beats per bar
            for beat in beats:
                notes.append(
                    Note(
                        pitch=pitch,
                        start_beat=bar_offset + beat,
                        duration_beats=0.1,  # short hit
                        velocity=velocity,
                    )
                )

    create_midi_file(output_path, notes, tempo_bpm=tempo_bpm)
