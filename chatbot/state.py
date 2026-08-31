"""The session's musical truth: key, mode, tempo, meter.

The chat layer may only change this state through `MusicalState`, and every
proposal is checked against it before it reaches the user. Unset state is
UNKNOWN and is never silently defaulted -- an unknown key produces a question,
not a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .theory import (
    Chord,
    TheoryError,
    diatonic_triads,
    normalize_mode,
    note_name,
    parse_note,
    roman_numeral,
    scale_pitch_classes,
)
from .theory import MINOR_MODES

# Logic's own tempo range. Outside this a value is a mishearing, not a tempo.
MIN_TEMPO = 5.0
MAX_TEMPO = 990.0

FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}


@dataclass(frozen=True)
class Verdict:
    """The result of checking a proposal against the state."""

    ok: bool
    reason: str
    detail: str = ""

    def __bool__(self) -> bool:  # so callers can write `if verdict:`
        return self.ok


@dataclass
class MusicalState:
    tonic_pc: int | None = None
    mode: str | None = None
    tempo: float | None = None
    meter: tuple[int, int] | None = None
    progression: list[Chord] = field(default_factory=list)

    # -- key ---------------------------------------------------------------

    @property
    def key_known(self) -> bool:
        return self.tonic_pc is not None and self.mode is not None

    @property
    def prefer_flats(self) -> bool:
        if self.tonic_pc is None:
            return False
        return note_name(self.tonic_pc, prefer_flats=True) in FLAT_KEYS

    def key_name(self) -> str:
        if not self.key_known:
            return "UNKNOWN"
        return f"{note_name(self.tonic_pc, self.prefer_flats)} {self.mode}"

    def set_key(self, tonic: str, mode: str) -> str:
        pc = parse_note(tonic)
        normalized = normalize_mode(mode)
        self.tonic_pc, self.mode = pc, normalized
        return self.key_name()

    def set_tempo(self, bpm: float) -> float:
        bpm = float(bpm)
        if not MIN_TEMPO <= bpm <= MAX_TEMPO:
            raise TheoryError(
                f"{bpm:g} BPM is outside Logic's range ({MIN_TEMPO:g}-{MAX_TEMPO:g})"
            )
        self.tempo = bpm
        return bpm

    def set_meter(self, numerator: int, denominator: int) -> tuple[int, int]:
        if numerator < 1 or numerator > 32:
            raise TheoryError(f"{numerator} beats per bar is not a meter Logic accepts")
        if denominator not in (1, 2, 4, 8, 16, 32):
            raise TheoryError(f"/{denominator} is not a note value")
        self.meter = (numerator, denominator)
        return self.meter

    # -- coherence ---------------------------------------------------------

    def scale_pcs(self) -> tuple[int, ...]:
        if not self.key_known:
            raise TheoryError("no key set")
        return scale_pitch_classes(self.tonic_pc, self.mode)

    def check_chord(self, chord: Chord) -> Verdict:
        """Is this chord coherent with the current key?

        Fail-closed: with no key set we return not-ok with reason 'unknown',
        so the caller asks rather than inventing a key to be right about.
        """
        if not self.key_known:
            return Verdict(False, "unknown", "no key set for this session")
        scale = set(self.scale_pcs())
        outside = [pc for pc in chord.pitch_classes if pc not in scale]
        name = self.spell_chord(chord)
        if not outside:
            numeral = roman_numeral(chord, self.tonic_pc, self.mode)
            where = f" ({numeral})" if numeral else ""
            return Verdict(True, "diatonic", f"{name}{where} is in {self.key_name()}")
        spelled = ", ".join(self.spell(pc) for pc in outside)
        borrowed = self._borrowed_from(chord)
        if borrowed:
            return Verdict(
                False, "borrowed",
                f"{name} leaves {self.key_name()} on {spelled}; it is diatonic to "
                f"{borrowed}. Fine as a borrowed chord, not as a mistake.",
            )
        return Verdict(
            False, "outside",
            f"{name} leaves {self.key_name()} on {spelled}",
        )

    # Flat-side alterations get flat names even in a sharp key: bVII of C is
    # Bb, never A#. Sharp-side ones keep their sharps.
    _FLAT_SIDE = frozenset({1, 3, 6, 8, 10})

    def spell(self, pc: int) -> str:
        if self.tonic_pc is None:
            return note_name(pc, self.prefer_flats)
        flats = self.prefer_flats or (pc - self.tonic_pc) % 12 in self._FLAT_SIDE
        return note_name(pc, flats)

    def spell_chord(self, chord: Chord) -> str:
        suffix = {"maj": "", "min": "m", "5": "5"}.get(chord.quality, chord.quality)
        return f"{self.spell(chord.root_pc)}{suffix}"

    def _borrowed_from(self, chord: Chord) -> str | None:
        """Name a parallel mode on the same tonic that does contain the chord."""
        if self.tonic_pc is None:
            return None
        # Nearest neighbours first: from a minor mode, V7 is harmonic minor
        # long before it is "the parallel major".
        if self.mode in MINOR_MODES:
            order = ("harmonic minor", "melodic minor", "dorian", "minor",
                     "phrygian", "major", "mixolydian", "lydian")
        else:
            order = ("mixolydian", "lydian", "major", "minor", "dorian",
                     "harmonic minor", "melodic minor", "phrygian")
        for candidate in order:
            if candidate == self.mode:
                continue
            pcs = set(scale_pitch_classes(self.tonic_pc, candidate))
            if set(chord.pitch_classes) <= pcs:
                return f"{note_name(self.tonic_pc, self.prefer_flats)} {candidate}"
        return None

    def check_note(self, note: str) -> Verdict:
        pc = parse_note(note)
        if not self.key_known:
            return Verdict(False, "unknown", "no key set for this session")
        if pc in set(self.scale_pcs()):
            return Verdict(True, "diatonic", f"{self.spell(pc)} is in {self.key_name()}")
        return Verdict(False, "outside", f"{self.spell(pc)} is outside {self.key_name()}")

    def check_progression(self, chords: list[Chord]) -> list[Verdict]:
        return [self.check_chord(c) for c in chords]

    def diatonic_names(self) -> list[str]:
        return [c.name(self.prefer_flats)
                for c in diatonic_triads(self.tonic_pc, self.mode)]

    # -- timing ------------------------------------------------------------

    def bar_seconds(self) -> float | None:
        """Seconds per bar, or None if tempo or meter is unknown."""
        if self.tempo is None or self.meter is None:
            return None
        numerator, denominator = self.meter
        beats_per_bar = numerator * (4.0 / denominator)
        return beats_per_bar * 60.0 / self.tempo

    def summary(self) -> str:
        tempo = f"{self.tempo:g} BPM" if self.tempo is not None else "tempo UNKNOWN"
        meter = f"{self.meter[0]}/{self.meter[1]}" if self.meter else "meter UNKNOWN"
        return f"{self.key_name()} | {tempo} | {meter}"

    def snapshot(self) -> "MusicalState":
        return replace(self, progression=list(self.progression))
