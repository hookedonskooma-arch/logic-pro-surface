"""Guided setup: one step, checked, then the next. Never all five at once.

GNOMO cannot click Logic's Control Surfaces window. There is no public API
for it, and driving it with Accessibility or CGEvent would be the exact
channel docs/HONEST_CONTRACT.md refuses as a pass bit. So the gnome does the
half it can do honestly (CoreMIDI/IAC), and for the half that needs hands it
gives one instruction at a time and checks the result.

Each step reports done | todo | unknown. `unknown` is load-bearing: steps 3
and 4 happen inside Logic's UI where we have no honest readback, so the gnome
says so instead of guessing. The MCU echo in step 5 is the only pass bit.
"""

from __future__ import annotations

from typing import Any, Callable

DONE = "done"
TODO = "todo"
UNKNOWN = "unknown"


class Step:
    def __init__(
        self,
        *,
        step_id: str,
        title: str,
        spoken: str,
        detail: list[str],
        check: Callable[[], dict[str, Any]],
        fixable: bool = False,
        trap: str | None = None,
        manual: list[str] | None = None,
    ) -> None:
        self.step_id = step_id
        self.title = title
        self.spoken = spoken
        self.detail = detail
        self.check = check
        self.fixable = fixable
        self.trap = trap
        # Shown when the automatic path cannot run. A step the gnome cannot do
        # for you is still a step you can do yourself.
        self.manual = manual or []


def _check_iac() -> dict[str, Any]:
    """Do the two named IAC buses exist? This half needs no hands."""
    from logic_probe import midi_io

    ports = midi_io.snapshot_ports()
    if ports.get("error"):
        return {"state": UNKNOWN, "evidence": ports["error"], "channel": "coremidi"}
    pair = midi_io.select_mcu_pair(ports)
    if pair:
        return {"state": DONE, "evidence": pair, "channel": "coremidi"}
    return {
        "state": TODO,
        "evidence": {"inputs": ports.get("inputs"), "outputs": ports.get("outputs")},
        "channel": "coremidi",
    }


def _check_logic_running() -> dict[str, Any]:
    from logic_probe import host

    reachable = bool(host.logic_reachable())
    return {
        "state": DONE if reachable else TODO,
        "evidence": {"logic_running": reachable},
        "channel": "host_detect",
    }


def _cs_hint() -> dict[str, Any]:
    """Read the control-surface blob. It hints; it never confirms.

    com.apple.logic.pro.cs is an undocumented FORM/SSCF blob and Logic may
    not flush it until quit. A hit here is EXPERIMENTAL evidence at best, so
    the best state this can return is `unknown`.
    """
    from logic_probe import cs_prefs

    try:
        info = cs_prefs.summarize()
    except OSError as exc:
        return {"state": UNKNOWN, "evidence": f"cs_prefs_unreadable:{exc}", "channel": "cs_prefs"}
    if not info.get("exists"):
        return {"state": UNKNOWN, "evidence": "cs_prefs_missing", "channel": "cs_prefs"}
    return {
        "state": UNKNOWN,
        "evidence": {
            "iac_mentioned": info.get("iac_mentioned"),
            "named_ports": info.get("named_ports"),
            "catalog": info.get("catalog"),
            "note": "cs blob is a hint, not a readback; Logic may not flush it until quit",
        },
        "channel": "cs_prefs",
    }


def _check_echo() -> dict[str, Any]:
    """The only pass bit: an independent MCU echo (E06)."""
    from logic_probe import channels

    try:
        env = channels.mixer_set_volume(3, -6.0)
    except Exception as exc:  # noqa: BLE001 — fail closed into the step
        return {"state": UNKNOWN, "evidence": f"probe_failed:{exc}", "channel": "mcu"}
    status = env.get("status")
    readback = (env.get("readback") or {}).get("method")
    return {
        "state": DONE if status == "confirmed" and readback == "mcu_feedback" else TODO,
        "evidence": {"status": status, "readback_method": readback},
        "channel": "mcu",
    }


STEPS: tuple[Step, ...] = (
    Step(
        step_id="iac",
        title="Create the two IAC buses",
        spoken="Step one. I can do this one myself. Say the word and I will make the two I A C buses.",
        detail=[
            "GNOMO does this for you: `python -m gnomo setup mcu --fix`",
            "It brings the IAC Driver online and adds two buses:",
            "  logic-probe-mcu-cmd   (Logic listens here)",
            "  logic-probe-mcu-fb    (Logic answers here)",
            "It does not touch SSL 2+, does not rename Bus 1, does not quit Logic.",
            "Do this BEFORE opening Logic's Setup window, or the ports will not",
            "appear in its dropdowns.",
        ],
        check=_check_iac,
        fixable=True,
        manual=[
            "By hand, if GNOMO cannot reach CoreMIDI:",
            "  1. Open Audio MIDI Setup.app",
            "  2. Window > Show MIDI Studio",
            "  3. Double-click IAC Driver",
            "  4. Tick 'Device is online'",
            "  5. Under Ports, click + twice and name them exactly:",
            "       logic-probe-mcu-cmd",
            "       logic-probe-mcu-fb",
            "  6. Apply",
        ],
    ),
    Step(
        step_id="logic",
        title="Open Logic Pro",
        spoken="Step two. Open Logic Pro, on a scratch project, not your only one.",
        detail=[
            "Open Logic Pro with an empty or scratch project.",
            "Never run setup against the only copy of a song you care about.",
        ],
        check=_check_logic_running,
    ),
    Step(
        step_id="install",
        title="Install Mackie Control",
        spoken="Step three. Logic Pro menu, Control Surfaces, Setup. Then New, Install.",
        detail=[
            "Menu bar:  Logic Pro > Control Surfaces > Setup...",
            "In the Setup window:  New > Install...",
            "Manufacturer: Mackie Designs",
            "Model:        Mackie Control",
            "Click Add.",
        ],
        check=_cs_hint,
        trap="Do NOT use Rebuild Defaults in that window. It wipes the iPad Logic Remote assignment.",
    ),
    Step(
        step_id="ports",
        title="Point it at the two buses",
        spoken="Step four. Input is the command bus. Output is the feedback bus. Do not swap them.",
        detail=[
            "Select the Mackie Control device in the Setup window, then in the",
            "parameter list on the left:",
            "  Input Port  = IAC Driver logic-probe-mcu-cmd",
            "  Output Port = IAC Driver logic-probe-mcu-fb",
            "",
            "Read that twice. Logic's INPUT is where Logic RECEIVES our commands,",
            "so it gets the cmd bus. Logic's OUTPUT is where Logic SENDS its echo",
            "back to us, so it gets the fb bus.",
        ],
        check=_cs_hint,
        trap=(
            "Swapping these is the number one cause of mcu_no_echo: everything looks "
            "assigned, nothing ever echoes, and no error is shown anywhere."
        ),
    ),
    Step(
        step_id="echo",
        title="Prove it with an echo",
        spoken="Step five. Now we find out. Running the fader probe.",
        detail=[
            "PYTHONPATH=logic-probe python3 -m logic_probe mixer set-volume --track 3 --db -6",
            "",
            "E06 is TESTED only on status=confirmed with readback.method=mcu_feedback.",
            "Anything else is uncertain, and uncertain is not pass.",
        ],
        check=_check_echo,
    ),
)


def evaluate() -> list[dict[str, Any]]:
    """Run every check. Import failures degrade to unknown, never to done."""
    out: list[dict[str, Any]] = []
    for step in STEPS:
        try:
            result = step.check()
        except ImportError as exc:
            result = {"state": UNKNOWN, "evidence": f"not_checkable_here:{exc}", "channel": None}
        except Exception as exc:  # noqa: BLE001 — a broken check is never a pass
            result = {"state": UNKNOWN, "evidence": f"check_failed:{exc}", "channel": None}
        out.append(
            {
                "step": step.step_id,
                "title": step.title,
                "spoken": step.spoken,
                "detail": step.detail,
                "trap": step.trap,
                "fixable": step.fixable,
                "manual": step.manual,
                **result,
            }
        )
    return out


def current(results: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """The one step to do now: the first that is not done. None means finished."""
    for row in results if results is not None else evaluate():
        if row["state"] != DONE:
            return row
    return None
