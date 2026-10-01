# GNOMO hands

GNOMO can look at the front app, point at a button, and, after you say so,
click, type, or press a key. Status: **UNKNOWN**. The macOS helper has not been
compiled or run yet.

## Use

```sh
companion/build_hands.sh                      # once, on the Mac
python -m gnomo hands look                    # what's in the front window
python -m gnomo hands point "Bounce"          # glide the cursor onto it, no click
python -m gnomo hands click "Bounce"          # asks first, then presses
python -m gnomo hands type "verse 2 idea"     # asks first, then types
python -m gnomo hands key cmd+z               # asks first, then presses
```

First run: macOS asks you to allow `gnomo-hands` under
System Settings > Privacy & Security > Accessibility.

## Who decides

1. **The ladder** (`logic-probe/gnomo/hands.py`). Every request is put into
   words ("click Bounce") and judged. Tier 3 is refused and never reaches the
   helper. Looking and pointing change nothing, so they are tier 0.
2. **You** (`companion/gnomo_hands.swift`). Every click, typed text, and key
   combo opens a native dialog that says exactly what will happen. The default
   button is "Not now". Nothing happens unless you press "Do it". There is no
   flag, mode, or environment variable that skips the dialog.
3. **The kill switch.** If you touched the mouse or keyboard in the 750 ms
   before the gnome acts, he lets go and reports `human_took_over`.

Labels that match more than one thing fail closed with a list of candidates;
pick one with `--index N`.

## What a reply means

`attempted` plus a channel (`ax_press`, `cgevent_click`, `cgevent_keys`,
`cgevent_move`). That is a receipt that the press was sent, not proof that the
app did what you wanted (HONEST_CONTRACT rules 1 and 4). Every request,
including refusals and "Not now", is written to the decision ledger.

## Channel order

Accessibility press before a synthetic click: it targets the element, not a
screen position, so a moved window cannot turn it into a click on something
else. For Logic, MCU and key commands stay the better channels; the cursor is
the last resort.
