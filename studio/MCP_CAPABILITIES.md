# MCP capabilities (reality)

Date: 2026-09-01

Checkboxes match the studio Mac **as inspected**. Unchecked means we do not have it. Do not advertise unchecked items. There is no documented public Logic API for project control.

## READ

- [ ] list tracks reliably
- [ ] plugin slots
- [ ] regions
- [ ] tempo from Logic API
- [ ] loudness metering
- [ ] spectral
- [ ] hear audio
- [x] control-surface pref blob exists (`com.apple.logic.pro.cs`; Logic Remote on iPad installed; Logic Control in catalog)
- [x] CoreMIDI ports can be listed via mido

AX is **not** a read capability we accept as truth.

## WRITE

- [x] MCU fader send over IAC `logic-probe-mcu-cmd` (adapter-level; send ≠ confirmed)
- [ ] MCU echo/readback (E06 UNKNOWN, `mcu_no_echo` 2026-09-01)
- [ ] create track
- [ ] insert plugins
- [ ] move regions

MELEGI is an installed `aumi` MIDI FX. It is not a mixer API.
