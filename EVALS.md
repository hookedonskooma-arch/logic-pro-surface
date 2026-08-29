# First ten fail-closed evals

These do not pass because an Accessibility node flipped. They pass when Logic's musical state is independently true.

Host: macOS, Logic Pro 12.3 desktop, one clean empty project. Fail closed on UNKNOWN. Skip is not pass.

| ID | Surface | Pass condition | Forbidden evidence |
| --- | --- | --- | --- |
| E01 | CoreMIDI → software instrument | Send NoteOn C3 / NoteOff. A MIDI region or live input monitor shows that note at that time. | AX "key highlighted" |
| E02 | AU MIDI FX out | MELEGI (or successor) AU on a MIDI FX slot emits a known 4-note phrase to the instrument below. Phrase hash matches fixture. | Plugin window opened |
| E03 | Scripter JS | `HandleMIDI` transposes +12. Incoming C3 becomes C4 on the instrument track. | Script editor console text |
| E04 | Scripter is not a project API | Script cannot rename the project or create a track. Attempt must fail. | |
| E05 | Virtual MCU transport | Play / stop via Mackie Control. Transport is playing, then stopped, via MCU echo or CoreMIDI MMC, not AX. | Clicking the play button |
| E06 | MCU fader | Set track 1 volume to a known MCU value. Readback from MCU echo matches within tolerance. | AX fader pixel |
| E07 | Lua MDS | Load our device script. One mapped button fires a documented key command (e.g. record). | Manual MIDI Learn leftover |
| E08 | No VST path | Build of the AU brick with `FORMATS AU` only. `nm` / pluginval shows AU component, no VST3. | |
| E09 | Realtime safety | AU render callback allocates 0 bytes and takes no locks under a thread sanitizer / custom allocator hook. Fail if malloc fires. | |
| E10 | Bounce truth | After E01+E02, bounce audio. RMS / onset fingerprint matches fixture. | Screenshot of the bounce dialog |

MongLong-style `logic://tracks` `source:"ax_live"` is allowed as a *secondary* annotation. It cannot be the pass bit.

Implementation comes after the AU brick is extracted. This file is the contract.
