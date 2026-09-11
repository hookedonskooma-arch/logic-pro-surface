# Project state

Date: 2026-09-11
LAST VERIFIED: 2026-09-11

- DAW: Logic Pro **12.2** on the studio Mac (not 12.3; do not pretend).
- Open project: `Untitled 34 - Tracks`, one audio track (`Audio 1`). Read live, not assumed.
- This repo: platform (surfaces, probe, AU stub). Not mixing a named song here.

## Control surface — TESTED 2026-09-11

- Mackie Control **is** installed and assigned: Logic INPUT = `IAC Driver logic-probe-mcu-cmd`,
  Logic OUTPUT = `IAC Driver logic-probe-mcu-fb`. Read back live from the Control Surface
  Setup window, not from the cs blob.
- E06 echo **passes** and repeats: `mixer set-volume --track 1 --db -6` returns
  `confirmed` with `readback.method=mcu_feedback`, echo within ~0.03 dB.
- TESTED, not VERIFIED: the MCU byte protocol is not an Apple spec.
- Baby HUI was removed; the earlier `mcu_echo_mismatch` was a HUI-module device
  sitting on the MCU ports, plus Logic INPUT and OUTPUT both pointed at `-fb`.
- Logic only echoes a fader on CHANGE. Re-sending the current value is a no-op and
  returns no echo; the probe now nudges to disambiguate that from a dead surface.

## Known blockers

- Cursor GitHub cloud agents are unauthenticated.

Do not invent a song title or a mixer state.
