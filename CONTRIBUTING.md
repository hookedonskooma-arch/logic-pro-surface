# Contributing

This repo would rather ship `UNKNOWN` than a lie.

## Before you write code

1. Read [SURFACE.md](SURFACE.md), [EVALS.md](EVALS.md), [docs/HONEST_CONTRACT.md](docs/HONEST_CONTRACT.md).
2. Apple documentation outranks community MCP repos. Community code is evidence, not spec.
3. Pick a status tag. Do not collapse VERIFIED / TESTED / EXPERIMENTAL / UNKNOWN into "supported".

## Hard rules

- Logic's native third-party plugin path is Audio Units, not VST.
- Scripter is JavaScript. MIDI Device Scripts are Lua. Do not swap them.
- Accessibility is not a public Logic API. AX receipts cannot be the pass bit.
- Sent command ≠ confirmed. Adapter success ≠ semantic success.
- Result envelope status is only `confirmed` | `uncertain` | `failed`.
- Never invent Logic state. Never mark TESTED without a cited live run against Logic.
- Skip is not pass. A skipped live eval stays UNKNOWN / fails closed.
- Do not add Ollama, songs, secrets, or home-directory dumps.
- Do not copy the MELEGI app stack (band / backend / web UI). Extract AU MIDI FX only, later.
- MCP last, and only over channels the harness has passed.
- This is not a clone of MongLong0214/logic-pro-mcp.

## Tests

Linux-safe tests must stay green without a Mac:

```bash
PYTHONPATH=logic-probe python -m pytest tests -m "not live_logic"
```

Live-Logic tests must fail closed when Logic Pro 12.3 is not reachable. Do not `pytest.skip` those into a pass.

## Pull requests

- Update [docs/CAPABILITY_MATRIX.md](docs/CAPABILITY_MATRIX.md) if you touch a capability. Every row needs a status tag.
- New actuation paths need a probe JSON envelope and an eval id.
- Real-time C++: no heap, I/O, locks, or Swift/ObjC in the render path.
