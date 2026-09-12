# GNOMO / Logic Pro Companion
## Failure-Driven Architecture — Narrowed Product Build

**GOAL (2026-09-12, Chris): product ready.** Everything built must be live-verified,
shipped, and honest before anything new is built. That means: the composition
seam (v0.1 chords + v0.2 melody) proven audible through the hands step, the
body committed through the ship workflow's gates (A body works → B merged →
C desk test), suite green, docs truthful. The further ladder (bass, melody
variants, arrangement, AU selection, parameters, session analysis, mixing)
stays earned-later: no layer starts until the previous one is product-ready.

### Core premise

Instead of starting by writing every piece of code that *might* build the product, start by identifying implementations that will fail, eliminating them, and building the smallest architecture that survives.

> **Do not begin with "what code could build this?"**
>
> Begin with **"what implementations would fail, why would they fail, and what is the smallest surviving architecture?"**

The target is a Logic Pro companion that can translate human musical intent into structured composition and eventually interact with instruments, effects, and AU plugins. Logic's native third-party plug-in format is Audio Units (AU/AUv3) — never VST (see docs/HONEST_CONTRACT.md rule 7).

---

## 1. Reject the architectures that fail first

### Failure: LLM directly controls all of Logic Pro

Why it fails:

- nondeterministic behavior
- difficult to debug
- dangerous state changes
- unclear action history
- difficult recovery when the model misunderstands the session

**Rule:** The language model proposes actions. A deterministic execution layer performs approved actions.

---

### Failure: Natural language directly becomes a finished song

Why it fails:

- scope is too broad
- difficult to evaluate individual failures
- duplicates text-to-music systems instead of creating a DAW companion
- composition, arrangement, performance, synthesis, mixing, and DAW manipulation become one inseparable problem

**Rule:** Introduce structured musical representations between language and audio.

---

### Failure: LLM blindly generates arbitrary MIDI

Why it fails:

- syntactically valid MIDI can still be musically incoherent
- no guaranteed relationship between harmony, melody, rhythm, instrumentation, and user intent
- difficult to enforce musical constraints

**Rule:** Generate a constrained `MusicPlan`, validate it, then deterministically compile it into MIDI.

---

### Failure: Agent continuously observes the entire DAW

Why it fails:

- excessive context
- unnecessary state synchronization
- irrelevant information enters the reasoning loop
- higher latency and cost
- difficult to determine which state actually matters

**Rule:** Request only the minimum DAW state necessary for the current action.

---

### Failure: Build a custom instrument plug-in first

Why it fails:

- large engineering burden
- doesn't prove the intelligence layer
- combines DSP/plugin engineering with agent architecture before either is validated

**Rule:** Use Logic's existing MIDI/instrument environment first. (The plug-in format here is AU only — VST is not a Logic format; treating it as one is itself a failure to eliminate.)

---

### Failure: Let the model invent plugins, presets, and parameters

Why it fails:

- hallucinated plugin names
- nonexistent parameters
- unsupported parameter ranges
- preset mismatch

**Rule:** Eventually give the model a verified plugin registry rather than unrestricted plugin vocabulary.

---

### Failure: One giant agent

Why it fails:

- failures become difficult to isolate
- testing is poor
- composition and DAW execution become entangled
- difficult to reproduce behavior

**Rule:** Separate planning, validation, compilation, and execution.

---

# 2. Surviving architecture

```text
USER INTENT
    |
    v
SEMANTIC / MUSIC PLANNER
    |
    v
MUSIC PLAN
    |
    v
SCHEMA VALIDATOR
    |
    v
MIDI / COMMAND COMPILER
    |
    v
LOGIC BRIDGE
    |
    v
LOGIC PRO
```

The model does **not** receive unrestricted authority over Logic.

The critical boundary is:

```text
AI DECISION
     |
     v
STRUCTURED PLAN
-------------------- SAFETY / DETERMINISM WALL
     |
     v
VALIDATION
     |
     v
DAW EXECUTION
```

---

# 3. GNOMO v0.1

The first product should do one thing extremely well:

> **The user describes a musical idea. GNOMO creates a structured musical plan and places a valid MIDI region into Logic Pro.**

Example request:

```text
Give me an 8-bar sad shoegaze progression
that becomes darker during bars 5-8.
```

Possible internal representation:

```json
{
  "tempo": 88,
  "key": "D minor",
  "length_bars": 8,
  "chords": [
    "Dm9",
    "Bbmaj7",
    "Fadd9",
    "C",
    "Dm9",
    "Bbmaj7",
    "Gm9",
    "A7sus4"
  ],
  "voicing": "wide",
  "register": "mid",
  "velocity_range": [48, 76]
}
```

The language model stops here.

A deterministic system converts this specification into notes and DAW actions.

---

# 4. Six initial components

## A. Intent Parser

Input:

```text
sad, nostalgic, 8 bars, shoegaze
```

Output:

```json
{
  "emotion": ["sad", "nostalgic"],
  "genre": ["shoegaze"],
  "bars": 8
}
```

Responsibilities:

- extract musical intent
- normalize user terminology
- identify constraints
- reject impossible/ambiguous values when necessary

It does **not** manipulate Logic.

---

## B. Music Planner

Transforms normalized intent into musical decisions.

Initial responsibilities:

- key
- BPM
- meter
- chord sequence
- harmonic rhythm
- register
- dynamics
- density
- voicing intent

Later versions can add:

- melody
- bass
- drums
- arrangement
- articulation
- transitions
- orchestration

---

## C. Schema Validator

Nothing reaches Logic until it passes validation.

Example constraints:

```text
bars >= 1
bars <= 32

tempo >= 40
tempo <= 220

MIDI note >= 0
MIDI note <= 127

velocity >= 0
velocity <= 127

recognized chord symbols only
recognized meters only
recognized instrument roles only
```

The validator is deliberately boring.

That is a feature.

It creates a deterministic boundary around probabilistic model output.

---

## D. MIDI Compiler

This should initially contain **no generative AI**.

Example pipeline:

```text
Chord Symbol
    |
    v
Pitch Classes
    |
    v
Voicing Rules
    |
    v
MIDI Notes
    |
    v
Timing
    |
    v
Velocity
    |
    v
MIDI Region
```

This component should be unit-testable.

Given the same `MusicPlan`, it should produce the same result unless explicitly configured for controlled variation.

---

## E. Logic Bridge

Do not expose all possible Logic actions.

Start with the smallest useful command surface.

Candidate v0.1 operations:

```text
get tempo
set tempo

get selected track

create MIDI region
insert MIDI notes

play
stop

undo
```

Additional capabilities should only be added when a concrete product feature requires them.

---

## F. GNOMO Interface

The first interface does not need the final animated character system.

Minimal version:

```text
+-----------------------------+
| GNOMO                       |
|                             |
| "What are we making?"       |
|                             |
| > sad 8-bar guitar loop     |
|                             |
| [PREVIEW PLAN]              |
| [PUT INTO LOGIC]            |
+-----------------------------+
```

The final animated GNOMO embodiment can sit on top of a proven musical engine.

---

# 5. Do not solve AU plug-in control first

Eventually the architecture can become:

```text
MIDI
 |
 v
INSTRUMENT ROLE
 |
 v
PLUGIN SELECTION
 |
 v
PRESET SELECTION
 |
 v
PARAMETER CONTROL
 |
 v
AUDIO
```

But GNOMO v0.1 should stop earlier:

```text
INTENT
 |
 v
COMPOSITION
 |
 v
MIDI
 |
 v
LOGIC
```

Do not initially attempt to support every Neural DSP, Kontakt, Alchemy, Serum, FabFilter, Darkglass, or third-party plugin configuration.

Plugin intelligence becomes its own layer after composition-to-Logic works reliably.

---

# 6. First real vertical slice

### User

```text
Make me an eight-bar sad progression in D minor.
```

### GNOMO MusicPlan

```text
Tempo: 86 BPM
Key: D minor

Dm9
Bbmaj7
Fadd9
C
Dm9
Bbmaj7
Gm9
A7
```

### User interaction

```text
[Preview]
[Insert Into Selected Logic Track]
[Reject]
```

### Expected result

Logic Pro contains a correctly timed eight-bar MIDI region on the selected track.

That is the first meaningful definition of **working**.

---

# 7. Product expansion sequence

## v0.1

```text
TEXT -> CHORD MIDI
```

## v0.2

```text
TEXT -> CHORDS + MELODY
```

## v0.3

```text
TEXT -> CHORDS + MELODY + BASS
```

## v0.4

```text
TEXT -> ARRANGEMENT
```

## v0.5

```text
ARRANGEMENT -> AU SELECTION
```

## v0.6

```text
PLUGIN PARAMETER CONTROL
```

## Later

```text
SESSION ANALYSIS
       +
COMPOSITION
       +
ARRANGEMENT
       +
PLUGIN CONTROL
       +
MIXING ASSISTANCE
       +
GNOMO CHARACTER / ANIMATION
```

Each layer is earned by proving the previous layer.

---

# 8. The fundamental execution rule

Never make the default architecture:

```text
LLM
 |
 v
RAW MOUSE / KEYBOARD ACTIONS
```

Prefer:

```text
LLM
 |
 v
JSON MUSIC PLAN
 |
 v
VALIDATOR
 |
 v
COMMAND COMPILER
 |
 v
LOGIC BRIDGE
 |
 v
LOGIC PRO
```

UI automation should be a fallback only where Logic exposes no sufficiently reliable integration route.

---

# 9. Coding order

The initial engineering sequence should be:

1. Define `MusicPlan` JSON schema.
2. Generate one valid `MusicPlan`.
3. Validate the plan.
4. Convert `MusicPlan` into MIDI.
5. Get that MIDI into Logic Pro.
6. Add preview / accept / reject / undo.
7. Test the complete round trip repeatedly.
8. Only then expand musical complexity.
9. Add AU plug-in intelligence after the composition bridge is stable. Never write "VST/AU" again in this repo: Logic is AU-only (E08).
10. Add the final GNOMO character/UI after the engine proves useful.

---

# 10. First engineering question

The first seam to prove is:

> **Can structured JSON reliably become an eight-bar MIDI region inside Logic Pro?**

If the answer is **no**, stop and solve that seam.

Do not spend time on:

- animated GNOMO
- broad agent autonomy
- hundreds of plugin integrations
- sophisticated prompt engineering
- complete song generation

until the seam works.

If the answer is **yes**, the backbone exists:

```text
HUMAN INTENT
     |
     v
MACHINE-READABLE MUSICAL INTENT
     |
     v
DETERMINISTIC MUSICAL EVENTS
     |
     v
DAW EXECUTION
```

---

# 11. Connection to the original whiteboard concept

The broader concept can eventually become:

```text
STORY / FEELING / DESCRIPTION
            |
            v
SEMANTIC INTERPRETATION
            |
            v
STRUCTURED MUSIC / "SHEET MUSIC"
            |
            +---- GENRE TAGS
            |
            +---- ARRANGEMENT CUES
            |
            v
MIDI / MUSICAL EVENTS
            |
            v
AU / LOGIC INSTRUMENTS
            |
            v
AUDIO
```

The important innovation is the intermediate representation.

Rather than relying entirely on:

```text
TEXT -> AUDIO
```

GNOMO can reason through:

```text
TEXT
 -> MUSICAL INTENT
 -> COMPOSITION
 -> EVENTS
 -> INSTRUMENTS
 -> AUDIO
```

That gives the system inspectable decisions, editability, deterministic execution, and a natural connection to a professional DAW workflow.

---

## Immediate milestone

**Build only enough software to prove:**

```text
Prompt
  ->
MusicPlan JSON
  ->
Validation
  ->
MIDI
  ->
Logic Pro
```

Everything else remains outside the v0.1 scope until this loop works.

---

## 12. Applied to this repo (2026-09-11)

The concept turned on its own inventory. Eliminations found:

**Eliminated: two vehicles for one proof.** E02 (AU MIDI FX phrase hash) has
two unproven vehicles: the `audio-unit/` stub and the extracted MELEGI aumi.
Failure-driven rule: keep one. The stub survives only as the E09 render-path
fixture (no-malloc/no-lock static scan). The E02 proof rides MELEGI — it is
the product's own instrument. Do not finish the stub for E02's sake.

**Eliminated: "full AU spine" as the parked unit.** The Phase-4 item
"compile → validate → Logic → audio" per the guide is this doc's v0.5, not
v0.1. It shrinks to: prove the composition seam via MELEGI (E02 live) + the
E12 readback below. The full spine is earned later, per this doc's ladder.

**Eliminated: region placement as a solved seam.** Logic has no public
project API: no create-region op exists in any VERIFIED row of
docs/CAPABILITY_MATRIX.md. The honest v0.1 endpoint is: MELEGI aumi
live-plays the compiled MIDI into a record-armed scratch track, and Chris
Consolidates/Joins by hand. Deterministic wall intact; human hands at the
one seam no API crosses.

**New rule found by the concept: the composition seam needs its readback
defined before coding.** Honest contract rule 4 — confirmed requires
evidence from a different path than the one written. For composition:

- machine evidence: CoreMIDI capture of the aumi's output (E12 fixture)
- human receipt: Chris hears it on the instrument and consolidates

Capture alone proves notes were SENT, not that Logic played them. Both, or
the status is `uncertain`.

**Validated: the bot fleet.** This doc's "one giant agent" failure is the
fleet architecture in reverse — gnomo-closer/shipper/launcher/parked are the
planner/validator/executor split at process level: isolated, gated, own
SOUL, own tests. The same profile-per-role pattern is the template for the
future composition split (planner / compiler / bridge). Not built now —
Gate discipline holds.

**Taste note for the MusicPlan schema.** Voicing ("wide"), register, and
velocity_range are taste, not math. They enter the schema as explicit
fields with defaults Chris ratifies once — then frozen. The deterministic
compiler never invents taste; it compiles the ratified constants.

**Surviving composition v0.1 — smallest architecture that survives:**

```text
INTENT (typed or spoken → existing companion router)
  -> MUSIC PLAN JSON (planner; the only LLM touchpoint, stops at the plan)
  -> VALIDATOR (third instance of the boring-schema pattern:
     envelope schema, decision ladder, now music plan)
  -> MIDI COMPILER (the only genuinely new component; deterministic,
     unit-testable, no AI in it)
  -> MELEGI aumi MIDI FX -> record-armed scratch track
  -> CHRIS consolidates by hand (the honest region placement)
  -> readback: CoreMIDI capture + human receipt (E12 pass bit)
```

First seam to prove, restated honestly: **can a validated MusicPlan become
audible MIDI on a Logic track, with capture + human receipt?** Region
placement is not part of the machine seam and must not be promised.
