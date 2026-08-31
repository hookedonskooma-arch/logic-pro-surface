# Honest contract

Ten rules. The system under test is the source of truth. The bot is not.

1. **A sent command is not a confirmed state change.** MIDI bytes leaving the process, a CGEvent post, or an AX press only prove actuation was attempted.

2. **Adapter success is not semantic success.** `adapter_result.success` may be true while Logic did nothing. Do not promote that to `confirmed`.

3. **The only semantic statuses are `confirmed`, `uncertain`, and `failed`.** Do not return `success`, `ok`, or `unverified-but-fine`. Process exit 0 means the envelope was printed, nothing more.

4. **`confirmed` requires independent evidence.** MCU echo, CoreMIDI capture, SMF / Event List, bounce fingerprint, or another path that is not the same surface you wrote. Same-surface AX readback is a receipt, not musical truth.

5. **If verification cannot be performed, return `uncertain`.** Missing Logic, missing permissions, missing readback, or a stub channel are `uncertain`, not `confirmed`. Skip is not pass.

6. **Never invent Logic state.** Do not fill `before` / `readback` with guessed dB, track names, or transport flags. Use `null` and say why.

7. **Never claim VST is Logic's native plug-in format.** Audio Units (AU / AUv3) only. `FORMATS AU`. MIDI FX is `kAudioUnitType_MIDIProcessor`, not a synth and not VST3.

8. **Destructive work is fail-closed.** If an operation cannot be verified or rolled back, do not execute it automatically. Checkpoint first. Never test against a user's only project.

9. **Every capability has an explicit status tag** (VERIFIED / TESTED / EXPERIMENTAL / UNKNOWN) in [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md). Community MCP repos do not upgrade a row to VERIFIED. Apple docs do not upgrade a row to TESTED.

10. **Never hide the channel.** Logs and envelopes name MCU, CoreMIDI, Scripter, MDS, AX, CGEvent, AppleScript, or OSC. Do not advertise Accessibility, CGEvent, or AppleScript as a Logic project API.

Related: [SURFACE.md](../SURFACE.md), [EVALS.md](../EVALS.md), [ARCHITECTURE.md](ARCHITECTURE.md).
