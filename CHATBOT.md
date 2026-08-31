# CHATBOT.md — a musically coherent chat bot, voice and text

The same rule that governs [SURFACE.md](SURFACE.md) governs this: we do not
collapse "I know" and "I assume" into one word. A chat bot that answers a chord
question without knowing the key is not helpful, it is confidently wrong, and
in a session that costs you a take.

Status tags carry the meaning they carry in the README: **VERIFIED**,
**TESTED**, **EXPERIMENTAL**, **UNKNOWN**.

## The coherence contract

Musical coherence here means one specific, testable thing, not a vibe:

1. **State is single-sourced.** Key, mode, tempo and meter live in one object,
   `chatbot.state.MusicalState`. Nothing else stores them.
2. **Every answer is derived at answer time.** No answer is carried forward from
   earlier in the conversation. Change the key and the same chord gets a
   different verdict on the next turn — this is a test, not a hope
   (`test_answers_are_derived_from_current_state_not_history`).
3. **Unset is UNKNOWN, and UNKNOWN fails closed.** With no key set, "is Bbmaj7
   in key?" returns a request for the key. It does not pick C major and answer.
4. **Outside is named, not scolded.** A chord that leaves the key is reported
   with the exact pitch that leaves it, and with the parallel mode it *is*
   diatonic to, nearest neighbour first. `E7` in A minor is harmonic minor, not
   "wrong" and not "A major".
5. **Spelling follows the key.** Flat-side alterations are spelled flat even in
   a sharp key: bVII of C is Bb, never A#.
6. **Leniency is confined to one module.** `chatbot.language` is the only place
   allowed to guess what you meant. Everything downstream raises on input it
   cannot represent.

## What ships in this branch

| Piece | File | Status |
| --- | --- | --- |
| Pitch-class theory, scales, chords, roman numerals | `chatbot/theory.py` | **TESTED** — unit tests |
| Session state and coherence verdicts | `chatbot/state.py` | **TESTED** |
| Spoken/typed English → theory input | `chatbot/language.py` | **TESTED** |
| Conversation routing | `chatbot/bot.py` | **TESTED** |
| Local STT/TTS adapters | `chatbot/voice.py` | **UNKNOWN** — probes correctly on a box with no speech stack; not yet run against live audio |
| CLI, text and voice | `chatbot/cli.py` | **EXPERIMENTAL** — text path exercised, voice path unproven |

## Running it

```
python3 -m chatbot                       # text
python3 -m chatbot --probe               # which local speech backends exist
python3 -m chatbot --voice --speak       # local speech in and out
python3 -m unittest discover -s tests
```

No dependencies for the text path. Python 3.11+ (PEP 604 unions at runtime).

## Voice: local only

Nothing in `chatbot/voice.py` touches the network. Every take stays on the
machine — the studio is often offline and a vocal idea is not something to
upload by accident.

Speech to text, first available wins:

1. **whisper.cpp** — `WHISPER_CPP_BIN` (or `whisper-cli` on PATH) plus
   `WHISPER_CPP_MODEL` pointing at a ggml model.
2. **faster-whisper** — `pip install faster-whisper`, CPU int8, model from
   `FASTER_WHISPER_MODEL` (default `base.en`).

Text to speech, first available wins:

1. **Piper** — `PIPER_BIN` + `PIPER_MODEL` (.onnx voice), rendered through
   `afplay`/`aplay`/`play`.
2. **macOS `say`** — present on any machine that can run Logic. `SAY_VOICE`
   picks a voice.

Capture is 16 kHz mono, which is what Whisper wants, via `sounddevice` if
installed, else `sox`/`rec`. A missing backend is reported as MISSING and the
text path keeps working; it is never a crash.

Replies come in two forms per turn: `Turn.reply` for the screen (aligned,
multi-line) and `Turn.spoken` for the speaker (one line, no `OUT`/`ok` column
markers, no newlines — that is a test too).

## What this does *not* do yet — UNKNOWN

Said plainly so nobody reads a roadmap as a feature list:

- **It does not read your Logic session.** Key, tempo and meter are what you
  tell it, not what the project window says. Wiring these to the real session
  is exactly the work SURFACE.md maps (Scripter, MIDI Device Scripts, an AU MIDI
  FX brick), and none of it is done.
- **It does not generate parts.** RIFF/PORADO/TECLA are taste layers; this is
  the theory floor they would have to stand on.
- **It has no voice-activity detection.** `--voice` records a fixed window per
  take. Push-to-talk, not always-on.
- **It has no notion of harmonic rhythm, voice leading, or form.** A
  progression is checked chord by chord against the key, nothing more.
- **The voice path has never been run against live audio in CI**, because CI
  has no microphone. Treat the probe output, not this document, as the truth
  about your machine.

## Evals

The fail-closed cases in `tests/test_chatbot.py` are the same shape as the ones
in [EVALS.md](EVALS.md): they score musical truth, and half of them score the
bot's willingness to say it does not know.
