# Monk Music

![Monk Music](assets/hero.jpg)

An LLM-driven CLI for music production. Describe what you want in natural language, and Monk creates MIDI, modifies your Reaper project, and renders audio — all without touching a DAW.

**Monk is to Reaper what Claude Code is to Xcode.**

## How It Works

```
You: "Create a chill lo-fi beat at 85 BPM with a jazzy chord progression"

Monk: [creates MIDI, adds tracks with synths, renders audio]
      Here's a 4-bar loop with Dm7 → G7 → Cmaj7 → Am7 and a boom-bap drum pattern.
      [plays audio]

You: "Make the drums swing more and add a bass line"

Monk: [modifies MIDI, re-renders]
      Added swing to the hi-hats and a root-note bass line. Take a listen.
```

## Installation

**Requirements:**
- Python 3.9+
- [Reaper DAW](https://www.reaper.fm/) ($60 license)
- `ANTHROPIC_API_KEY` environment variable

```bash
pip install -e .
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

```bash
# Create a new project
monk init my-song

# Start creating music
cd my-song
monk chat
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `/render` | Render and play current project |
| `/status` | Show project status |
| `/quit` | Exit |

### What You Can Ask

- "Create a chord progression in C major"
- "Add a drum pattern with kick on 1 and 3, snare on 2 and 4"
- "Make a melody in A minor"
- "Change the tempo to 140 BPM"
- "Add a bass line following the root notes"

## Architecture

```
You (natural language)
        ↓
    Monk CLI
        ↓
  LLM (Claude) ──→ MIDI files + Reaper project (.rpp)
        ↓
  Reaper (headless render)
        ↓
    Audio playback
```

Key design decisions:
- **No live DAW connection** — Monk edits .rpp files directly
- **Reaper as compiler** — Only invoked for rendering, never for editing
- **File-based workflow** — All state lives in project files

## Project Structure

When you run `monk init`, it creates:

```
my-song/
├── my-song.rpp     # Reaper project file
├── midi/           # Generated MIDI files
├── renders/        # Rendered audio (WAV)
└── audio/          # Audio assets (samples, etc.)
```

## Why Reaper?

| DAW | Project Format | Headless Render |
|-----|----------------|-----------------|
| **Reaper** | Text-based (.rpp) | Yes |
| Ableton | Binary/XML | No |
| Logic Pro | Binary | No |
| Pro Tools | Binary | No |

Reaper's `.rpp` format is human-readable text — an LLM can read and modify it directly.

## License

MIT

---

*Named after Thelonious Monk, the jazz pianist who bent harmony and rhythm in innovative ways.*
