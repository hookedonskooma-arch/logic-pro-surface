# logic-pro-surface

Honest Logic Pro agent surfaces, plus the harness that refuses to call Accessibility a public API.

This is not a clone of [MongLong0214/logic-pro-mcp](https://github.com/MongLong0214/logic-pro-mcp). That project already owns the outside-the-app MCP race. We live inside Logic: Audio Units, Scripter, MIDI Device Scripts, and a virtual control surface. MCP is a thin adapter over channels the harness has already passed.

Start here: [SURFACE.md](SURFACE.md).

Honesty rules: [docs/HONEST_CONTRACT.md](docs/HONEST_CONTRACT.md). Tonight vs later: [SHIP.md](SHIP.md).

Studio workforce memory is [studio/](studio/). Roles, honest MCP checkboxes, taste, project state, and tasks live there. That folder is a shared brain, not a Logic API and not a claim that we can mix. SURFACE.md is the channel map; this pointer does not rewrite it.

Spoken mouth (v0): macOS `say`, not MELEGI. See [studio/VOICE.md](studio/VOICE.md).

## Status tags

We never collapse these into "supported":

- **VERIFIED** — Apple documents it.
- **TESTED** — we or a cited project ran it against live Logic.
- **EXPERIMENTAL** — works sometimes, not a contract.
- **UNKNOWN** — we have not proved it.

## What ships first

1. Surface map (this repo).
2. AU MIDI FX brick (extracted from MELEGI).
3. Ten fail-closed evals that score musical truth, not AX receipts.
4. MCP adapter last.

Logic's native third-party plugin path is Audio Units, not VST.

## What is public tonight vs what needs a Mac

**Tonight (Linux-safe, this tree):** the surface map, the E01–E10 contract, the honest envelope, a `logic-probe` CLI that returns `uncertain` when Logic is not reachable, a compile-shaped AU MIDI Processor stub, fail-closed unit tests, and CI that only runs those tests.

**Not tonight:** live TESTED results against Logic Pro. This drop does **not** invent them.

**Needs macOS + Logic Pro 12.3 (desktop, one clean empty project):** E01–E07 and E10 musical truth, `nm` / pluginval on a real `.component` for E08, a render-thread allocator hook for E09, live E02 against the extracted MELEGI AU MIDI FX (see [docs/MELEGI-EXTRACTION.md](docs/MELEGI-EXTRACTION.md)), virtual MCU, then MCP last.

A green Linux CI run is not TESTED against Logic. Skip is not pass. AX receipts cannot be the pass bit.

## Probe

From the repo root:

```bash
PYTHONPATH=logic-probe python -m logic_probe mixer set-volume --track 3 --db -6
PYTHONPATH=logic-probe python -m logic_probe transport play
PYTHONPATH=logic-probe python -m logic_probe ax inspect-selected-track
```

JSON always includes `before`, `adapter_result`, `readback`, `verification`, and `status` in `{confirmed, uncertain, failed}`.

Without Logic, `status` is `uncertain`. The process exiting 0 only means an envelope was printed — that is adapter-level, not semantic success. `confirmed` requires independent MCU echo (`readback.method=mcu_feedback`). AX receipts cannot be the pass bit. Mixer `-6 dB` is an MCU fader, not MELEGI audio pass-through. See [docs/MCU.md](docs/MCU.md).

## Tests

```bash
PYTHONPATH=logic-probe python -m pytest tests -m "not live_logic"
```

Live-Logic tests (`pytest -m live_logic`) fail closed when Logic is absent. They do not skip-pass.

## Layout

- [SURFACE.md](SURFACE.md) — channel map with tags. Apple is highest authority.
- [EVALS.md](EVALS.md) — ten fail-closed evals.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — AU / MIDI / control-surface first, MCP last.
- [docs/CAPABILITY_MATRIX.md](docs/CAPABILITY_MATRIX.md) — every row has a status tag.
- `audio-unit/` — Apple-shaped MIDI FX stub (4-note phrase C3 E3 G3 C4).
- `audio-unit/melegi/` — extracted MELEGI JUCE AU MIDI FX only. Not TTS, not audio pass-through, not Ollama. See [docs/MELEGI-EXTRACTION.md](docs/MELEGI-EXTRACTION.md).
- `logic-probe/` — Python harness.
- `grok/` — bot prompt, source policy, promotion gates.

Scripter is JavaScript. MIDI Device Scripts are Lua. Do not bring Ollama, songs, or a VST-first path into this repo.
