# Capability matrix

Every row has a status tag. Tags are never collapsed into "supported".

`Last tested (ours)` is empty unless this repo cites a live Logic run. Community TESTED is not our TESTED. This v0 did **not** run Logic.

Target host for later live rows: macOS, Logic Pro 12.3.

| Capability | Primary channel | Fallback | Readback | Status | Last tested (ours) | Logic version | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AU / AUv3 hosting in Logic | Audio Units | none | Logic plug-in slot | VERIFIED | — | 12.x (Apple) | Apple docs. Not VST. |
| AU MIDI Processor type | `kAudioUnitType_MIDIProcessor` | none | MIDI to instrument below | VERIFIED | — | 12.x (Apple) | MIDI FX sit before the instrument. |
| AU stub 4-note phrase (C3 E3 G3 C4) | in-process kernel | none | E02 phrase hash | EXPERIMENTAL | — | — | Coded in `audio-unit/`. Not live-tested. |
| MELEGI AU MIDI FX (extracted) | AU MIDI FX | none | E02 | EXPERIMENTAL | — | — | Sources in `audio-unit/melegi/`. AU only, MIDI FX, not TTS, not Ollama. Live Logic phrase hash UNKNOWN. |
| Scripter HandleMIDI / ProcessMIDI | Scripter JS | none | MIDI out of slot | VERIFIED | — | 12.x (Apple) | JavaScript, not Lua. |
| Scripter +12 transpose | Scripter JS | none | C3→C4 on instrument | UNKNOWN | — | — | E03. Fixture shipped; live UNKNOWN. |
| Scripter project rename / new track | (none) | none | must fail | VERIFIED (API absence) | — | — | E04. Not a project API. |
| MIDI Device Scripts | Lua MDS | none | control-surface assignment | VERIFIED (exists, Lua) | — | 12.x (Apple) | Lua host API UNKNOWN. |
| Custom MDS button → key command | Lua MDS | none | E07 (e.g. record) | UNKNOWN | — | — | E07. |
| Control surface hosting | Logic CSS | none | Setup window | VERIFIED | — | 12.x (Apple) | Hardware/firmware MCU. |
| Virtual MCU transport play/stop | MCU over CoreMIDI | CGEvent | MCU echo or MMC, not AX | EXPERIMENTAL | — | — | Community TESTED. Ours: E05 UNKNOWN. |
| MCU fader write + echo | MCU | AX (forbidden as pass) | MCU echo within tolerance | TESTED | 2026-09-11 (studio Mac, Logic 12.2, live echo) | 12.2 | Implementation in `logic_probe`. E06 returns `confirmed` + `mcu_feedback`, echo within ~0.03 dB, repeatable. Mackie Control assigned: Logic INPUT `logic-probe-mcu-cmd`, OUTPUT `logic-probe-mcu-fb`. Logic echoes only on CHANGE, so a no-op send is disambiguated by a nudge. TESTED, not VERIFIED: MCU bytes are not an Apple spec. MELEGI not used. |
| CoreMIDI virtual endpoints | CoreMIDI | IAC | MIDI monitor | VERIFIED (API) | — | macOS | Agent use in Logic: E01 UNKNOWN. |
| NoteOn C3 to software instrument | CoreMIDI | IAC | region or input monitor | UNKNOWN | — | — | E01. AX "key highlighted" forbidden. |
| Apple OSC paths | Logic OSC (UDP/IPv4) | none | Logic OSC monitor | VERIFIED (path set) | — | 12.x (Apple) | Invented `/track/N/volume` is not Apple OSC. |
| Accessibility inspect selected track | AXUIElement | none | AX tree | UNKNOWN (Logic contract: none) | — | — | macOS API VERIFIED. Probe returns `uncertain` without Logic. Never fake `confirmed`. |
| CGEvent key command | CGEvent | none | independent state | EXPERIMENTAL | — | — | Last-resort. Send ≠ success. |
| AppleScript project edit | Logic sdef | System Events | — | UNKNOWN | — | — | Apple publishes no Logic sdef. |
| Mixer set-volume track N | MCU | AX (not pass bit) | MCU echo | UNKNOWN | 2026-09-01 (studio Mac, envelope) | 12.x | CLI attempts MCU over IAC `logic-probe-mcu-cmd`/`-fb`. `confirmed` only on echo. Prefs: Logic Remote iPad; SSL 2+ MIDI offline; no Mackie named ports. See docs/MCU.md. |
| Bounce RMS / onset fingerprint | Bounce + audio hash | none | E10 fixture | UNKNOWN | — | — | E10. Screenshot of dialog forbidden. |
| VST / VST3 in Logic native path | — | — | — | VERIFIED absent | — | — | E08. AU only. |
| Realtime render: no malloc/lock | C++ kernel | none | E09 hook | EXPERIMENTAL (static) | — | — | Static scan tonight. Live TSan UNKNOWN. |
| MCP adapter | thin adapter | none | harness pass list | UNKNOWN | — | — | Last. Not started. |
| GNOMO decision ladder (tier 0-3) | repo-local rules | none | decision record in `studio/datasets/decisions.jsonl` | EXPERIMENTAL | — | — | Touches no Logic surface. Unmatched action fails closed to tier 2; tier 1 without a stated rollback is downgraded. Unit-tested, not a live claim. |
| GNOMO spoken mouth | macOS `say` via `scripts/speak.py` | none | `say` returncode + `spoken.jsonl` | EXPERIMENTAL | — | macOS | One mouth, reused. Off macOS reports `spoke: false`. Printed text is not speech. Not a singing model, not a voice clone. |
| GNOMO guided MCU setup (steps 3-4, in Logic's window) | none (human hands) | none | none available | UNKNOWN | — | — | `com.apple.logic.pro.cs` is an undocumented hint Logic may not flush until quit; it cannot close a step. E06 echo is the only pass bit. |
| GNOMO desk companion window | AppKit panel over the CLI | none | window renders CLI records; routing pinned by `companion_router.py` tests | EXPERIMENTAL | 2026-09-11 (studio Mac) | macOS | A face, not a brain: one photo, tier gestures, bubble, type-to-decide. Body verbs (walk/zoom/point) move the window only, never ledger. Ears push-to-talk, transcript routes like typed text. |
| GNOMO hands: look / find / point (any front app) | AXUIElement tree + CGEvent cursor move | none | none (observe only) | UNKNOWN | — | — | `python -m gnomo hands look|find|point`. Tier 0 unless the ladder refuses. Swift helper `companion/gnomo_hands.swift` has not been compiled or run yet. Needs Accessibility permission. |
| GNOMO hands: click / type / key (any front app) | AXPress, then CGEvent click; CGEvent keys | none | none; reply is `attempted` + channel | UNKNOWN | — | — | Ladder first (tier 3 never reaches the helper), then a native "Do it" dialog for every action. No skip flag or mode. Touching mouse/keyboard within 750 ms makes it let go. Never reports `confirmed` (HONEST_CONTRACT rule 4). Not run yet. See [HANDS.md](HANDS.md). |
| GNOMO hearing / judging audio | — | — | — | VERIFIED absent | — | — | No ears at any tier. Refused as tier 3 however phrased, including a hearing request worded as a read. |

Status vocabulary: [SURFACE.md](../SURFACE.md). Contract: [HONEST_CONTRACT.md](HONEST_CONTRACT.md).
