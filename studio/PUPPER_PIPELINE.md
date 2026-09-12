# The puppet pipeline: bust gnome → live full-body companion

The goal: a full-body, transparent-background gnome who lives on the screen,
driven by Chris's webcam and microphone through Adobe Character Animator.
Everything machine-side (poof, teleport, zoom takeover, tier expressions) is
already wired; this is the art + rig pass that replaces the static bust.

## Stage 1 — layered art (Photoshop, on Chris's side)

`companion/assets/gnomo-puppet-scaffold.psd` (440×790) is the scaffold: 12
named layers, one per body part, each holding a colored placeholder block with
its name printed on it.

- hat, head, headphones, beard — head stack
- torso, arm-L/R — body
- hip, leg-L/R, shoe-L/R — legs

**The task:** paint/clone the real gnome art into each named layer, keeping
every part on its own layer (CA needs separable parts to rig). The bust art in
`companion/assets/mockup/` is the character reference; `scraps/probe-hero.png`
is the seated full-body reference. Save as
`companion/assets/gnomo-puppet.psd` when done.

## Stage 2 — rig + perform (Character Animator)

1. File → Import `gnomo-puppet.psd`. CA auto-tags by layer name; fix any
   mis-tags (Independent group per limb, hinge pins at shoulders/hips/knees).
2. Rig → Face: webcam calibrates; Head Turner + Lip Sync (visemes) from mic.
3. Behaviors: Face Tracker + Lip Sync + Auto Blink + Physics (beard gets
   Dangle — it's huge, let it swing).
4. Arm IK for the mugs; walk cycles optional (teleport replaced walking).

## Stage 3 — export to the companion window

Two routes, pick per need:

- **Live puppet (best):** CA renders to a virtual camera or to a Mercury/
  NDI output. If we run a local NDIsender → capture loop, the companion window
  can display the live puppet instead of a static PNG. (Requires a small
  Swift view swap — the seam already knows how to swap images.)
- **Rendered clips (simple):** Export → PNG sequence with alpha for each
  expression/state (idle, listening, thinking, hype, sleepy, error). Drop the
  sequences into `companion/assets/sequences/<state>/`. The window's
  `setFaceImage` becomes a frame-player for the active state.

## What stays true

- The face matches the ladder: T0 happy, T1 thinking, T2 confused, T3 error,
  ears → listening. The puppet inherits these as triggers, not hardcoded swaps.
- Body verbs never ledger; the ladder never sees the VFX.
- One mouth, one ladder, one face — the puppet is still GNOMO, not a second
  speaker.