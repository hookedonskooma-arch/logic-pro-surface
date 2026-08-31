# MELEGI extraction

Stub shipped because the MELEGI source is **not in this drop**.

## Source (later, not copied)

Studio tree (sits next to Ollama / band / backend — do not copy those):

`/Users/neonpissstudios/dev/melegi/newmelegi/plugin/`

Extract **AU MIDI FX only**. Never the Ollama band stack. Never ai-stack, vibe-producer, beatstore, or backend.

## What v0 ships instead

`audio-unit/` — a clean Apple-shaped MIDI Processor stub:

- Swift `AUAudioUnit` layer
- Objective-C++ adapter
- C++ kernel that can emit C3 E3 G3 C4 (E02 phrase)
- CMake: AU only, MIDI effect, not a synth, not VST

This stub is not MELEGI. Live install of `MELEGI.component` remains **UNKNOWN** (see SURFACE.md).

## What to lift later (from plugin/CMakeLists.txt, inspected 2026-08-31, not copied)

Observed flags — keep these:

- `FORMATS AU`
- `IS_MIDI_EFFECT TRUE`
- `IS_SYNTH FALSE`
- `NEEDS_MIDI_INPUT TRUE`
- `NEEDS_MIDI_OUTPUT TRUE`
- Sources named `Source/PluginProcessor.cpp`, `Source/PluginEditor.cpp`

Leave behind:

- Ollama, band, backend, web control surfaces that are not the MIDI FX
- `NEEDS_WEB_BROWSER TRUE` / `Resources/plugin_ui.html` unless a later eval truly needs UI
- `HARDENED_RUNTIME_OPTIONS com.apple.security.network.client` — a MIDI FX does not need network
- Any path that would add VST or VST3 to `FORMATS`

SURFACE.md: a repo copy that calls MELEGI an "AU instrument" is wrong. It is a MIDI effect.

## JUCE vs Apple stack

MELEGI today is a JUCE AU MIDI effect. This repo's long-term stack is the Apple sample shape (Swift / Objective-C++ / C++). Extraction may:

1. Keep JUCE for a first E02 pass (`FORMATS AU` only), or
2. Re-host the MIDI FX behavior in the stub kernel.

Either way: AU only, MIDI effect, not a synth, no VST, no Ollama.

## E02 acceptance (later)

Phrase hash of C3 E3 G3 C4 (`60 64 67 72`) on the instrument below the MIDI FX slot, on Logic Pro 12.3. Plugin window opened is forbidden evidence. Not claimed TESTED in v0.
