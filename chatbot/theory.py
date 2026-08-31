"""Pitch-class theory primitives.

Deliberately small and total: every function here is pure, has no I/O, and
raises on input it cannot represent rather than guessing. The chat layer is
allowed to be vague; this module is not.
"""

from __future__ import annotations

from dataclasses import dataclass

SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

_ALIASES = {
    "e#": "F", "fb": "E", "b#": "C", "cb": "B",
    "cx": "D", "dx": "E", "fx": "G", "gx": "A", "ax": "B",
}

# Scale degrees as semitone offsets from the tonic.
SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "locrian": (0, 1, 3, 5, 6, 8, 10),
    "harmonic minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic minor": (0, 2, 3, 5, 7, 9, 11),
    "phrygian dominant": (0, 1, 4, 5, 7, 8, 10),
    "minor pentatonic": (0, 3, 5, 7, 10),
    "major pentatonic": (0, 2, 4, 7, 9),
    "blues": (0, 3, 5, 6, 7, 10),
}

# Modes that read as minor-ish, for naming and for the tonic triad.
MINOR_MODES = {
    "minor", "aeolian", "dorian", "phrygian", "locrian",
    "harmonic minor", "melodic minor", "minor pentatonic",
}

# Chord qualities as intervals from the root.
CHORD_QUALITIES: dict[str, tuple[int, ...]] = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "5": (0, 7),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "7": (0, 4, 7, 10),
    "min7b5": (0, 3, 6, 10),
    "dim7": (0, 3, 6, 9),
    "min6": (0, 3, 7, 9),
    "6": (0, 4, 7, 9),
    "min9": (0, 3, 7, 10, 14),
    "maj9": (0, 4, 7, 11, 14),
    "9": (0, 4, 7, 10, 14),
}

# Spellings accepted from humans and from speech-to-text, mapped to a quality.
_QUALITY_ALIASES = {
    "": "maj", "maj": "maj", "major": "maj", "M": "maj",
    "m": "min", "min": "min", "minor": "min", "-": "min",
    "dim": "dim", "diminished": "dim", "o": "dim",
    "aug": "aug", "augmented": "aug", "+": "aug",
    "sus": "sus4", "sus2": "sus2", "sus4": "sus4",
    "5": "5", "power": "5",
    "maj7": "maj7", "major7": "maj7", "M7": "maj7", "Maj7": "maj7",
    "m7": "min7", "min7": "min7", "minor7": "min7", "-7": "min7",
    "7": "7", "dom7": "7", "dominant7": "7",
    "m7b5": "min7b5", "min7b5": "min7b5", "halfdim": "min7b5", "o7": "dim7",
    "dim7": "dim7", "m6": "min6", "min6": "min6", "6": "6",
    "m9": "min9", "min9": "min9", "maj9": "maj9", "M9": "maj9", "9": "9",
}

ROMAN_DEGREES = ["I", "II", "III", "IV", "V", "VI", "VII"]


class TheoryError(ValueError):
    """Input that cannot be represented as pitch material."""


def parse_note(name: str) -> int:
    """Return the pitch class 0-11 for a note name. Raises on nonsense."""
    raw = name.strip().replace("♯", "#").replace("♭", "b")
    if not raw:
        raise TheoryError("empty note name")
    low = raw.lower()
    if low in _ALIASES:
        raw = _ALIASES[low]
        low = raw.lower()
    letter = raw[0].upper()
    if letter not in "ABCDEFG":
        raise TheoryError(f"not a note name: {name!r}")
    base = SHARP_NAMES.index(letter) if letter in SHARP_NAMES else FLAT_NAMES.index(letter)
    pc = base
    for accidental in raw[1:]:
        if accidental == "#":
            pc += 1
        elif accidental == "b":
            pc -= 1
        elif accidental in " \t":
            continue
        else:
            raise TheoryError(f"not a note name: {name!r}")
    return pc % 12


def note_name(pc: int, prefer_flats: bool = False) -> str:
    names = FLAT_NAMES if prefer_flats else SHARP_NAMES
    return names[pc % 12]


def normalize_mode(mode: str) -> str:
    key = mode.strip().lower().replace("_", " ")
    key = {"maj": "major", "min": "minor", "nat minor": "minor",
           "natural minor": "minor", "pent minor": "minor pentatonic",
           "pent major": "major pentatonic"}.get(key, key)
    if key not in SCALES:
        raise TheoryError(f"unknown mode: {mode!r}")
    return key


def scale_pitch_classes(tonic_pc: int, mode: str) -> tuple[int, ...]:
    return tuple((tonic_pc + step) % 12 for step in SCALES[normalize_mode(mode)])


@dataclass(frozen=True)
class Chord:
    """A chord as a root pitch class plus a quality from CHORD_QUALITIES."""

    root_pc: int
    quality: str
    text: str

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple((self.root_pc + i) % 12 for i in CHORD_QUALITIES[self.quality])

    def name(self, prefer_flats: bool = False) -> str:
        suffix = {"maj": "", "min": "m", "5": "5"}.get(self.quality, self.quality)
        return f"{note_name(self.root_pc, prefer_flats)}{suffix}"


def parse_chord(text: str) -> Chord:
    """Parse 'Bbmaj7', 'F#m', 'Csus4', 'G7' into a Chord. Raises on nonsense."""
    raw = text.strip().replace("♯", "#").replace("♭", "b")
    if not raw:
        raise TheoryError("empty chord")
    head = raw.split("/")[0]  # slash bass does not change the chord's pitch set
    i = 1
    while i < len(head) and head[i] in "#b":
        i += 1
    root_text, quality_text = head[:i], head[i:].strip()
    root_pc = parse_note(root_text)
    quality = _QUALITY_ALIASES.get(quality_text)
    if quality is None:
        quality = _QUALITY_ALIASES.get(quality_text.lower())
    if quality is None:
        raise TheoryError(f"unknown chord quality: {quality_text!r} in {text!r}")
    return Chord(root_pc=root_pc, quality=quality, text=raw)


def diatonic_triads(tonic_pc: int, mode: str) -> list[Chord]:
    """The seven diatonic triads, built in thirds off the scale itself."""
    mode = normalize_mode(mode)
    steps = SCALES[mode]
    if len(steps) != 7:
        raise TheoryError(f"{mode} is not a seven-note scale; no diatonic triads")
    pcs = scale_pitch_classes(tonic_pc, mode)
    chords: list[Chord] = []
    for degree in range(7):
        root = pcs[degree]
        third = (pcs[(degree + 2) % 7] - root) % 12
        fifth = (pcs[(degree + 4) % 7] - root) % 12
        quality = {
            (4, 7): "maj", (3, 7): "min", (3, 6): "dim", (4, 8): "aug",
        }.get((third, fifth))
        if quality is None:
            raise TheoryError(f"non-tertian triad on degree {degree + 1} of {mode}")
        chords.append(Chord(root_pc=root, quality=quality, text=""))
    return chords


def roman_numeral(chord: Chord, tonic_pc: int, mode: str) -> str | None:
    """Roman numeral for a chord that is diatonic to the key, else None."""
    for degree, diatonic in enumerate(diatonic_triads(tonic_pc, mode)):
        if diatonic.root_pc == chord.root_pc:
            triad = set(chord.pitch_classes) & set(diatonic.pitch_classes)
            if not set(diatonic.pitch_classes) <= set(chord.pitch_classes) and len(triad) < 3:
                return None
            numeral = ROMAN_DEGREES[degree]
            if diatonic.quality in ("min", "dim"):
                numeral = numeral.lower()
            if diatonic.quality == "dim":
                numeral += "°"
            return numeral
    return None
