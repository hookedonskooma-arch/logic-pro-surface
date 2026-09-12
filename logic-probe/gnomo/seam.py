"""The composition seam: validated plan -> compiled MIDI -> CoreMIDI out.

Machine half of composition v0.1 (studio/FAILURE_DRIVEN_ARCHITECTURE.md
section 12). Honest boundaries, all enforced here:

- The send path proves notes were SENT. That is adapter success, not
  semantic success (HONEST_CONTRACT rule 2).
- The only machine pass bit is an independent CoreMIDI capture of what
  came back, whose phrase hash matches the compiled fixture. Capture on
  the same port as the send is loopback — same surface, not independent
  — and is refused as a pass bit (rule 4).
- Even with capture matched, the envelope notes that the human receipt
  (Chris hears the instrument) is still required before E02/E12 is
  TESTED. A capture is evidence, not a hearing.
- Offline (LOGIC_PROBE_FORCE_OFFLINE=1) or missing mido: uncertain,
  nothing opens, nothing sends. Skip is not pass (rule 5).
- Nothing here writes into a Logic project. Region placement stays a
  human hand (consolidate). This module promises audible MIDI, not regions.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from logic_probe.envelope import confirmed, failed, uncertain
from logic_probe.host import detect

PROBE_ID = "composition_seam"


def _mido():
    try:
        import mido  # type: ignore
    except ImportError as exc:
        raise SeamError("mido_not_installed") from exc
    return mido


class SeamError(RuntimeError):
    pass


def port_names() -> dict[str, Any]:
    """Snapshot of available CoreMIDI ports (empty on failure, never a guess)."""
    try:
        mido = _mido()
    except SeamError:
        return {"inputs": [], "outputs": [], "error": "mido_not_installed"}
    try:
        return {
            "inputs": list(mido.get_input_names()),
            "outputs": list(mido.get_output_names()),
        }
    except Exception as exc:  # noqa: BLE001
        return {"inputs": [], "outputs": [], "error": f"port_list_failed:{exc}"}


def _schedule_events(compiled: dict[str, Any]) -> list[tuple[float, bytes]]:
    """Compiled bars -> [(absolute_seconds, raw_bytes)] with tempo math.

    Deterministic timing from the plan's own tempo; NoteOff exactly on the
    bar line. Returns raw MIDI bytes so the send path stays trivially
    testable and port-independent.
    """
    ppq = compiled["ppq"]
    seconds_per_tick = 60.0 / (compiled["tempo"] * ppq)
    events: list[tuple[float, bytes]] = []
    for bar in compiled["bars"]:
        start_s = bar["start_tick"] * seconds_per_tick
        end_s = bar["end_tick"] * seconds_per_tick
        for entry in bar["notes"]:
            events.append((start_s, bytes([0x90, entry["note"], entry["velocity"]])))
            events.append((end_s, bytes([0x80, entry["note"], 0x40])))
    events.sort(key=lambda item: (item[0], item[1]))
    return events


def _phrase_hash_of_captured(messages: list[Any], ppq: int, tempo: int) -> str | None:
    """Hash captured NoteOn/NoteOff pairs into the compiled phrase-hash shape.

    Reconstructs start ticks from message times (seconds since capture
    opened) using the plan's tempo math — the inverse of _schedule_events —
    so the hash is comparable with midi_compiler.phrase_hash. Returns None
    when the capture holds no complete note pairs.
    """
    import hashlib

    ticks_per_second = tempo * ppq / 60.0
    ons: dict[int, tuple[float, int]] = {}
    parts: list[tuple[int, int, int]] = []
    for msg in messages:
        if msg.type == "note_on" and msg.velocity > 0:
            ons.setdefault(msg.note, (getattr(msg, "time", 0.0), msg.velocity))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            start = ons.pop(msg.note, None)
            if start is None:
                continue
            parts.append((round(start[0] * ticks_per_second), msg.note, start[1]))
    if not parts:
        return None
    parts.sort()
    blob = "|".join(f"{t}:{n}:{v}" for t, n, v in parts) + f"|ppq{ppq}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def play_plan(
    compiled: dict[str, Any],
    *,
    out_port: str,
    capture_port: str | None = None,
    force_offline: bool | None = None,
) -> dict[str, Any]:
    """Play the compiled phrase live. Returns one honest envelope.

    - force_offline / no mido / missing port -> uncertain, nothing sent
    - sent with no capture (or no capture requested) -> uncertain
      (adapter success only)
    - capture on the same port as send -> refused (loopback is not
      independent); uncertain with the refusal named
    - capture hash == compiled hash -> confirmed via coremidi_capture,
      with notes stating the human receipt is still outstanding
    - capture mismatch -> failed (independent evidence contradicts)
    """
    host = detect()
    requested = {
        "operation": "composition.play_plan",
        "phrase_hash": compiled["phrase_hash"],
        "bars": compiled["length_bars"],
        "tempo": compiled["tempo"],
        "out_port": out_port,
        "capture_port": capture_port,
    }
    versions = {
        "logic_version": host.get("logic_version"),
        "macos_version": host.get("macos_version"),
    }
    base_notes = [
        "sent notes are adapter success, not semantic success",
        "region placement is a human hand (consolidate); this seam does not write regions",
        "MELEGI stays aumi MIDI FX on the target track (hands, per CURRENT_TASKS)",
    ]

    offline = force_offline
    if offline is None:
        import os

        offline = bool(os.environ.get("LOGIC_PROBE_FORCE_OFFLINE"))
    if offline:
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason="forced_offline",
            extra_notes=["skip is not pass; nothing was opened or sent"],
            **versions,
        )

    if capture_port is not None and capture_port == out_port:
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason="capture_port_equals_send_port_loopback_refused",
            extra_notes=[
                "same-surface capture is not independent evidence (HONEST_CONTRACT rule 4)"
            ],
            **versions,
        )

    try:
        mido = _mido()
    except SeamError as exc:
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason=str(exc),
            **versions,
        )

    ports = port_names()
    if out_port not in (ports.get("outputs") or []):
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason=f"out_port_not_found:{out_port}",
            extra_notes=[f"outputs={ports.get('outputs')}"],
            **versions,
        )

    # ---- adapter: open, schedule, send -----------------------------------
    captured: list[Any] = []
    cap_in = None
    out = None
    try:
        out = mido.open_output(out_port)
        if capture_port is not None:
            if capture_port not in (ports.get("inputs") or []):
                return uncertain(
                    probe_id=PROBE_ID,
                    channel="coremidi",
                    operation="composition.play_plan",
                    requested=requested,
                    reason=f"capture_port_not_found:{capture_port}",
                    **versions,
                )
            cap_in = mido.open_input(capture_port)

        events = _schedule_events(compiled)
        t0 = time.perf_counter()
        for when, raw in events:
            delay = when - (time.perf_counter() - t0)
            if delay > 0:
                time.sleep(delay)
            out.send(mido.Message.from_bytes(raw))
            if cap_in is not None:
                captured.extend(cap_in.iter_pending())
        # drain the tail (final note-offs + capture catch-up)
        time.sleep(0.05)
        if cap_in is not None:
            captured.extend(cap_in.iter_pending())
        adapter_result = {
            "success": True,
            "events_sent": len(events),
            "span_seconds": round(events[-1][0], 3) if events else 0.0,
        }
    except Exception as exc:  # noqa: BLE001
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason=f"coremidi_io_error:{type(exc).__name__}:{exc}",
            adapter_success=False,
            **versions,
        )
    finally:
        for port in (cap_in, out):
            if port is not None:
                try:
                    port.close()
                except Exception:  # noqa: BLE001
                    pass

    # ---- readback: independent capture or honest uncertainty --------------
    if cap_in is None:
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason="sent_without_independent_capture",
            adapter_success=True,
            before={"phrase_hash": compiled["phrase_hash"]},
            extra_notes=[
                f"adapter_result={adapter_result}",
                "E12 machine evidence needs a capture port on a different surface",
                "E02/E12 pass also needs the human receipt: Chris hears the instrument",
            ],
            **versions,
        )

    captured_hash = _phrase_hash_of_captured(captured, compiled["ppq"], compiled["tempo"])
    if captured_hash is None:
        return uncertain(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason="capture_empty_no_complete_note_pairs",
            adapter_success=True,
            before={"phrase_hash": compiled["phrase_hash"]},
            extra_notes=["capture saw nothing complete; is anything routed to the capture port?"],
            **versions,
        )

    if captured_hash != compiled["phrase_hash"]:
        return failed(
            probe_id=PROBE_ID,
            channel="coremidi",
            operation="composition.play_plan",
            requested=requested,
            reason="captured_hash_mismatch",
            adapter_result=adapter_result,
            readback={
                "method": "coremidi_capture",
                "captured_hash": captured_hash,
                "expected_hash": compiled["phrase_hash"],
                "messages": len(captured),
            },
            extra_notes=["independent capture contradicts the send; investigate routing before retrying"],
            **versions,
        )

    return confirmed(
        probe_id=PROBE_ID,
        channel="coremidi",
        operation="composition.play_plan",
        requested=requested,
        before={"phrase_hash": compiled["phrase_hash"]},
        adapter_result=adapter_result,
        readback={
            "method": "coremidi_capture",
            "captured_hash": captured_hash,
            "expected_hash": compiled["phrase_hash"],
            "messages": len(captured),
        },
        extra_notes=[
            "machine evidence matches (E12 capture leg)",
            "human receipt still required before E02/E12 is TESTED: Chris must hear the instrument",
        ],
        **versions,
    )


def play_plan_with_ports(
    compiled: dict[str, Any],
    *,
    send: Callable[[bytes], None],
    receive_pending: Callable[[], list[Any]],
    tempo_scale: float = 1.0,
) -> dict[str, Any]:
    """Port-free execution core for tests: same schedule, injected I/O.

    The live play_plan() wraps this with real mido ports; tests inject a
    fake out/in pair. Same honest envelope rules apply.
    """
    events = _schedule_events(compiled)
    sent = 0
    for _when, raw in events:
        send(raw)
        sent += 1
    captured = list(receive_pending())
    return {"events_sent": sent, "captured": captured}