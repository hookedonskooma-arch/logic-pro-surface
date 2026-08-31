// E03 fixture — Scripter is JavaScript MIDI processing, not Lua.
// Live pass: incoming C3 (60) becomes C4 (72) on the instrument track.
// Forbidden evidence: Script editor console text.
// This file is not a live TESTED result.

function HandleMIDI(event) {
    if (event instanceof Note) {
        event.pitch += 12;
    }
    event.send();
}
