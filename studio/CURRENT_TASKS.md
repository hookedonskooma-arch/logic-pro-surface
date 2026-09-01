# Current tasks

Date: 2026-09-01

## NOW

Chris: assign Mackie Control in Logic Pro > Control Surfaces > Setup.

- Input: IAC Driver `logic-probe-mcu-cmd`
- Output: IAC Driver `logic-probe-mcu-fb`
- Do **not** Rebuild Defaults (would wipe iPad Logic Remote).

## NEXT

Re-run:

```bash
PYTHONPATH=logic-probe python3 -m logic_probe mixer set-volume --track 3 --db -6
```

E06 is TESTED only on `status=confirmed` with `readback.method=mcu_feedback`.

## LATER

- MELEGI AU MIDI FX extract (not the app stack)
- E01–E10 live against Logic

## DO NOT TOUCH

- MELEGI audio buses
- iPad Logic Remote assignment
- Ollama band stack
