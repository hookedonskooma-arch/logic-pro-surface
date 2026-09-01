# Architecture

AU / MIDI / control-surface first. MCP last. Not a MongLong clone.

```
         agent / operator
                 │
            logic-probe
             (envelope)
                 │
     ┌───────────┼───────────┐
     │           │           │
    AU        MIDI        surface
  MIDI FX    CoreMIDI      MCU
  Scripter     IAC        MDS Lua
  (JS)                     OSC
     │           │           │
     └───────────┼───────────┘
                 │
            Logic Pro
                 │
            readback
                 │
        confirmed / uncertain / failed
```

MCP, if it ever exists here, is a thin adapter over channels **this harness has already passed**. It is not the product. It is not a first-party Logic API.

## In-Logic lane (own this)

1. **Audio Units / AUv3** — VERIFIED. Native third-party path. Stack in `audio-unit/`: Swift `AUAudioUnit` layer, Objective-C++ adapter, C++ kernel. Render path: no alloc, no I/O, no locks, no Swift/ObjC. MIDI FX type `aumi` / `kAudioUnitType_MIDIProcessor`.
2. **Scripter** — VERIFIED. JavaScript MIDI plug-in. Not a project API (E04).
3. **MIDI Device Scripts** — VERIFIED that they exist and are Lua. Host Lua API: UNKNOWN (Apple publishes no reference).
4. **Control surfaces / Mackie Control** — VERIFIED that Logic hosts MCU-class devices. A software virtual MCU is community-TESTED, EXPERIMENTAL for us until E05/E06.
5. **CoreMIDI / IAC** — VERIFIED as macOS APIs. Agent-grade use in Logic is TESTED only after E01.

## Workaround lane (fallback only)

Accessibility, CGEvent, AppleScript/System Events. macOS APIs, not Logic APIs. Never the pass bit.

## Why this is not a MongLong clone

MongLong0214/logic-pro-mcp already runs the outside-the-app MCP race (AX + MCU + fail-closed envelopes). We are not rebuilding that. Their honesty gap, which they document, is musical truth: AX receipts and MCU echo are not SMF / Event List / bounce hash. [EVALS.md](../EVALS.md) scores that gap. We publish the map and the in-Logic brick first.

## Probe envelope

Every actuation returns JSON with `before`, `adapter_result`, `readback`, `verification`, `status`. v0 implements the envelope and host detection. It does not implement MCU writes. On this Linux drop, Logic is not reachable → `uncertain`.

## Build order

1. Map + contract (tonight).
2. AU MIDI FX brick (Apple stub in `audio-unit/`; MELEGI JUCE extract in `audio-unit/melegi/`).
3. Ten fail-closed evals.
4. MCP adapter last.

See [SHIP.md](../SHIP.md).
