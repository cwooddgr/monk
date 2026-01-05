# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monk Music is an LLM-driven CLI for music production. It follows the Claude Code paradigm: users interact via natural language, and the tool modifies project files directly. Reaper DAW serves as a headless "compiler" for rendering audio.

**Core analogy:** Monk is to Reaper what Claude Code is to Xcode.

## Build & Run Commands

```bash
# Install in development mode
pip install -e .

# Run CLI
monk --help
monk init <project-name>    # Create new project
monk chat                   # Start interactive session (from project directory)
monk chat -p /path/to/project.rpp  # Specify project path
```

**Requirements:**
- Python 3.9+
- Reaper DAW installed
- `ANTHROPIC_API_KEY` environment variable set for AI features
- ffplay (from ffmpeg) or mpv for audio preview

## Architecture

```
User (natural language) → Monk CLI → LLM (Claude) → Project Files → Reaper (headless render)
```

Key design decisions:
- **No live DAW connection** - Edit .rpp files directly, call Reaper only for rendering
- **File-based workflow** - All state lives in .rpp, MIDI, and audio asset files
- **Human-in-the-loop** - User provides feedback, LLM iterates

## Code Structure

```
monk/
├── cli.py       # Click-based CLI entry points (init, chat commands)
├── chat.py      # Conversation loop, command handling, auto-render
├── llm.py       # Anthropic API integration, tool definitions and execution
├── project.py   # MonkProject class - manages project state and history
├── rpp.py       # ReaperProject class - parse/modify .rpp files
├── midi.py      # MIDI generation (notes, chords, drums) using mido
├── render.py    # Headless Reaper rendering pipeline
├── preview.py   # Audio playback (ffplay/mpv/afplay)
└── templates/   # Starter .rpp templates
```

## LLM Tools

The LLM has access to these tools (defined in `llm.py`):
- `create_midi` - Create MIDI with individual notes
- `create_chord_progression` - Generate chord progression MIDI
- `create_drum_pattern` - Create drum patterns using GM mapping
- `set_tempo` - Change project BPM
- `add_track` - Add new track to project

## File Formats

- **.rpp** (Reaper Project) - Text-based hierarchical format. See: https://wiki.cockos.com/wiki/index.php/RPP_File_Format
- **.mid** (MIDI) - Standard MIDI format, generated via `mido` library

## Key Classes

- `MonkProject` (`project.py`) - Main project manager, handles saving, rendering, conversation history
- `ReaperProject` (`rpp.py`) - Parses and modifies .rpp files, adds tracks and MIDI items
- `MusicLLM` (`llm.py`) - Anthropic client wrapper with streaming and tool use loop
