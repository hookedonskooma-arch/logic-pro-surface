# Voice (mouth)

Date: 2026-09-01

MELEGI is MIDI FX, not the mouth. The mouth is TTS.

## v0

macOS `say`. Voice: **Reed (English (US))**. If that voice is missing, **Samantha**. Offline only. Not a singing model. Not a voice clone.

Fluency = Logic vocabulary in the spoken text, not a model that sings or hears.

Implementation: `logic-probe/voz/mouth.py`. **One mouth, imported, never
re-implemented.** `scripts/speak.py` is a thin CLI over it and `gnomo.mouth` is
a thin companion wrapper. A test fails the build if any file outside `voz/`
invokes `say` directly - because "one mouth" as a convention regrew a second
one within three days (see [VOICE_TEARDOWN.md](VOICE_TEARDOWN.md) §1.1).

Driver: `python3 scripts/speak.py "..."`.

## Pronounce

| Token | Spoken as |
| --- | --- |
| AU | A U |
| AUv3 | A U v 3 |
| Scripter | Scripter |
| MCU | M C U |
| IAC | I A C |
| fader | fader |
| bus | bus |
| send | send |
| bounce | bounce |
| aumi | A U M I |

## Candidates beyond v0

Source-verified teardown of the options: [VOICE_TEARDOWN.md](VOICE_TEARDOWN.md).
Short version: `say` stays the floor; Piper is archived upstream and its heir is
GPL-3.0; Kokoro (Apache-2.0, weights included) is the only clean upgrade path;
Pipecat is the wrong altitude for a two-sentence mouth. Nothing is TESTED.

## Never

- Never claim MCP heard the mix.
- Never treat MELEGI as a mouth, mixer, or listener.
- Never pretend this layer can hear audio.
