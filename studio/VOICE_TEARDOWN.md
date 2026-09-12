# Mouth teardown

Date: 2026-09-12
Method: read the source, not the marketing.
Question: what should GNOMO's mouth become after `say`?

Companion spec: [GNOMO.md](GNOMO.md). Current mouth: [VOICE.md](VOICE.md).
Source rules: [../grok/SOURCE_POLICY.md](../grok/SOURCE_POLICY.md).

## What was actually verified

Honesty about the honesty check, since this teardown is itself evidence:

| Target | How it was read | Tag |
| --- | --- | --- |
| `chatbot/voice.py` on `claude/musical-chatbot-voice-text-1fqugj` | **full source, every class** | VERIFIED |
| rhasspy/piper archive state | repository page, archive notice quoted | VERIFIED |
| OHF-Voice/piper1-gpl license | repository page | VERIFIED |
| hexgrad/kokoro license, deps, hardware | repository page + README | VERIFIED (page), source tree UNREAD |
| pipecat-ai/pipecat license, architecture, Python floor | repository page + README | VERIFIED (page), source tree UNREAD |

The SURFACE.md incumbent teardown read `Channels/` and ADRs. This one did not
do that for Pipecat or Kokoro. Landing pages are better than blog posts and
worse than code. **Nothing below is TESTED — no candidate has been run against
this repo on a Mac.**

## Matrix

| Candidate | License | Upstream alive | Offline | Invocation | Verdict |
| --- | --- | --- | --- | --- | --- |
| macOS `say` (current v0) | Apple | yes | yes | `subprocess` | Keep as the floor |
| Kokoro (hexgrad) | Apache-2.0, **weights too** | yes | yes | Python package (`pip install kokoro`) | Only clean upgrade path |
| Piper (rhasspy) | MIT | **ARCHIVED 2025-10-06** | yes | CLI binary | Dead end |
| Piper (OHF-Voice/piper1-gpl) | **GPL-3.0** | yes (successor) | yes | CLI binary | License question first |
| Pipecat | BSD-2-Clause | yes | yes (with local services) | orchestration framework | Wrong altitude |

## 1. Our own chatbot branch — the finding that matters

**Tag: VERIFIED. Full read of `chatbot/voice.py` (205 lines) on
`claude/musical-chatbot-voice-text-1fqugj`, 2026-09-12.**

This is the only target read completely, and it is the only one that is ours.

### 1.1 It is a second mouth

`MacSaySpeaker.say()` is four lines and calls `say` directly:

```python
cmd = [self.binary]
if self.voice:
    cmd += ["-v", self.voice]
subprocess.run(cmd + [text], check=False, timeout=120)
```

`grep` for `speak.py` across `chatbot/` returns **nothing**. So this path
loses, provably, everything `scripts/speak.py` does:

- **The lexicon.** [VOICE.md](VOICE.md) maps `AU`→"A U", `MCU`→"M C U",
  `IAC`→"I A C", `aumi`→"A U M I". Without it the mouth says "aw", "mcyoo"
  and "ow-mee". Fluency in this repo is defined as *Logic vocabulary in the
  spoken text*. This path is not fluent.
- **The secret filter.** `speak.py` refuses to log a line matching `api_key`,
  `token=`, `bearer `, `sk-`, `-----begin`, `password`. This path has no such
  check.
- **The log.** No `spoken.jsonl` record, so nothing spoken here is auditable.
- **The pinned voice.** VOICE.md pins Reed, then Samantha. This path reads
  `SAY_VOICE` with **no default**, so it uses whatever the system voice is.

This is not a style disagreement. It is the six-voices problem regrown in
code three days after Decision 004 cut it to one.

### 1.2 Its neural path targets a dead upstream

`PiperSpeaker` shells out to a `piper` binary. `rhasspy/piper` was
**archived by its owner on 2025-10-06 and is read-only**. The branch is
built on software that is no longer developed.

### 1.3 Its ears are not our forbidden ears

`WhisperCppRecognizer` and `FasterWhisperRecognizer` transcribe **speech**.
That is not metering audio, and it is not judging a mix.

GNOMO's tier-3 rule cannot currently tell those apart — it refuses on
`hear|listen|audition|ears`, deliberately widened so that "check how the
guitar sounds" cannot sneak into tier 0. Transcribing Chris talking would
trip the same rule.

**This is the real merge blocker, and it is a design decision, not a bug.**
Before these branches meet, the ladder needs the distinction written in:

- Hearing **the human** (speech → text): legitimate, and nothing to do with
  musical truth.
- Hearing **the mix** (audio → judgement): VERIFIED absent, forever.

Loosen the rule without drawing that line and the no-ears guarantee dies
quietly, which is the exact failure this repo exists to prevent.

## 2. Kokoro — the only clean upgrade path

**Tag: VERIFIED from the repository page. Source tree UNREAD. Not run.**

- Apache-2.0, **and the weights are Apache-2.0 too**. Clean against our MIT.
  Model licensing is where most "open" TTS gets you; this one does not.
- 82M parameters. CPU by default; Apple Silicon GPU via
  `PYTORCH_ENABLE_MPS_FALLBACK=1`.
- Installed as a **Python package** (`pip install kokoro`), driven through a
  `KPipeline` object — *not* a CLI binary. That matters: our current mouth is
  a subprocess call, so this is a different integration shape.
- Dependencies: `soundfile`, `misaki` (G2P), and **espeak-ng** for
  out-of-distribution English and non-English. Plus PyTorch. That is a real
  weight increase over `say`, which is already on every Mac that runs Logic.
- Supports Spanish among others — relevant to bilingual vocal work, though
  a companion that *speaks Logic vocabulary* is not a singing model, and
  this changes nothing about that.

**Verdict:** the right target if and when the mouth graduates. Not urgent.

## 3. Piper — dead, and its heir changes the license

**Tag: VERIFIED (archive notice quoted).**

`rhasspy/piper`: *"This repository was archived by the owner on Oct 6, 2025.
It is now read-only."* MIT. Development moved to `OHF-Voice/piper1-gpl`,
which is **GPL-3.0**.

Our repo is MIT. Our code invokes a TTS binary as a **subprocess**, which is
not linking — but whether that distinction holds for any particular
distribution is a legal question, not an engineering one.

**Tag: UNKNOWN. This repo does not render legal opinions.** If a Piper-family
binary is ever shipped or bundled rather than invoked from a user's own
install, ask a human who does this for a living. Kokoro's Apache-2.0 makes
the question disappear, which is itself an argument for Kokoro.

## 4. Pipecat — right tool, wrong altitude

**Tag: VERIFIED from the repository page. Source tree UNREAD.**

- BSD-2-Clause. Permissive, fine against MIT.
- Composable pipeline of transports and AI services; local operation is
  genuinely possible (Ollama, Whisper) — the cloud services are optional
  integrations, not a requirement.
- **Minimum Python 3.11.** Our `pyproject.toml` says `requires-python =
  ">=3.10"`. Adopting it raises our floor.

Pipecat orchestrates realtime multimodal conversation: transports, turn
handling, interruption, streaming. GNOMO speaks **one line, two sentences,
then stops**. Using a realtime pipeline framework for that is carrying a PA
system to say one sentence.

**Verdict: do not adopt.** Revisit only if the companion ever becomes a
live back-and-forth voice loop, which is not on any roadmap here.

## Recommendation

1. **Do nothing about TTS yet.** `say` is a working floor, is on every Mac
   that runs Logic, and has the lexicon and the secret filter. No candidate
   beats it on the thing GNOMO actually needs, which is saying one correct
   Logic sentence.
2. **Fix the second mouth before merging the chatbot branch.** Route
   `MacSaySpeaker` through `scripts/speak.py` so there is one mouth, one
   lexicon, one log. This is a small change and it protects Decision 004.
3. **Write the hearing distinction into the ladder before the branches
   meet** — hearing the human is not hearing the mix. Doing it after a merge
   means doing it under pressure, which is how guarantees get loosened.
4. **If the mouth ever graduates, it graduates to Kokoro.** Apache-2.0
   including weights, offline, Apple Silicon capable. Not Piper.

Nothing here is TESTED. Promoting any row requires running it on the studio
Mac and citing the run.
