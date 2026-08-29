# logic-pro-surface

Honest Logic Pro agent surfaces, plus the harness that refuses to call Accessibility a public API.

This is not a clone of [MongLong0214/logic-pro-mcp](https://github.com/MongLong0214/logic-pro-mcp). That project already owns the outside-the-app MCP race. We live inside Logic: Audio Units, Scripter, MIDI Device Scripts, and a virtual control surface. MCP is a thin adapter over channels the harness has already passed.

Start here: [SURFACE.md](SURFACE.md).

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
