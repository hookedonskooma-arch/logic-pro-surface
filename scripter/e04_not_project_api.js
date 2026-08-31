// E04 — Scripter is not a Logic project API (Apple: Scripter MIDI plug-in).
// A script cannot rename the project or create a track. Attempt must fail.
// Documented surface: HandleMIDI / ProcessMIDI / PluginParameters / MIDI events.

var PluginParameters = [
    { name: "E04 probe", type: "menu", valueStrings: ["midi-only"], defaultValue: 0 }
];

function HandleMIDI(event) {
    event.send();
}

function ProcessMIDI() {
    // These identifiers are NOT in Apple's Scripter API. A host that
    // implements only Scripter must leave them undefined / throwing.
    if (typeof RenameProject === "function") {
        Trace("E04 FAIL: RenameProject exists");
    }
    if (typeof CreateTrack === "function") {
        Trace("E04 FAIL: CreateTrack exists");
    }
    if (typeof NewTrack === "function") {
        Trace("E04 FAIL: NewTrack exists");
    }
}
