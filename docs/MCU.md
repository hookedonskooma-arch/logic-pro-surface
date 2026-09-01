# Virtual MCU / IAC

Date: 2026-09-01
Studio host: Logic Pro **12.2** (EVALS.md target is 12.3; do not pretend this is 12.3).
Status: EXPERIMENTAL. Apple documents that Logic hosts MCU-class surfaces.
Apple does not publish the MCU byte protocol, and Apple does not document a
software virtual MCU. E06 is TESTED only when `mixer set-volume` returns
`confirmed` with `readback.method=mcu_feedback`.

MELEGI is not this path. MELEGI stays `aumi` MIDI FX. Mixer dB is a fader.

## What this machine had (inspected, not edited)

`~/Library/Preferences/com.apple.logic.pro.cs` is a little-endian FORM/SSCF
blob, not a plist. `plutil` cannot parse it.

Observed in the blob:

- Module **catalog** includes Logic Control, HUI, iControl, Logic Remote, TouchOSC, …
- **Installed** hints: Logic Remote on iPad (`Control Surface: iPad`, `Remote (iPad Pro11)`)
- MIDI port names in the blob: `SSL 2+`, `Logic Pro Virtual In`, `Logic Pro Virtual Out`
- No IAC strings
- `com.apple.logic10.plist` exists (binary plist); not used as a CS assignment store

CoreMIDI at probe time (before IAC enable):

- Online: `Logic Pro Virtual In` / `Logic Pro Virtual Out` only
- Present but **offline**: IAC Driver (Bus 1), SSL 2+ MIDI entity

Those Logic Pro Virtual ports are sequencer endpoints. Sending MCU pitch-bend
there would pitch-bend a software instrument. The probe must not use them as MCU.

SSL 2+ MIDI is left offline. Do not flip MELEGI. Do not Rebuild Defaults.

## What the probe does

1. If `LOGIC_PROBE_FORCE_OFFLINE=1` or Logic is not running: `uncertain`.
2. Bring IAC Driver online (`kMIDIPropertyOffline=0`). Idempotent.
3. Add IAC entities `logic-probe-mcu-cmd` and `logic-probe-mcu-fb` if missing.
   Does not rename `Bus 1`.
4. Send MCU host-connection query + fader pitch-bend on **cmd**.
5. Listen for motor/echo pitch-bend on **fb**.
6. Envelope:
   - `confirmed` — echo matched (independent bus, not AX)
   - `failed` — MCU traffic came back, value outside tolerance
   - `uncertain` — no MCU echo (`mcu_no_echo`) or ports missing

Two IAC buses are required so our send is not our readback. Same-bus loopback
is not independent evidence.

## Operator step this process cannot click

Accessibility UI scripting of Logic is blocked here. Logic will not treat IAC
as Mackie Control until a surface is installed:

Logic Pro > Control Surfaces > Setup > New > Install > **Mackie Control**
(or Logic Control).

- Input port: `IAC Driver logic-probe-mcu-cmd`
- Output port: `IAC Driver logic-probe-mcu-fb`

Do **not** choose Rebuild Defaults. That would wipe the iPad Logic Remote
assignment.

Then:

```bash
PYTHONPATH=logic-probe python3 -m logic_probe mixer set-volume --track 3 --db -6
```

`status=confirmed` with `readback.method=mcu_feedback` is E06. Anything else
stays UNKNOWN. Skip is not pass.
