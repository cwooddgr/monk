# Redesign ideas

> **Author:** Claude Code (planner)
> **Date:** 2026-09-30
> **Status:** proposed-by-agent

Ideas for later, if we return to Monk. Nothing here has been built, tested, or agreed to. Charlie asked for them to be written down; he hasn't picked any of them.

## Background

The MVP (January 2026) used `claude-sonnet-4-20250514`, hardcoded in `monk/llm.py`, and its output wasn't very musical. My view is that a current model (Opus 5.5, Fable 5.1) would improve theory, arrangement coherence, instruction-following over long sessions, and tool use. I think it would do much less for how the music actually sounds, because the main limits are in Monk's design:

- **The model can't hear the result.** It writes notes and never perceives the render. The user is the only feedback.
- **The tools are too low-level.** `create_midi` makes the model list every note by hand, and there's little room for velocity, timing, swing, or articulation.
- **Monk barely controls timbre.** Instrument sounds, effects, and mixing matter more than the notes, and Monk hardly touches them in the .rpp.

This is my judgment, not a measurement. I haven't run a newer model against Monk.

## Ideas

### 1. Let the model write code that generates MIDI

Instead of note-by-note tool calls, the model writes Python (mido or music21) that produces the MIDI. Code lets it express patterns, variation, and humanization (velocity curves, microtiming, swing) with loops and functions rather than long note lists. It would need a sandboxed execution step.

### 2. Close the feedback loop

After each render, give the model:
- a spectrogram image of the rendered audio (current models read images well), and
- a text or image piano-roll view of the MIDI it wrote.

The aim is for it to catch problems on its own, such as a muddy low end, clashing registers, or rhythms locked to the grid, before the user has to point them out.

### 3. Real control over sound

Add tools for choosing each track's instrument plugin and presets and for adding effects (EQ, compression, reverb) to the .rpp. This probably needs a curated list of plugins available on the machine so the model doesn't invent ones that aren't installed.

### 4. Upgrade the model

Swap the hardcoded model ID for a current one, and make it configurable. This is the cheapest change, but I'd do it together with 1–3 rather than by itself.
