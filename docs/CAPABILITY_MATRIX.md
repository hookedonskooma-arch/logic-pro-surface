# Capability matrix

Every row has a status tag. Tags are never collapsed into "supported".

`Last tested (ours)` is empty unless this repo cites a live Logic run. Community TESTED is not our TESTED. This v0 did **not** run Logic.

Target host for later live rows: macOS, Logic Pro 12.3.

| Capability | Primary channel | Fallback | Readback | Status | Last tested (ours) | Logic version | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AU / AUv3 hosting in Logic | Audio Units | none | Logic plug-in slot | VERIFIED | — | 12.x (Apple) | Apple docs. Not VST. |
| AU MIDI Processor type | `kAudioUnitType_MIDIProcessor` | none | MIDI to instrument below | VERIFIED | — | 12.x (Apple) | MIDI FX sit before the instrument. |
| AU stub 4-note phrase (C3 E3 G3 C4) | in-process kernel | none | E02 phrase hash | EXPERIMENTAL | — | — | Coded in `audio-unit/`. Not live-tested. |
| MELEGI AU MIDI FX (extracted) | AU MIDI FX | none | E02 | UNKNOWN | — | — | Source not in this drop. |
| Scripter HandleMIDI / ProcessMIDI | Scripter JS | none | MIDI out of slot | VERIFIED | — | 12.x (Apple) | JavaScript, not Lua. |
| Scripter +12 transpose | Scripter JS | none | C3→C4 on instrument | UNKNOWN | — | — | E03. Fixture shipped; live UNKNOWN. |
| Scripter project rename / new track | (none) | none | must fail | VERIFIED (API absence) | — | — | E04. Not a project API. |
| MIDI Device Scripts | Lua MDS | none | control-surface assignment | VERIFIED (exists, Lua) | — | 12.x (Apple) | Lua host API UNKNOWN. |
| Custom MDS button → key command | Lua MDS | none | E07 (e.g. record) | UNKNOWN | — | — | E07. |
| Control surface hosting | Logic CSS | none | Setup window | VERIFIED | — | 12.x (Apple) | Hardware/firmware MCU. |
| Virtual MCU transport play/stop | MCU over CoreMIDI | CGEvent | MCU echo or MMC, not AX | EXPERIMENTAL | — | — | Community TESTED. Ours: E05 UNKNOWN. |
| MCU fader write + echo | MCU | AX (forbidden as pass) | MCU echo within tolerance | EXPERIMENTAL | — | — | Community TESTED. Ours: E06 UNKNOWN. |
| CoreMIDI virtual endpoints | CoreMIDI | IAC | MIDI monitor | VERIFIED (API) | — | macOS | Agent use in Logic: E01 UNKNOWN. |
| NoteOn C3 to software instrument | CoreMIDI | IAC | region or input monitor | UNKNOWN | — | — | E01. AX "key highlighted" forbidden. |
| Apple OSC paths | Logic OSC (UDP/IPv4) | none | Logic OSC monitor | VERIFIED (path set) | — | 12.x (Apple) | Invented `/track/N/volume` is not Apple OSC. |
| Accessibility inspect selected track | AXUIElement | none | AX tree | UNKNOWN (Logic contract: none) | — | — | macOS API VERIFIED. Probe returns `uncertain` without Logic. Never fake `confirmed`. |
| CGEvent key command | CGEvent | none | independent state | EXPERIMENTAL | — | — | Last-resort. Send ≠ success. |
| AppleScript project edit | Logic sdef | System Events | — | UNKNOWN | — | — | Apple publishes no Logic sdef. |
| Mixer set-volume track N | MCU | AX (not pass bit) | MCU echo | UNKNOWN | — | — | v0 probe: `uncertain` without Logic and without MCU. |
| Bounce RMS / onset fingerprint | Bounce + audio hash | none | E10 fixture | UNKNOWN | — | — | E10. Screenshot of dialog forbidden. |
| VST / VST3 in Logic native path | — | — | — | VERIFIED absent | — | — | E08. AU only. |
| Realtime render: no malloc/lock | C++ kernel | none | E09 hook | EXPERIMENTAL (static) | — | — | Static scan tonight. Live TSan UNKNOWN. |
| MCP adapter | thin adapter | none | harness pass list | UNKNOWN | — | — | Last. Not started. |

Status vocabulary: [SURFACE.md](../SURFACE.md). Contract: [HONEST_CONTRACT.md](HONEST_CONTRACT.md).
