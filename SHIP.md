# SHIP — tonight vs later

One page. Not a claim that the bridge works.

## Tonight (this v0 drop)

- Public map: [SURFACE.md](SURFACE.md) (unchanged from the public repo, plus a pointer at the honest contract).
- Public eval contract: [EVALS.md](EVALS.md).
- MIT license, contributing rules, architecture, capability matrix, honest contract.
- `logic-probe` CLI. Without Logic: `status=uncertain`. Never fakes `confirmed`.
- AU MIDI Processor **stub** (Swift `AUAudioUnit` → Objective-C++ adapter → C++ kernel). Phrase C3 E3 G3 C4 is coded, not live-tested.
- Linux-safe fail-closed tests: envelope schema, E04 (Scripter is not a project API), E08 (no VST format), E09 (render-path scan).
- GitHub Actions: those tests only.
- Grok bot files: system prompt, source policy, promotion gates.

## Not in this drop

- The MELEGI plugin source (`newmelegi/plugin/`). Stub shipped because that source is not in this drop. Extract later; see [docs/MELEGI-EXTRACTION.md](docs/MELEGI-EXTRACTION.md).
- Ollama, band stack, backend, ai-stack, vibe-producer, beatstore.
- Any live Logic TESTED numbers. None were run for this v0.
- MCP server. MCP is last.

## Later (Mac + Logic Pro 12.3)

| When | What | Status until then |
| --- | --- | --- |
| Extract | AU MIDI FX only from MELEGI. `FORMATS AU`, `IS_MIDI_EFFECT TRUE`, not a synth. | UNKNOWN |
| E01 | CoreMIDI note on a software instrument | UNKNOWN |
| E02 | AU MIDI FX 4-note phrase hash | UNKNOWN |
| E03 | Scripter JS +12 transpose | UNKNOWN |
| E04 live | Confirm Scripter cannot rename/create tracks inside Logic | Linux unit test exists; live remains UNKNOWN |
| E05 / E06 | Virtual MCU transport + fader echo | E05 still stub. E06 implemented; TESTED only if live envelope is `confirmed` |
| E07 | Lua MDS mapped button | UNKNOWN |
| E08 live | `nm` / pluginval on a `.component` | Static scan exists; binary UNKNOWN |
| E09 live | allocator hook / TSan on the render thread | Static scan exists; live UNKNOWN |
| E10 | Bounce RMS / onset fingerprint | UNKNOWN |
| After harness passes | Thin MCP adapter over those channels only | not started |

## How to run what exists tonight

```bash
PYTHONPATH=logic-probe python -m pytest tests -m "not live_logic"
PYTHONPATH=logic-probe python -m logic_probe mixer set-volume --track 3 --db -6
```
