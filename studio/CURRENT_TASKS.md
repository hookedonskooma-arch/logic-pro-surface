# Current tasks

Date: 2026-09-12

## NOW — composition v0.1 seam (the doc's first vertical slice)

Machine half is DONE and tested (commits 2b0413c, 5dbecec, c218c47):

```bash
# compile (tier 0, never sends):
PYTHONPATH=logic-probe python3 -m gnomo plan --file studio/plans/shoegaze8.json --out /tmp/shoegaze8.mid
# play (tier 1, sends only with --go):
PYTHONPATH=logic-probe python3 -m gnomo play --file studio/plans/shoegaze8.json --out "<port>" --go
```

Chris, the hands half (one Logic window, five minutes):

1. Create a scratch software-instrument track (never the only project).
2. Insert the MELEGI AU MIDI FX (aumi) on it — input-monitor the track ON.
3. Find the port names: `PYTHONPATH=logic-probe python3 -c "import mido; print(mido.get_output_names())"`
4. Play the phrase: `PYTHONPATH=logic-probe python3 -m gnomo play --file studio/plans/shoegaze8.json --out "IAC Driver Bus 1" --go`
   (or whichever output reaches Logic's input; IAC Bus 1 → Logic record-armed input is the default route).
5. E02/E12 pass bits: CoreMIDI capture hash matches (`readback.method=coremidi_capture`) AND you heard the instrument.
   Capture alone is not a hearing; your ears are the second half of the pass bit.

## NEXT (unchanged)

Re-run E06 after the seam is live:

```bash
PYTHONPATH=logic-probe python3 -m logic_probe mixer set-volume --track 3 --db -6
```

E06 is TESTED only on `status=confirmed` with `readback.method=mcu_feedback`.

## LATER

- v0.2 melody layer on MusicPlan (composition ladder)
- v0.3 bass, v0.4 arrangement, v0.5 AU selection, v0.6 AU parameters
- Kokoro mouth; session analysis + mixing assistance; MCP adapter LAST

## DO NOT TOUCH

- MELEGI audio buses (aumi MIDI FX only — Decision 001)
- iPad Logic Remote assignment
- Ollama band stack