"""Turning spoken or typed English into things the theory layer accepts.

Speech-to-text hands us "b flat minor" and "ninety two b p m". This module is
the only place allowed to be lenient; everything downstream of it is strict.
"""

from __future__ import annotations

import re

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
}

_SPOKEN_FIXES = [
    (r"\bb\s*p\s*m\b", "bpm"),
    (r"\bbeats per minute\b", "bpm"),
    (r"\b([a-g])\s+flat\b", r"\1b"),
    (r"\b([a-g])\s+sharp\b", r"\1#"),
    (r"\b([a-g])-flat\b", r"\1b"),
    (r"\b([a-g])-sharp\b", r"\1#"),
    (r"\bmajor seven(th)?\b", "maj7"),
    (r"\bminor seven(th)?\b", "m7"),
    (r"\bdominant seven(th)?\b", "7"),
    (r"\bsus (two|2)\b", "sus2"),
    (r"\bsus (four|4)\b", "sus4"),
    (r"\bpower chord\b", "5"),
    (r"\bhalf[- ]diminished\b", "m7b5"),
]


NOTE = r"[A-Ga-g](?:#|b|♯|♭)?"


def words_to_number(text: str) -> float | None:
    """Parse '92', 'ninety two', 'one hundred forty' into a number."""
    text = text.strip().lower().replace("-", " ")
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    total = 0
    current = 0
    seen = False
    for word in text.split():
        if word == "and":
            continue
        value = WORD_NUMBERS.get(word)
        if value is None:
            return None
        seen = True
        if value == 100:
            current = max(current, 1) * 100
        else:
            current += value
    if not seen:
        return None
    return float(total + current)


def normalize(text: str) -> str:
    """Fold spoken spellings into written ones. Case is preserved elsewhere."""
    out = " ".join(text.split())
    low = out.lower()
    for pattern, replacement in _SPOKEN_FIXES:
        low = re.sub(pattern, replacement, low)
    low = _numberize_tempo(low)
    # "b flat maj7" -> "bbmaj7": speech puts a space where notation does not.
    return re.sub(
        rf"\b({NOTE})\s+((?:maj|min|dim|sus|m|M)?[0-9]?(?:b5)?)\b(?=\s|$|[,.;])",
        lambda m: m.group(1) + m.group(2) if m.group(2) else m.group(0),
        low,
    )


_WORD = r"(?:" + "|".join(WORD_NUMBERS) + r"|and)"
_NUMBER_WORDS_RE = re.compile(rf"\b({_WORD}(?:[- ]+{_WORD})*)\s+bpm\b")


def _numberize_tempo(text: str) -> str:
    """'ninety two bpm' -> '92 bpm'. Digits are left alone."""

    def replace(match: re.Match) -> str:
        value = words_to_number(match.group(1))
        return f"{value:g} bpm" if value is not None else match.group(0)

    return _NUMBER_WORDS_RE.sub(replace, text)


MODES = (
    "major|minor|ionian|dorian|phrygian dominant|phrygian|lydian|mixolydian|"
    "aeolian|locrian|harmonic minor|melodic minor|minor pentatonic|"
    "major pentatonic|blues"
)

KEY_RE = re.compile(rf"\b(?:key of\s+)?({NOTE})\s+({MODES})\b", re.I)
TEMPO_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:bpm|beats)\b", re.I)
METER_RE = re.compile(r"\b(\d{1,2})\s*/\s*(1|2|4|8|16|32)\b")
CHORD_TOKEN_RE = re.compile(
    rf"\b({NOTE}(?:maj7|maj9|min7b5|m7b5|min7|min9|min6|min|maj|dim7|dim|aug|"
    rf"sus2|sus4|sus|m7|m9|m6|m|7|9|6|5|\+|°)?)\b"
)

# Words that look like chords to the regex but are English.
_NOT_CHORDS = {"a", "b", "be", "e", "am", "as", "ad", "add", "f", "g", "d", "c",
               "an", "at", "bad", "bag", "bed", "cab", "dad", "did", "fed",
               "fee", "gag", "age", "ace", "bee", "egg", "face", "cage"}


def find_key(text: str) -> tuple[str, str] | None:
    match = KEY_RE.search(text)
    return (match.group(1), match.group(2)) if match else None


def strip_key(text: str) -> str:
    """Remove any 'key of X mode' span, so its tonic is not read as a chord."""
    return KEY_RE.sub(" ", text)


def find_tempo(text: str) -> float | None:
    match = TEMPO_RE.search(text)
    return float(match.group(1)) if match else None


def find_meter(text: str) -> tuple[int, int] | None:
    match = METER_RE.search(text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def find_chords(text: str) -> list[str]:
    """Chord tokens in the order written.

    Bare single letters are only taken as chords when the text is chord-shaped
    (dashes, arrows, commas, or the word 'chord'), because 'a' and 'be' are
    English far more often than they are A major.
    """
    return [token for token, ok in find_chord_candidates(text) if ok]


SUSPECT_RE = re.compile(rf"\b({NOTE}[A-Za-z][A-Za-z0-9#b]*)\b")


def find_chord_candidates(text: str) -> list[tuple[str, bool]]:
    """Chord tokens plus tokens that are chord-shaped but not chords.

    The second kind matters: 'Cwobble' in a chord question is a mishearing the
    bot must report, not silently drop.
    """
    chord_shaped = bool(re.search(r"[-–>,|]|chord|progression|changes", text, re.I))
    found: list[tuple[str, bool]] = []
    spans: list[tuple[int, int]] = []
    for match in CHORD_TOKEN_RE.finditer(text):
        token = match.group(1)
        if not chord_shaped and token.lower() in _NOT_CHORDS:
            continue
        found.append((token, True))
        spans.append(match.span())
    if chord_shaped:
        for match in SUSPECT_RE.finditer(text):
            if any(start <= match.start() < end for start, end in spans):
                continue
            token = match.group(1)
            if token.lower() in _NOT_CHORDS or len(token) < 3:
                continue
            found.append((token, False))
    return found
