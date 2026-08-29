# Logic Pro agent surface map

Date: 2026-08-29
Author: GROUXX / Christian Grau
Status: Phase 1 reviewer artifact. Not a claim that we have shipped a bridge.

Logic Pro has no documented public API for project control, session setup, mixer automation, or live project readback. Anyone who tells an agent "just use the Logic API" is wrong.

We still have real surfaces. They are not one stack. Mixing them without tags is how you ship a liar.

## Tags

| Tag | Meaning |
| --- | --- |
| VERIFIED | Apple documents this. URL required. |
| TESTED | Cited live run against Logic. |
| EXPERIMENTAL | Observed, not a contract. |
| UNKNOWN | Not proved here. |

Do not collapse these into "supported."

## 1. VERIFIED Apple surfaces (in-Logic)

These are the lane we will own.

### 1.1 Audio Units / AUv3

**Tag: VERIFIED**

Logic's native third-party plugin path is Audio Units, not VST. Never say "Logic's plugin API is VST." That is incorrect.

- Host interface: [`AUAudioUnit`](https://developer.apple.com/documentation/audiotoolbox/auaudiounit). Parameters: [`AUParameterTree`](https://developer.apple.com/documentation/audiotoolbox/auparametertree).
- [AUv3 plug-ins](https://developer.apple.com/documentation/audiotoolbox/audio-unit-v3-plug-ins). Apple silicon Logic hosts [most AUv2 and AUv3](https://support.apple.com/en-us/102082), including iOS/iPadOS AUv3. Intel-only AUs need Rosetta. Logic itself should stay native.
- MIDI FX type is [`kAudioUnitType_MIDIProcessor`](https://developer.apple.com/documentation/audiotoolbox/kaudiounittype_midiprocessor). Instrument is `kAudioUnitType_MusicDevice`. Effect is `kAudioUnitType_Effect`. Music effect (audio + MIDI) is `kAudioUnitType_MusicEffect`.
- Logic [MIDI plug-ins](https://support.apple.com/guide/logicpro/use-midi-plug-ins-lgcef1c11e8f/mac) sit in series **before** the instrument and emit standard MIDI. An AU is not a project API: no tracks, regions, or `.logicx` I/O.
- Stack: Swift `AUAudioUnit` layer, Objective-C++ adapter, C++ DSP kernel.
- Apple, on the render path: do not allocate memory, perform file I/O, take locks, or interact with the Swift or Objective-C runtimes. Source: [Creating custom audio effects](https://developer.apple.com/documentation/avfaudio/creating-custom-audio-effects) and [`internalRenderBlock`](https://developer.apple.com/documentation/audiotoolbox/auaudiounit/internalrenderblock).

Our `NEWMELEGI` CMake is `FORMATS AU` only, `IS_MIDI_EFFECT TRUE`, not a synth. Repo copy that calls it an "AU instrument" is wrong. Live install at `~/Library/Audio/Plug-Ins/Components/MELEGI.component` is **UNKNOWN** to this reviewer.

### 1.2 Scripter = JavaScript MIDI processing

**Tag: VERIFIED**

Scripter is **not Lua**. It is a JavaScript MIDI plug-in on a channel strip. It is not a Logic project API.

Apple:
- [Use Scripter](https://support.apple.com/guide/logicpro/use-scripter-lgce728c68f6/mac)
- [Scripter API overview](https://support.apple.com/guide/logicpro/scripter-api-overview-lgce3905a48c/mac)
- [`HandleMIDI`](https://support.apple.com/guide/logicpro/handlemidi-function-lgce12088271/mac)
- [`ProcessMIDI`](https://support.apple.com/guide/logicpro/processmidi-function-lgce225e4d89/mac)
- [Create controls](https://support.apple.com/guide/logicpro/create-scripter-controls-lgce9f7063b5/mac)

Use it for MIDI transform, arps, chords, velocity, note filter, timing, MIDI-side agent helpers. Requires Enable Complete Features. Cannot rename the project, create tracks, or host other AUs.

### 1.3 MIDI Device Scripts = Lua

**Tag: VERIFIED that MDS exists and is Lua. The Lua host API itself is UNKNOWN (Apple publishes no reference).**

Different system from Scripter.

- Scripter: JavaScript, per-track MIDI FX.
- MDS: Lua, USB controller auto-assignment and control-surface mapping. Modeless zone named after the device, tied to Control Surface Group 1.

Apple:
- [Automatic assignment for USB MIDI controllers](https://support.apple.com/guide/logicpro/automatic-assignment-for-usb-midi-controllers-ctlsbfee6d57/mac)
- [Control surfaces supported](https://support.apple.com/guide/logicpro/supported-control-surfaces-ctls718dd5b2/mac)

Scripts live under `~/Music/Audio Music Apps/MIDI Device Scripts` and `/Library/Audio/MIDI Device Scripts`.

On Apple silicon, third-party binary MIDI Device Plug-ins are Intel-only. Built-in MDP/MDS or a manufacturer Lua MDS is the path. On Intel, if both Lua and MDP exist, MDP wins.

Custom `config.lua` is reverse-engineered from bundled scripts. **TESTED** by the community, not Apple-specified.

### 1.4 Control surfaces / Mackie Control / OSC

**Tag: VERIFIED that Logic hosts MCU-class surfaces and OSC. A software virtual MCU is TESTED (community), not Apple-specified.**

- [Mackie Control overview](https://support.apple.com/guide/logicpro-css/mackie-control-overview-ctls7222820e/mac). Powered MCU is auto-detected. Apple's "Mackie Control" includes devices in MCU emulation mode.
- [Control Surfaces Support Guide (PDF)](https://help.apple.com/pdf/logicpromac-css/en_US/logic-pro-mac-control-surfaces-support-guide.pdf)
- [OSC message paths](https://support.apple.com/guide/logicpro/osc-message-paths-ctlsf67f4bdc/mac): UDP/IPv4 only.

Apple documents hardware/firmware MCU emulation, not a virtual software controller. A CoreMIDI virtual source that speaks MCU can be added in Setup. That is our strategic in-Logic control path, and it stays **EXPERIMENTAL** until [EVALS.md](EVALS.md) E05/E06 pass.

MCU is mixer, transport, and banks. It is not an arrangement or region API. Apple does not publish the MCU byte protocol.

### 1.5 CoreMIDI / Core Audio

**Tag: VERIFIED as macOS APIs. Agent-grade use in Logic is TESTED only after harness evals.**

[CoreMIDI](https://developer.apple.com/documentation/coremidi) virtual endpoints and the [IAC Driver](https://support.apple.com/guide/audio-midi-setup/ams1013/mac) carry MIDI. [Core Audio](https://developer.apple.com/documentation/coreaudio) is the engine. Neither is a Logic session API.

## 2. Workaround channels (outside-the-app)

Use these only as fallbacks. Never advertise them as a Logic API.

| Channel | What it is | Tag |
| --- | --- | --- |
| Accessibility (AX) | [`AXUIElement`](https://developer.apple.com/documentation/applicationservices/axuielement) UI tree | macOS API VERIFIED. Logic contract: none. Trees move every release. |
| CGEvent / PostEvent | [`CGEvent`](https://developer.apple.com/documentation/coregraphics/cgevent) synthetic HID | macOS API VERIFIED. Last-resort actuation. |
| AppleScript / System Events | UI scripting for non-scriptable apps | Apple publishes **no Logic sdef**. System Events is [official for UI automation](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AutomatetheUserInterface.html), not a Logic object model. |
| MIDI key commands | Mapped key commands over MIDI | TESTED by incumbents. Logic 12.2+ dropped legacy plist import. |

MongLong's own track resource reports `source:"ax_live"`. That is a UI receipt.

## 3. Incumbent teardown

We are not racing them on their field.

### MongLong0214/logic-pro-mcp

**Tag: TESTED (their claims, from their README on 2026-08-29). We have not re-run their live suite.**

- https://github.com/MongLong0214/logic-pro-mcp
- MIT. Swift. Stable **v3.14.0** (2026-08-22). Homebrew tap. Site: https://logicpromcp.com/
- README badge: 3917 Swift tests, 63 stars at lookup.
- They say, correctly: Logic does not ship a first-party API for agentic composition, session setup, mixer ops, or live project readback.
- Seven channels behind one MCP: MCU, Accessibility, AppleScript, CoreMIDI, CGEvent, Scripter, MIDI Key Commands.
- Honest Contract: confirmed / uncertain / failed. This part is good engineering.
- Doctor requires Accessibility, Automation → Logic, Automation → System Events, and PostEvent.
- Track and mixer readback is AX. Plugin insert verification is AX inventory diff.
- Last full strict live E2E they cite is the v3.8.0 line (372/373). Later surfaces are spike-tested or deferred. 3917 tests are mostly deterministic Swift, not live Logic.
- Selected for Anthropic Claude for Open Source.

Honesty gap: they are the best outside MCP, and they still score UI state. MIDI export read-back and Channel EQ verified params are deferred in their own changelog.

### koltyj/logic-pro-mcp

**Tag: UNKNOWN beyond listing.** ~80 stars, Swift, "8 dispatcher tools + 7 resources across 5 native macOS channels." https://github.com/koltyj/logic-pro-mcp

### rubenknol/logic-pro-mcp

**Tag: UNKNOWN beyond README listing.** TypeScript MCP + Python MCU worker. Favors Mackie Control over clicking. https://github.com/rubenknol/logic-pro-mcp

Rebuilding any of these is how we come in third.

## 4. Our lane

1. In-Logic surfaces first: AU MIDI Processor (`aumi`), Scripter helpers, Lua MDS / virtual MCU / OSC.
2. Harness that scores musical truth: note on the track, MIDI out of the AU, transport via MCU echo, bounce audio hash. Not `ax_live`.
3. MCP last, and only for channels the harness passed.
4. Open-source this map, then the AU brick, then the evals. Not the Ollama band stack.

## 5. What we will not say

- "Logic's plugin API is VST."
- "Scripter is Lua."
- "MIDI Device Scripts are JavaScript."
- "Apple documents the Lua MDS API."
- "The Logic MCP is a first-party API."
- "Accessibility verified the region."

See [EVALS.md](EVALS.md) for the first ten fail-closed tests.
