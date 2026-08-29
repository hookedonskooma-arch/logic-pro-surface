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

- Host interface: [`AUAudioUnit`](https://developer.apple.com/documentation/audiotoolbox/auaudiounit)
- AUv3 is the current extension model. Apple silicon Logic hosts AUv2 and AUv3.
- Recommended stack: Swift `AUAudioUnit` layer → Objective-C++ adapter → C++ DSP kernel.
- Real-time render path must avoid memory allocation, file I/O, locks, and Swift / Objective-C runtime.
- Know: `AUParameterTree`, `AudioComponentDescription`, `AudioBus`, `AudioBufferList`, `AURenderBlock`, `internalRenderBlock`, `allocateRenderResources` / `deallocateRenderResources`, in-process vs out-of-process hosting.

Our existing `NEWMELEGI` plugin CMake is `FORMATS AU` only, `IS_MIDI_EFFECT TRUE`, not a synth. Repo copy that calls it an "AU instrument" is wrong. Live install at `~/Library/Audio/Plug-Ins/Components/MELEGI.component` is **UNKNOWN** to this reviewer.

### 1.2 Scripter = JavaScript MIDI processing

**Tag: VERIFIED**

Scripter is **not Lua**. It is a JavaScript MIDI plug-in inside a channel strip. It is not a Logic project API.

Apple:
- [Scripter API overview](https://support.apple.com/guide/logicpro/scripter-api-overview-lgce3905a48c/mac)
- [Use Scripter](https://support.apple.com/guide/logicpro/use-scripter-lgce728c68f6/mac)
- [`HandleMIDI`](https://support.apple.com/guide/logicpro/handlemidi-function-lgce12088271/mac)
- [`ProcessMIDI`](https://support.apple.com/guide/logicpro/processmidi-function-lgce225e4d89/mac)

Use it for: MIDI transform, arps, chords, velocity, note filter, timing, MIDI-side agent helpers.

Requires Enable Complete Features in Logic settings.

### 1.3 MIDI Device Scripts = Lua

**Tag: VERIFIED**

Different system from Scripter.

- Scripter: JavaScript, MIDI plug-in processing on a track.
- MIDI Device Script: Lua, USB controller auto-assignment and control-surface mapping.

Apple:
- [Automatic assignment for USB MIDI controllers](https://support.apple.com/guide/logicpro/automatic-assignment-for-usb-midi-controllers-ctlsbfee6d57/mac)
- [Control surfaces supported](https://support.apple.com/guide/logicpro/supported-control-surfaces-ctls718dd5b2/mac)

Scripts live under `~/Music/Audio Music Apps/MIDI Device Scripts` and `/Library/Audio/MIDI Device Scripts`.

On Apple silicon, third-party MIDI Device Plug-ins (binary MDPs) are not the general path. Lua MDS is.

### 1.4 Control surfaces / Mackie Control

**Tag: VERIFIED (Apple supports MCU-class surfaces). Virtualizing one as an agent bridge is EXPERIMENTAL until we pass evals.**

Apple documents control-surface modules and MIDI device scripts. An agent can impersonate a controller instead of driving the screen. That is the strategic in-Logic control path.

Apple: [Control surfaces supported](https://support.apple.com/guide/logicpro/supported-control-surfaces-ctls718dd5b2/mac) and the Control Surfaces Support Guide PDF linked from that page.

### 1.5 CoreMIDI / Core Audio

**Tag: VERIFIED as macOS APIs. Agent-grade use in Logic is TESTED only after harness evals.**

IAC buses, virtual MIDI ports, MMC, and note/CC streams are real. They do not give you project tree, region list, or mixer plugin inventory.

## 2. Workaround channels (outside-the-app)

Use these only as fallbacks. Never advertise them as a Logic API.

| Channel | What it is | Tag |
| --- | --- | --- |
| Accessibility (AX) | UI tree read/press | EXPERIMENTAL as a product contract. UI trees move every Logic release. |
| CGEvent / PostEvent | Synthetic clicks and keys | EXPERIMENTAL. Last-resort actuation. |
| AppleScript / System Events | App automation, not a Logic project dictionary | EXPERIMENTAL for session control. |
| MIDI key commands | Mapped key commands over MIDI | TESTED by incumbents; Logic 12.2+ dropped legacy plist import. |

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

1. In-Logic surfaces first: AU MIDI FX, Scripter helpers, Lua MDS / virtual MCU.
2. Harness that scores musical truth: note on the track, MIDI out of the AU, transport via MCU echo, bounce audio hash. Not `ax_live`.
3. MCP last, and only for channels the harness passed.
4. Open-source this map, then the AU brick, then the evals. Not the Ollama band stack.

## 5. What we will not say

- "Logic's plugin API is VST."
- "Scripter is Lua."
- "MIDI Device Scripts are JavaScript."
- "The Logic MCP is a first-party API."
- "Accessibility verified the region."

See [EVALS.md](EVALS.md) for the first ten fail-closed tests.
