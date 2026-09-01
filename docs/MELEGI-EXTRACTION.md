# MELEGI extraction

Extracted 2026-09-01 from the studio plugin tree. **AU MIDI FX only.**

This extract is **not TTS**, **not audio pass-through**, **not Ollama**.

## Source (read, not modified)

`/Users/neonpissstudios/dev/melegi/newmelegi/plugin/`

CMake (kept): `FORMATS AU`, `IS_MIDI_EFFECT TRUE`, `IS_SYNTH FALSE`, `NEEDS_MIDI_INPUT TRUE`, `NEEDS_MIDI_OUTPUT TRUE`.

JUCE lives at `/Users/neonpissstudios/dev/melegi/juce` (symlink `~/JUCE`). It is **not** vendored here.

## What was copied

Into `audio-unit/melegi/`:

| Path | Notes |
| --- | --- |
| `Source/PluginProcessor.cpp` | Phrase FIFO, host-clock MIDI emit, `BusesProperties()` empty (no audio buses) |
| `Source/PluginProcessor.h` | `isMidiEffect() == true` |
| `Source/PluginEditor.cpp` | WebView native bridge (`queuePhrase`, host context, loop) |
| `Source/PluginEditor.h` | |
| `Source/VozBridgeClient.h` | Header-only localhost TCP param client (compile-required). Not TTS. |
| `CMakeLists.txt` | Adapted: `JUCE_PATH` / optional FetchContent 8.0.13, `FORMATS AU` only, copy-after-build off by default |
| `Resources/plugin_ui.html` | **Sanitized MIDI FX panel.** Queues C3 E3 G3 C4 via `queuePhrase`. |
| `README.md` | JUCE fetch instructions |

`NEEDS_WEB_BROWSER TRUE` is existing MELEGI — kept because `PluginEditor` will not compile without it. Not expanded.

`HARDENED_RUNTIME_OPTIONS com.apple.security.network.client` is existing MELEGI (VozBridge localhost TCP). Kept. Not an Ollama client.

## What was left private

Do not copy these into this repo:

- Ollama / local LLM runtime
- `ai-stack`, `vibe-producer`, `beatstore`
- `newmelegi/backend/`, catalog, songs
- `newmelegi/ui/` (control room `app.html` / `plugin.html`)
- `plugin/Resources/plugin_ui.html` **original** — talks to `http://127.0.0.1:4780` and `ws://127.0.0.1:4780/ws` (private band backend, agent rack, vibe pad, MCP badges)
- `plugin/make_ui.py` — copies from `../ui/plugin.html`
- `plugin/voz-bridge/` — Node companion for a FORMANT/vocal slice; not MIDI FX
- `plugin/build/`, installed `MELEGI.component`
- The JUCE source tree (document fetch of **8.0.13** instead)

## Stub vs extract

`audio-unit/` Apple-shaped stub (Swift / Objective-C++ / C++ `PhraseKernel`, 4-note C3 E3 G3 C4) stays. Linux-safe E08/E09 scans still target that stub.

`audio-unit/melegi/` is the JUCE AU MIDI FX extract, added **alongside** the stub after a local AU build — the stub is not replaced.

Taste Director: this is not a vocal/TTS plugin. Spoken mouth remains macOS `say` (`studio/VOICE.md`).

## JUCE

Not a git submodule and not vendored. See `audio-unit/melegi/README.md`.

```bash
git clone --branch 8.0.13 --depth 1 https://github.com/juce-framework/JUCE.git
cmake -S audio-unit/melegi -B audio-unit/melegi/build \
  -DJUCE_PATH=/path/to/JUCE -DCMAKE_BUILD_TYPE=Release
cmake --build audio-unit/melegi/build --config Release
```

`-DMELEGI_FETCH_JUCE=ON` clones 8.0.13 into the build dir only.

## Build (studio Mac, 2026-09-01)

Configured with `-DJUCE_PATH=$HOME/JUCE` (8.0.13-family checkout). Artefact:

`audio-unit/melegi/build/MELEGI_artefacts/Release/AU/MELEGI.component`

Info.plist `AudioComponents.type` = **`aumi`**. Release folder contains `AU/` only — no VST / VST3 product. Stub in `audio-unit/` was left in place (augment, not replace).

Copy-after-build was **off**, so this did not overwrite `~/Library/Audio/Plug-Ins/Components/MELEGI.component`.

## Honesty

- Compile of the AU MIDI FX brick: done on the studio Mac. Not a live Logic TESTED claim.
- Live install / E02 phrase hash against Logic Pro 12.3: **UNKNOWN** until a cited run. Plugin window opened is forbidden evidence.
- `processBlock` still calls `VozBridgeClient::sendParam` (localhost TCP). That is existing MELEGI, not render-path-clean like the stub kernel. E09 static scan stays on `audio-unit/cpp-dsp`, not this JUCE editor.
- A green Linux CI run is not TESTED against Logic.
