# Current tasks

Date: 2026-09-12

## SHIPPED (Gates A + B, live-verified)

- Body verbs + ears + composition seam v0.1/v0.2 on main (PR #1, `3089291`)
- gnomo-setup.sh + LaunchAgent on main (PR #2, `cd6652b`) — setup exit 0,
  LaunchAgent running, keep-alive proven twice (app kill → resurrect)
- Suite 173 passed, 1 skipped; selftest exit 0

## NOW — Gate C: the desk test (Chris, one reboot)

The machine half is staged. The reboot is yours:

1. Save your work, log out and back in (or reboot).
2. The gnome should greet you unaided — LaunchAgent `studio.gnomo.companion`.
3. The mic/speech grant should SURVIVE the reboot (same signature). If a
   dialog reappears, click Allow and tell me — that is a real finding
   (ad-hoc signature drift), not a failure to hide.
4. Speak "next" out loud → it answers → a ledger row lands:
   `tail -2 studio/datasets/decisions.jsonl`

Say the word after reboot and I'll verify the evidence side (launchctl state,
ledger row, window presence).

## NEXT — E02/E12: the composition seam, Logic half

Machine half is done (`gnomo play --out <port> --go` sends, capture hash is
the pass bit). Logic-side hands (5 minutes):

1. Scratch software-instrument track (never the only project)
2. MELEGI AU MIDI FX (aumi) on it — input-monitor ON
3. Ports: `PYTHONPATH=logic-probe python3 -c "import mido; print(mido.get_output_names())"`
4. `PYTHONPATH=logic-probe python3 -m gnomo play --file studio/plans/shoegaze8.json --out "IAC Driver Bus 1" --go`
5. Pass bit = capture hash match AND you heard the instrument. Capture alone
   is not a hearing.

## LATER (earned)

- v0.3 bass → v0.4 arrangement → v0.5 AU selection → v0.6 AU parameters
- Kokoro mouth; session analysis + mixing; MCP adapter LAST

## DO NOT TOUCH

- MELEGI audio buses (aumi MIDI FX only — Decision 001)
- iPad Logic Remote assignment
- Ollama band stack