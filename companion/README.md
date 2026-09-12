# The face — GNOMO's desk companion

A small, old, stubborn gnome that sits **on the desk** — the photo one, red
hat and headphones, floating in a borderless panel, always on top of every
space. It has a bubble, a place to type, and a tier badge. It does not have
a brain: the window owns no ladder and no mouth.

One companion, one mouth, one ladder — and now, one face. The rules in
[studio/GNOMO.md](../studio/GNOMO.md) did not move. This window is a
**viewer over the CLI**, nothing more:

- Type a decision → `python -m gnomo --json decide "…"`.
- Type `park: …` or `park …` → `python -m gnomo --json park "…"`.
- Type `next` → `python -m gnomo --json next`.
- The bubble shows `spoken`, the badge shows the tier, the gray subtext
  shows the hat, the authority, and whether the mouth actually spoke.

The window never decides, never speaks on its own, and never invents
state. If the CLI fails, the bubble says so in red and that is the truth.

## Build and run

```bash
swiftc -o companion/build/Gnomo companion/main.swift
companion/build/Gnomo
```

No Xcode, no package, no dependencies. One Swift file, one compiler call.
macOS only — the same constraint as the v0 mouth. Off macOS this window
does not exist, and nothing pretends otherwise.

## Selftest

```bash
GNOMO_MUTE=1 companion/build/Gnomo --selftest
```

Runs the three routes against the real CLI and prints a verdict; exits 0
only if every route returned a decision. No window opens. The routing
table itself (including the fail-closed rejects: empty input, bare `park`,
`park:` with nothing after it) is pinned by
[tests/test_companion_router.py](../tests/test_companion_router.py)
against [logic-probe/gnomo/companion_router.py](../logic-probe/gnomo/companion_router.py).

If you change the routing in either place, change both in the same commit.
The Swift `route(_:)` mirrors the Python `route()` by hand; drift between
them is a bug, not a feature.

## The pieces

| Piece | File | What it owns |
| --- | --- | --- |
| The window, bubble, badge, input | `main.swift` | drawing and routing only |
| The movements | `main.swift` `GnomeAnimator` | tier-shaped gestures over one photo |
| The CLI bridge | `main.swift` `Gnomo.run` | `python -m gnomo --json …` over `Process` |
| Routing table (tested) | `logic-probe/gnomo/companion_router.py` | typed text → CLI verb |
| The face | `assets/gnome@128/256/512.png` | lifted from the photo by `scripts/make_gnome_assets.py` |
| The driver (dev tool) | `drive_gnomo.swift` | CGEvent typing for end-to-end tests |

`GNOMO_REPO` overrides the repo root, `GNOMO_PYTHON` the interpreter.
The window position is saved (`GnomoPanelFrame`) and restored on launch.
Drag anywhere to move it. The menu bar item (GNOMO) has *The one thing*,
*Park an idea…*, and *Open the ledger*.

## Honesty notes

- The window cannot read Logic either. It shows what the CLI said, and the
  CLI knows only what `studio/` knows.
- The mouth is still `scripts/speak.py` — `say`, Reed then Samantha. There
  is no second TTS path; the window's "spoken/not spoken" subtext comes
  from the CLI's `voice` record.
- A decision typed into the window lands in the same
  `studio/datasets/decisions.jsonl` ledger as every other decision, with
  the same shape. Same gnome, same paper trail.

## The movements

One photo, honest motion — every move is a CoreAnimation transform on the
same single image. No second character, no sprite swaps, no invented
expressions. The gestures are the ladder made visible:

| Trigger | Move |
| --- | --- |
| idle | slow breathing + a stubborn 9s sway; every 12–22s it glances around the desk |
| app launch | drop-in onto the desk |
| first keystroke in the field | straightens to attention |
| T0 act | a small hop — "doing it" |
| T1 propose | a slow nod — "say the word" |
| T2 ask | a shrug — "your call" |
| T3 refuse | a firm head shake — "no" |
| spoke=true | a quick bounce while the mouth talks |
| CLI failure | a slump — not a decision, and it does not act like one |
| unknown tier | the shrug, never a bold move — same fail-closed rule |

The animation reacts to the CLI's record (tier + spoke) and to nothing
else. It never invents state and never claims a listen.