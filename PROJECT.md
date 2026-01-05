# Monk Music

## Overview

Monk Music is a command-line tool for music production that follows the same paradigm as Claude Code. Instead of interacting with a DAW (Digital Audio Workstation) through a graphical interface, you describe what you want in natural language, and Monk modifies the underlying project files directly.

**The core analogy:** Monk is to Reaper what Claude Code is to Xcode.

- You never touch the source files yourself
- The CLI is your only interface
- The DAW (Reaper) serves purely as a "compiler" to render audio
- The LLM handles all the complexity of understanding music and manipulating files

**Name origin:** Named after Thelonious Monk, the jazz pianist and composer who bent harmony and rhythm in innovative ways. Also evokes the monastic discipline of sitting with a tool, patiently crafting and iterating—devotional practice applied to creation. Parallel to Claude (Claude Code) being named after Claude Shannon.

*Note: "Monk Music" has an awkward k-m consonant transition. "Miles Music" (after Miles Davis) or just "Monk" as a standalone name are alternatives under consideration.*

---

## Architecture

### Stack

```
┌─────────────────────────────────────────┐
│  You (natural language)                 │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Monk CLI                               │
│  - Conversational interface             │
│  - Maintains project context            │
│  - Orchestrates LLM calls               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  LLM (Claude)                           │
│  - Understands musical intent           │
│  - Reads/writes .rpp format             │
│  - Generates/modifies MIDI              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Project Files                          │
│  - .rpp (Reaper project file)           │
│  - .mid (MIDI files)                    │
│  - Audio assets (.wav, .mp3, etc.)      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Reaper (headless)                      │
│  - Called via CLI to render audio       │
│  - No GUI required                      │
│  - Acts as the "compiler"               │
└─────────────────────────────────────────┘
```

### Key Design Decisions

1. **No live DAW connection** – Monk does not maintain a bridge to a running Reaper instance. It edits files directly and calls Reaper headlessly only for rendering.

2. **Reaper as compiler** – You never need to open Reaper's GUI. It's invoked only to render previews or final audio output.

3. **File-based workflow** – All state lives in the project files (.rpp, MIDI, audio assets). The LLM reads and writes these directly.

4. **Human in the loop** – You are the feedback mechanism. Monk makes changes, renders a preview, you listen and respond.

---

## Why Reaper?

| DAW | Scripting Capability | Project File Format |
|-----|---------------------|---------------------|
| Reaper | Outstanding (ReaScript: Lua, Python, EEL) | **Text-based (.rpp)** – human-readable |
| Ableton Live | Good (Max for Live, Python) | Binary/XML hybrid |
| Logic Pro | Limited (AppleScript, some Lua) | Binary |
| Pro Tools | Limited (proprietary) | Binary |

Reaper wins because:
- The .rpp format is essentially a weird text format, not binary—an LLM can read and modify it directly
- Headless rendering is well-supported
- It's cheap ($60 license)
- Extensive documentation
- No need for live scripting API since we're editing files directly

---

## Workflow

A typical session might look like:

```
You: monk init "summer-song"
Monk: Created new project at ./summer-song/

You: Create a chill lo-fi beat, 85 BPM, with a jazzy Rhodes chord progression

Monk: [creates .rpp file, generates MIDI for drums and Rhodes]
Monk: [calls Reaper to render preview]
Monk: Here's what I've got—a 4-bar loop with a Rhodes progression 
      (Dm7 → G7 → Cmaj7 → Am7) and a simple boom-bap drum pattern.
      [plays audio]
      What do you think?

You: The chords are good but the drums feel too stiff. Make them swing more
     and add some vinyl crackle

Monk: [modifies MIDI velocities and timing, adds audio effect]
Monk: [renders new preview]
Monk: Added swing to the hi-hats and snare, humanized the velocities,
      and put vinyl crackle on a bus. Here's the update.

You: Perfect. Now add a bass line that follows the root notes

Monk: [generates bass MIDI, adds to project]
Monk: [renders]
Monk: Added a simple bass line playing roots on beats 1 and 3 with 
      an octave on the & of 2. Take a listen.
```

---

## What the LLM Needs to Understand

### File Formats

1. **Reaper Project Files (.rpp)**
   - Text-based, hierarchical format
   - Contains track definitions, routing, plugin chains, automation
   - References external MIDI and audio files
   - LLM must be able to parse, reason about, and modify this format

2. **MIDI Files (.mid)**
   - Standard format for note data
   - Contains note on/off events, velocities, timing, control changes
   - LLM generates and modifies these for melodic/rhythmic content

3. **Audio Assets**
   - Monk can reference and arrange existing audio files
   - Cannot modify the *content* of recorded audio (can't change what was played)
   - Can adjust gain, panning, effects, positioning

### Musical Concepts

The LLM needs working knowledge of:
- Rhythm and meter (time signatures, BPM, swing, groove)
- Harmony (chord progressions, voice leading, key relationships)
- Arrangement (song structure, instrumentation, dynamics)
- Production techniques (compression, EQ, reverb, mixing concepts)
- Genre conventions (what makes lo-fi sound like lo-fi, etc.)

---

## Technical Components to Build

### 1. Monk CLI
- Python-based command-line interface
- Manages conversation history and project context
- Handles file I/O
- Calls Reaper for rendering

### 2. Project State Manager
- Parses .rpp files into a representation the LLM can reason about
- Tracks what exists in the project (tracks, regions, plugins)
- Serializes LLM-generated changes back to .rpp format

### 3. MIDI Generator/Editor
- Creates MIDI files from LLM instructions
- Modifies existing MIDI (transpose, quantize, humanize, etc.)
- Standard Python MIDI libraries (mido, pretty_midi) should work

### 4. Render Pipeline
- Calls Reaper headlessly to render audio
- Generates preview MP3s for quick feedback
- Renders final WAV/MP3 for export

### 5. Audio Preview
- Plays rendered audio in the terminal (or opens in default player)
- Could potentially use something like `ffplay` or `mpv` for inline playback

---

## Open Questions

1. **Virtual instruments** – Reaper needs instruments to turn MIDI into audio. Options:
   - Use Reaper's built-in synths (ReaSynth, etc.)
   - Require user to have certain VSTs installed
   - Use external synthesis (FluidSynth + soundfonts) before importing audio

2. **Audio preview in terminal** – What's the best way to play audio from a CLI tool?

3. **Project templates** – Should Monk ship with starter templates (e.g., "lo-fi starter," "rock band template") that pre-configure tracks and instruments?

4. **Multimodal feedback** – Could the LLM eventually "listen" to the rendered audio and self-critique? (Probably not yet—audio understanding models aren't reliable enough)

5. **Version control** – Since .rpp is text-based, could integrate with git for undo/branching

---

## Getting Started (Future)

1. Install Reaper ($60 or free evaluation)
2. Install Monk via pip: `pip install monk-music`
3. Initialize a project: `monk init my-song`
4. Start creating: `monk chat`

---

## References

- [Reaper](https://www.reaper.fm/) – DAW
- [Reaper .rpp file format](https://wiki.cockos.com/wiki/index.php/RPP_File_Format) – Documentation
- [ReaScript documentation](https://www.reaper.fm/sdk/reascript/reascript.php) – Scripting (less relevant since we're editing files directly)
- [mido](https://mido.readthedocs.io/) – Python MIDI library
- [pretty_midi](https://craffel.github.io/pretty-midi/) – Higher-level Python MIDI library

---

## Project Status

**Status:** Concept/Planning

**Next steps:**
1. Get Claude to read and explain a simple .rpp file to understand the format
2. Prototype basic MIDI generation and insertion into a project
3. Test headless rendering with Reaper
4. Build minimal CLI loop
