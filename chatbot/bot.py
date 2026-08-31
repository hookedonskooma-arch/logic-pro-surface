"""The conversation layer.

Rules this layer obeys, in the same spirit as SURFACE.md:

* State is never guessed. With no key set, a question about a chord returns a
  question, not an answer.
* Every answer that depends on key, tempo or meter is derived from
  MusicalState at answer time -- never from what was said earlier in the chat.
* Anything outside the key is named as outside, with the note that leaves it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import language
from .state import MusicalState
from .theory import TheoryError, note_name, parse_chord

HELP = """\
I hold the key, mode, tempo and meter for this session and check what you play
against them.

  key of F# dorian          set the key
  92 bpm / 6/8              set tempo or meter
  is Bbmaj7 in key?         check one chord
  Am - F - C - G            check a progression
  what chords do I have     the diatonic triads
  where am i                current state
  forget the key            clear it
  quit
"""


@dataclass
class Turn:
    user: str
    reply: str
    spoken: str


@dataclass
class MusicalChatBot:
    state: MusicalState = field(default_factory=MusicalState)
    history: list[Turn] = field(default_factory=list)

    def respond(self, raw: str) -> Turn:
        text = language.normalize(raw)
        reply, spoken = self._route(raw, text)
        turn = Turn(user=raw, reply=reply, spoken=spoken)
        self.history.append(turn)
        return turn

    # -- routing -----------------------------------------------------------

    def _route(self, raw: str, text: str) -> tuple[str, str]:
        if not text.strip():
            return "", ""
        if text in ("help", "?", "what can you do"):
            return HELP, "I hold the key, tempo and meter, and check what you play against them."
        if text in ("where am i", "state", "status", "what's the state"):
            return self._state_report(), self._spoken_state()
        if text.startswith("forget"):
            return self._forget(text)

        settings, text_after_settings = self._apply_settings(text)

        if any(word in text for word in ("what chords", "which chords", "diatonic",
                                         "chords do i have", "chords are in")):
            return self._prefix(settings, *self._diatonic_report())
        if "bar" in text and ("long" in text or "seconds" in text or "how" in text):
            return self._prefix(settings, *self._bar_length())

        # Look at what was typed first (case tells "Am" from "am"), then fall
        # back to the normalized text, which is where spoken chords survive.
        candidates = language.find_chord_candidates(language.strip_key(raw))
        if not candidates:
            candidates = language.find_chord_candidates(text_after_settings)
        if candidates:
            return self._prefix(settings, *self._check_chords(candidates))

        if settings:
            report = self._state_report()
            return "\n".join(settings) + "\n" + report, self._spoken_state()

        return (
            "I did not hear a key, a tempo or a chord in that. Say `help` for what I "
            "understand.",
            "I did not catch a key, tempo or chord in that.",
        )

    @staticmethod
    def _prefix(settings: list[str], reply: str, spoken: str) -> tuple[str, str]:
        if settings:
            reply = "\n".join(settings) + "\n" + reply
        return reply, spoken

    # -- handlers ----------------------------------------------------------

    def _apply_settings(self, text: str) -> tuple[list[str], str]:
        """Apply any key/tempo/meter in the text.

        Returns what changed and the text with those spans removed, so the key
        name in "key of Bb minor" is never re-read as a Bb chord.
        """
        changed: list[str] = []
        key = language.find_key(text)
        if key:
            try:
                changed.append(f"Key set: {self.state.set_key(*key)}")
            except TheoryError as error:
                changed.append(f"Key not set: {error}")
        tempo = language.find_tempo(text)
        if tempo is not None:
            try:
                changed.append(f"Tempo set: {self.state.set_tempo(tempo):g} BPM")
            except TheoryError as error:
                changed.append(f"Tempo not set: {error}")
        meter = language.find_meter(text)
        if meter:
            try:
                numerator, denominator = self.state.set_meter(*meter)
                changed.append(f"Meter set: {numerator}/{denominator}")
            except TheoryError as error:
                changed.append(f"Meter not set: {error}")
        return changed, language.strip_key(text)

    def _forget(self, text: str) -> tuple[str, str]:
        if "tempo" in text:
            self.state.tempo = None
            return "Tempo is UNKNOWN again.", "Tempo cleared."
        if "meter" in text or "time" in text:
            self.state.meter = None
            return "Meter is UNKNOWN again.", "Meter cleared."
        if "key" in text:
            self.state.tonic_pc = self.state.mode = None
            return "Key is UNKNOWN again.", "Key cleared."
        self.state = MusicalState()
        return "Cleared. Key, tempo and meter are all UNKNOWN.", "All cleared."

    def _state_report(self) -> str:
        lines = [self.state.summary()]
        if self.state.key_known:
            lines.append("Diatonic: " + " ".join(self.state.diatonic_names()))
        bar = self.state.bar_seconds()
        if bar is not None:
            lines.append(f"One bar = {bar:.3f} s")
        return "\n".join(lines)

    def _spoken_state(self) -> str:
        return self.state.summary().replace("|", ",").replace("UNKNOWN", "not set")

    def _diatonic_report(self) -> tuple[str, str]:
        if not self.state.key_known:
            return self._need_key()
        names = self.state.diatonic_names()
        numerals = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
        if self.state.mode in ("minor", "aeolian"):
            numerals = ["i", "ii°", "III", "iv", "v", "VI", "VII"]
        pairs = "  ".join(f"{n} {c}" for n, c in zip(numerals, names))
        return (f"In {self.state.key_name()}: {pairs}",
                f"In {self.state.key_name()}: " + ", ".join(names))

    def _bar_length(self) -> tuple[str, str]:
        bar = self.state.bar_seconds()
        if bar is None:
            missing = []
            if self.state.tempo is None:
                missing.append("tempo")
            if self.state.meter is None:
                missing.append("meter")
            text = f"I cannot say: {' and '.join(missing)} UNKNOWN."
            return text, text.replace("UNKNOWN", "not set")
        numerator, denominator = self.state.meter
        return (
            f"At {self.state.tempo:g} BPM in {numerator}/{denominator}, "
            f"one bar = {bar:.3f} s ({bar * 1000:.0f} ms).",
            f"One bar is {bar:.2f} seconds.",
        )

    def _need_key(self) -> tuple[str, str]:
        text = "No key set for this session, so I will not guess. Tell me the key first."
        return text, text

    def _check_chords(self, candidates: list[tuple[str, bool]]) -> tuple[str, str]:
        parsed = []
        rejected = []
        for token, looks_like_chord in candidates:
            if not looks_like_chord:
                rejected.append(f"could not parse {token!r} as a chord")
                continue
            try:
                parsed.append(parse_chord(token))
            except TheoryError as error:
                rejected.append(str(error))
        if not parsed:
            text = "I could not parse a chord out of that: " + "; ".join(rejected)
            return text, "I could not parse that chord."
        if not self.state.key_known:
            return self._need_key()
        self.state.progression = parsed
        lines = []
        outside = []
        for chord, verdict in zip(parsed, self.state.check_progression(parsed)):
            mark = "ok  " if verdict.ok else "OUT "
            lines.append(f"  {mark}{verdict.detail}")
            if not verdict.ok:
                outside.append(self.state.spell_chord(chord))
        header = f"Against {self.state.key_name()}:"
        if outside:
            spoken = f"{', '.join(outside)} leave the key."
        else:
            spoken = "All of that is in key."
        if rejected:
            lines.append("  ??  " + "; ".join(rejected))
        return "\n".join([header, *lines]), spoken
