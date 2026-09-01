# Fine-tune

Date: 2026-09-01

Do not fine-tune first.

## DAW brain

Fine-tune the DAW brain only after hundreds of inspect → probe → `confirmed` / `uncertain` / `failed` examples. Adapter success is not a training label. Skip is not pass. AX receipts are not musical truth.

## Voice clone

Voice fine-tune (clone) only after we have a chosen TTS vendor **and** studio takes. v0 is macOS `say` (see [VOICE.md](VOICE.md)). There is no clone dataset yet.

## Dataset path

`studio/datasets/` — schema in [datasets/SCHEMA.md](datasets/SCHEMA.md). Runtime `*.jsonl` is gitignored. Do not commit songs or secrets.

## Log format (JSONL)

One object per line:

```json
{"ts":"2026-09-01T00:00:00+00:00","role":"logic-studio","user":"chris","said":"...","spoken":"...","probe_status":null,"evidence":"..."}
```

Fields: `ts`, `role`, `user`, `said`, `spoken`, `probe_status`, `evidence`.

`probe_status` is `confirmed` | `uncertain` | `failed`, or `null` when the line is speak-only (no probe).

Never log secrets. Never log songs, lyrics, or bounce audio.
