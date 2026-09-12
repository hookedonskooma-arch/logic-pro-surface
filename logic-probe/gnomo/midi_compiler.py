"""MIDI compiler: MusicPlan in, deterministic MIDI events out. No AI here.

This is the component the failure-driven doc demands: no generative step,
same plan in -> same events out, byte for byte, unless variation is
explicitly configured later. Unit-testable without Logic, without mido,
without CoreMIDI.

Pipeline (studio/FAILURE_DRIVEN_ARCHITECTURE.md section 4-D):

    chord symbol -> pitch classes -> voicing rules -> MIDI notes
      -> timing -> velocity -> MIDI events -> standard MIDI file

Determinism contract, pinned by tests:
- same plan -> identical event list and identical SMF bytes
- unknown chord / voicing / register can never reach here (validator
  raises first), but the compiler re-checks and raises MusicPlanError
  rather than emitting a guess — defense in depth, fail closed
- taste (voicing/register/velocity) comes from the plan's frozen fields;
  the compiler never invents taste

Output is a SMF type 0 track (chords as one voice) written to disk and/or
held in memory for the seam to send live. Region placement in Logic is a
human hand (consolidate) — the compiler promises audible MIDI, not regions.
"""

from __future__ import annotations

from typing import Any

from .music_plan import (
    CHORD_INTERVALS,
    METERS,
    MusicPlanError,
    REGISTER_ROOT_OCTAVE,
    parse_chord,
)
from .melody import compile_melody, weave_events

PPQ = 480


def _scale_range(lo: int, hi: int, count: int) -> list[int]:
    """Deterministic velocity spread across a chord's notes: root gets lo+.

    Boring on purpose: same plan, same velocities. Root = hi anchor, upper
    voices scale down toward lo. A one-note chord gets exactly lo+hi // 2.
    """
    if count <= 0:
        return []
    if count == 1:
        return [(lo + hi) // 2]
    out: list[int] = []
    for i in range(count):
        frac = i / (count - 1)
        v = round(hi - frac * (hi - lo))
        out.append(max(lo, min(hi, v)))
    return out


def _voiced_midi_notes(symbol: str, voicing: str, register: str) -> list[int]:
    """One chord symbol -> concrete MIDI note numbers, deterministically.

    voicing:
      closed — stack the chord tones upward from the root, first inversion
               spread allowed only to avoid a minor-second cluster (none
               exists in the recognized table, so closed is pure stacking)
      wide   — closed stack, then drop voice 3 down an octave for spread
      shell  — root + 7th (or 5th when the quality has no 7th)
    register: root octave from REGISTER_ROOT_OCTAVE; chords may exceed
    octave 6 only by stacking — validator bounds nothing here because the
    recognized interval table cannot produce MIDI < 0 or > 127 from any
    root octave in the table. The assert below is the belt over braces.
    """
    root_pc, quality = parse_chord(symbol)
    intervals = CHORD_INTERVALS[quality]
    root_octave = REGISTER_ROOT_OCTAVE[register]
    root_midi = 12 * (root_octave + 1) + root_pc

    pcs = [(root_midi + iv) for iv in intervals]  # ascending stack, real octaves

    if voicing == "shell":
        # root + highest extension if present, else the fifth
        pick = pcs[-1] if len(pcs) >= 4 else pcs[min(2, len(pcs) - 1)]
        notes = [pcs[0], pick]
    elif voicing == "wide" and len(pcs) >= 4:
        notes = [pcs[0], pcs[1], pcs[2] - 12, pcs[3]]
        notes = notes + pcs[4:]
    else:
        notes = list(pcs)

    notes = sorted(notes)
    if any(n < 0 or n > 127 for n in notes):  # pragma: no cover — table-bounded
        raise MusicPlanError(f"compiled notes out of MIDI range for {symbol!r}")
    return notes


def compile_events(plan: dict[str, Any]) -> dict[str, Any]:
    """Plan -> deterministic event list + timing facts. No I/O, no AI."""
    voicing = plan.get("voicing")
    register = plan.get("register")
    if voicing not in ("closed", "wide", "shell") or register not in ("low", "mid", "high"):
        # Validator guarantees this; re-check fail closed anyway.
        raise MusicPlanError(f"compiler refuses unvalidated plan fields: {voicing!r}/{register!r}")

    ticks_per_bar = METERS[plan["meter"]]
    bar_ticks = ticks_per_bar
    lo, hi = plan["velocity_range"]
    chords: list[str] = plan["chords"]

    notes_by_bar: list[dict[str, Any]] = []
    for i, sym in enumerate(chords):
        notes = _voiced_midi_notes(sym, voicing, register)
        velocities = _scale_range(lo, hi, len(notes))
        notes_by_bar.append(
            {
                "bar": i + 1,
                "symbol": sym,
                "start_tick": i * bar_ticks,
                "end_tick": (i + 1) * bar_ticks,
                "notes": [
                    {"note": n, "velocity": v}
                    for n, v in zip(notes, velocities)
                ],
            }
        )

    return {
        "ppq": PPQ,
        "tempo": plan["tempo"],
        "meter": plan["meter"],
        "ticks_per_bar": ticks_per_bar,
        "length_bars": plan["length_bars"],
        "voicing": voicing,
        "register": register,
        "bars": notes_by_bar,
        "event_count": sum(len(b["notes"]) * 2 for b in notes_by_bar),  # on+off
    }


def _varlen(value: int) -> bytes:
    """SMF variable-length quantity."""
    if value < 0:
        raise MusicPlanError("negative delta time")
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def events_to_smf(compiled: dict[str, Any]) -> bytes:
    """Deterministic type-0 SMF: tempo meta, time signature, one chord track.

    Same compiled structure -> same bytes, every time. Notes start together
    at the bar line; NoteOff lands exactly on the next bar line. No human
    timing here — humanization is a taste call and stays out of the machine.
    """
    ppq = compiled["ppq"]
    ticks_per_bar = compiled["ticks_per_bar"]
    tempo = compiled["tempo"]

    # -- header ------------------------------------------------------------
    n_ticks = ticks_per_bar * compiled["length_bars"]
    division = ppq.to_bytes(2, "big")
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x00" + b"\x00\x01" + division

    # -- track events --------------------------------------------------------
    ev: list[tuple[int, bytes]] = []
    us_per_quarter = round(60_000_000 / tempo)
    ev.append((0, b"\xff\x51\x03" + us_per_quarter.to_bytes(3, "big")))
    num, den = compiled["meter"].split("/")
    den_pow = {2: 1, 4: 2, 8: 3}.get(int(den))
    if den_pow is None:
        raise MusicPlanError(f"unsupported meter denominator: {den}")
    ev.append((0, b"\xff\x58\x04" + bytes([int(num), den_pow, 24, 8])))

    for bar in compiled["bars"]:
        start = bar["start_tick"]
        end = bar["end_tick"]
        for entry in bar["notes"]:
            note, vel = entry["note"], entry["velocity"]
            ev.append((start, bytes([0x90, note, vel])))
            ev.append((end, bytes([0x80, note, 0x40])))

    # melody voice (v0.2): channel 1 (0x9n with n=1), same deterministic grid
    for bar in compiled.get("melody_bars") or []:
        start = bar["start_tick"]
        end = bar["end_tick"]
        for entry in bar["notes"]:
            note, vel = entry["note"], entry["velocity"]
            ev.append((start, bytes([0x91, note, vel])))
            ev.append((end, bytes([0x81, note, 0x40])))

    ev.sort(key=lambda item: (item[0], item[1]))  # stable: tick, then bytes

    track = bytearray()
    last = 0
    for tick, payload in ev:
        track += _varlen(tick - last) + payload
        last = tick
    track += _varlen(0) + b"\xff\x2f\x00"  # end of track

    return header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)


def phrase_hash(compiled: dict[str, Any]) -> str:
    """Stable content hash of the compiled phrase — the E02/E12 fixture bit.

    Hashes the compiled structure (not the SMF container), so the same
    musical events hash the same regardless of packaging. This is the value
    the seam's CoreMIDI capture must reproduce to call E02/E12 `confirmed`.
    """
    import hashlib

    parts: list[str] = []
    for bar in compiled["bars"]:
        for entry in bar["notes"]:
            parts.append(f"{bar['start_tick']}:{entry['note']}:{entry['velocity']}")
    blob = "|".join(parts) + f"|ppq{compiled['ppq']}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def compile_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """One call: validated plan -> compiled events + SMF bytes + phrase hash.

    With a melody block (v0.2): melody bars are compiled from the same
    frozen tables, woven in as a second voice on MIDI channel 1, and the
    phrase hash extends deterministically (chord notes, then m-prefixed
    melody notes). Chord-only plans hash exactly as v0.1 did.
    """
    compiled = compile_events(plan)
    melody_bars = compile_melody(plan, compiled["ticks_per_bar"])
    if melody_bars:
        compiled = weave_events(compiled, melody_bars)
    compiled["smf"] = events_to_smf(compiled)
    if "phrase_hash" not in compiled:  # chord-only path hashes as before
        compiled["phrase_hash"] = phrase_hash(compiled)
    return compiled


def write_smf(compiled: dict[str, Any], path: str) -> str:
    """Write the SMF to disk (for drag-in or DAW-less audition). Returns path."""
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(compiled["smf"])
    return str(p)