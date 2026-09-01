# MELEGI AU MIDI FX

JUCE Audio Unit **MIDI effect** (`aumi` / `kAudioUnitType_MIDIProcessor`).

This extract is:

- AU only (`FORMATS AU`)
- MIDI FX (`IS_MIDI_EFFECT TRUE`, `IS_SYNTH FALSE`)
- MIDI in + MIDI out, **no audio buses**
- **not TTS**, **not audio pass-through**, **not Ollama**

It is not the MELEGI app stack (backend, band, vibe-producer, songs).

## JUCE (not vendored)

The JUCE tree is huge and stays out of git. Studio build used **JUCE 8.0.13**.

```bash
git clone --branch 8.0.13 --depth 1 https://github.com/juce-framework/JUCE.git
cmake -S audio-unit/melegi -B audio-unit/melegi/build \
  -DJUCE_PATH=/path/to/JUCE -DCMAKE_BUILD_TYPE=Release
cmake --build audio-unit/melegi/build --config Release
```

If `~/JUCE` already points at a checkout, omit `-DJUCE_PATH`.

Optional: `-DMELEGI_FETCH_JUCE=ON` clones 8.0.13 into the **build directory** only.

Install into Logic: `-DMELEGI_COPY_PLUGIN_AFTER_BUILD=ON`.

`NEEDS_WEB_BROWSER` is required to compile the existing editor. Do not expand it.

`HARDENED_RUNTIME_OPTIONS com.apple.security.network.client` is existing MELEGI (local TCP param client). It is not an Ollama client.

## Layout

- `Source/PluginProcessor.*` — phrase FIFO, host-clock MIDI emit, empty `BusesProperties()`
- `Source/PluginEditor.*` — WebView + native `queuePhrase` / host context
- `Source/VozBridgeClient.h` — leftover localhost TCP param forwarder; companion Node `voz-bridge/` was **not** copied (vocal/FORMANT slice, not MIDI FX)
- `Resources/plugin_ui.html` — MIDI FX panel only. Original UI talked to a private backend on `:4780` and was **not** copied.

Apple-shaped stub remains in `audio-unit/` (Swift / ObjC++ / C++ kernel) for Linux-safe E08/E09 scans.

Live E02 against Logic Pro 12.3 remains **UNKNOWN** until a cited run.
