"""Fail-closed tests: the bot must refuse to guess before it may be right."""

import unittest

from chatbot import MusicalChatBot, MusicalState
from chatbot.language import find_chords, find_key, find_tempo, normalize
from chatbot.theory import TheoryError, diatonic_triads, parse_chord, parse_note


class TestTheory(unittest.TestCase):
    def test_enharmonics(self):
        self.assertEqual(parse_note("A#"), parse_note("Bb"))
        self.assertEqual(parse_note("Cb"), parse_note("B"))
        self.assertEqual(parse_note("E#"), parse_note("F"))

    def test_bad_note_raises(self):
        for bad in ("H", "", "sharp", "A##b#x"):
            with self.assertRaises(TheoryError):
                parse_note(bad)

    def test_bad_chord_raises(self):
        with self.assertRaises(TheoryError):
            parse_chord("Cwobble")

    def test_diatonic_triads_of_c_major(self):
        names = [c.name() for c in diatonic_triads(parse_note("C"), "major")]
        self.assertEqual(names, ["C", "Dm", "Em", "F", "G", "Am", "Bdim"])

    def test_modes_differ(self):
        dorian = [c.name() for c in diatonic_triads(parse_note("D"), "dorian")]
        self.assertEqual(dorian[0], "Dm")
        self.assertEqual(dorian[3], "G")  # major IV is what makes it dorian

    def test_pentatonic_has_no_diatonic_triads(self):
        with self.assertRaises(TheoryError):
            diatonic_triads(parse_note("A"), "minor pentatonic")


class TestState(unittest.TestCase):
    def setUp(self):
        self.state = MusicalState()

    def test_unknown_key_fails_closed(self):
        verdict = self.state.check_chord(parse_chord("Cmaj7"))
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason, "unknown")

    def test_diatonic_and_outside(self):
        self.state.set_key("C", "major")
        self.assertTrue(self.state.check_chord(parse_chord("Dm7")))
        self.assertFalse(self.state.check_chord(parse_chord("Ab")))

    def test_borrowed_is_named_not_scolded(self):
        self.state.set_key("A", "minor")
        verdict = self.state.check_chord(parse_chord("E7"))
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason, "borrowed")
        self.assertIn("harmonic minor", verdict.detail)

    def test_flat_side_alterations_are_spelled_flat(self):
        self.state.set_key("C", "major")
        self.assertIn("Bb", self.state.check_chord(parse_chord("Bb")).detail)

    def test_tempo_bounds(self):
        with self.assertRaises(TheoryError):
            self.state.set_tempo(0)
        with self.assertRaises(TheoryError):
            self.state.set_tempo(4000)
        self.assertEqual(self.state.set_tempo(92), 92.0)

    def test_meter_validation(self):
        with self.assertRaises(TheoryError):
            self.state.set_meter(4, 5)
        self.assertEqual(self.state.set_meter(6, 8), (6, 8))

    def test_bar_seconds_needs_both(self):
        self.state.set_tempo(120)
        self.assertIsNone(self.state.bar_seconds())
        self.state.set_meter(4, 4)
        self.assertAlmostEqual(self.state.bar_seconds(), 2.0)
        self.state.set_meter(6, 8)
        self.assertAlmostEqual(self.state.bar_seconds(), 1.5)


class TestLanguage(unittest.TestCase):
    def test_spoken_key_and_tempo(self):
        text = normalize("key of b flat minor at ninety two b p m")
        self.assertEqual(find_key(text), ("bb", "minor"))
        self.assertEqual(find_tempo(text), 92.0)

    def test_spoken_hundreds(self):
        self.assertEqual(find_tempo(normalize("one hundred forty bpm")), 140.0)

    def test_chord_shaped_text_finds_bare_letters(self):
        self.assertEqual(find_chords("Am - F - C - G"), ["Am", "F", "C", "G"])

    def test_prose_is_not_mined_for_chords(self):
        self.assertEqual(find_chords("can you help me"), [])

    def test_spoken_chord_quality(self):
        self.assertEqual(find_chords(normalize("is b flat major seventh in key")),
                         ["bbmaj7"])


class TestBot(unittest.TestCase):
    def setUp(self):
        self.bot = MusicalChatBot()

    def test_refuses_before_key_is_set(self):
        reply = self.bot.respond("is Bbmaj7 in key?").reply
        self.assertIn("No key set", reply)

    def test_sets_everything_in_one_sentence(self):
        self.bot.respond("key of A minor at 92 bpm in 4/4")
        self.assertEqual(self.bot.state.key_name(), "A minor")
        self.assertEqual(self.bot.state.tempo, 92.0)
        self.assertEqual(self.bot.state.meter, (4, 4))

    def test_answers_are_derived_from_current_state_not_history(self):
        self.bot.respond("key of C major")
        self.assertIn("OUT", self.bot.respond("Eb").reply)
        self.bot.respond("key of Eb major")
        self.assertNotIn("OUT", self.bot.respond("Eb").reply)

    def test_key_name_is_not_re_read_as_a_chord(self):
        reply = self.bot.respond("key of Bb minor at 92 bpm in 6/8").reply
        self.assertNotIn("OUT", reply)

    def test_spoken_chord_question_survives_normalization(self):
        self.bot.respond("key of Bb minor")
        self.assertIn("Bbmaj7", self.bot.respond("is b flat major seventh in key").reply)

    def test_forget_returns_to_unknown(self):
        self.bot.respond("key of C major")
        self.bot.respond("forget the key")
        self.assertIn("No key set", self.bot.respond("Dm7").reply)

    def test_bar_length_requires_tempo_and_meter(self):
        self.assertIn("UNKNOWN", self.bot.respond("how long is a bar").reply)
        self.bot.respond("120 bpm in 4/4")
        self.assertIn("2.000 s", self.bot.respond("how long is a bar").reply)

    def test_unparseable_chord_is_reported_not_swallowed(self):
        self.bot.respond("key of C major")
        reply = self.bot.respond("what about Cwobble, chord").reply
        self.assertIn("could not parse", reply.lower())

    def test_spoken_reply_never_contains_screen_formatting(self):
        self.bot.respond("key of A minor")
        spoken = self.bot.respond("Am - F - C - E7").spoken
        self.assertNotIn("\n", spoken)
        self.assertNotIn("OUT", spoken)


if __name__ == "__main__":
    unittest.main()
