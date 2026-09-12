"""Routing rules the desk companion shares with the CLI.

The companion window (companion/main.swift) does not own a ladder or a
mouth. It sends typed text to `python -m gnomo --json <verb> <arg>` and
renders the record it gets back. These tests pin the routing table both
sides agree on, so the window can never drift into deciding on its own.

Body verbs (walk / point / zoom / come) move the window's own body. They
never reach the ladder and never ledger — moving a gnome is not a decision
about the studio. Their targets are closed sets: fail closed.

If a route changes here, change companion/main.swift's `route(_:)` in the
same commit. If it changes without this file, the window is inventing a
path to the ladder and that is a bug, not a feature.
"""

from __future__ import annotations

from gnomo.companion_router import cli_argv, route

import pytest


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("next", ("next", None)),
        ("NEXT", ("next", None)),
        ("  next  ", ("next", None)),
        ("park: chop the intro tighter", ("park", "chop the intro tighter")),
        ("park:  double-space idea  ", ("park", "double-space idea")),
        ("park tighter intro", ("park", "tighter intro")),
        ("set track 3 to -6 dB", ("decide", "set track 3 to -6 dB")),
        ("", ("reject", None)),
        ("   ", ("reject", None)),
        ("park:", ("reject", None)),
        ("park: ", ("reject", None)),
        ("park:   ", ("reject", None)),
        ("park", ("reject", None)),
        ("park  ", ("reject", None)),
        ("how does the mix sound", ("decide", "how does the mix sound")),
    ],
)
def test_route(typed: str, expected: tuple[str, str | None]) -> None:
    assert route(typed) == expected


class TestBodyVerbs:
    """walk / come / point / zoom — the window's own body, fail closed."""

    @pytest.mark.parametrize(
        ("typed", "expected"),
        [
            ("come", ("walk", "here")),
            ("come here", ("walk", "here")),
            ("COME HERE", ("walk", "here")),
            ("walk", ("walk", "random")),
            ("WALK", ("walk", "random")),
            ("walk left", ("walk", "left")),
            ("walk right", ("walk", "right")),
            ("walk center", ("walk", "center")),
            ("walk random", ("walk", "random")),
            ("walk here", ("walk", "here")),
            ("zoom", ("zoom", "toggle")),
            ("zoom in", ("zoom", "in")),
            ("zoom out", ("zoom", "out")),
            ("zoom normal", ("zoom", "normal")),
            ("zoom toggle", ("zoom", "toggle")),
            ("ZOOM IN", ("zoom", "in")),
            ("point at the mixer", ("point", "at the mixer")),
            ("point to Chrome", ("point", "to Chrome")),
        ],
    )
    def test_body_routes(self, typed: str, expected: tuple[str, str | None]) -> None:
        assert route(typed) == expected

    @pytest.mark.parametrize(
        "typed",
        [
            "walk up",           # not a target — fail closed
            "walk to the moon",  # not a target
            "zoom sideways",    # not a zoom arg
            "zoom to eleven",   # not a zoom arg
            "point",            # nothing to point at
            "point ",           # nothing to point at
        ],
    )
    def test_body_fail_closed(self, typed: str) -> None:
        assert route(typed) == ("reject", None)

    def test_body_verbs_never_reach_the_ladder(self) -> None:
        """walk/zoom are not decisions. They must not fall through to decide."""
        verb, _ = route("walk left")
        assert verb not in {"decide", "next", "park"}


def test_route_never_invents_a_verb() -> None:
    """Anything not next/park/body goes to decide. The window adds no verbs."""
    assert route("frobnicate the widget")[0] == "decide"


def test_route_rejects_empty_park() -> None:
    """`park:` with no idea is not a park. It is not a decide either.

    An empty park string must not reach the parking lot — PARKING_LOT.md
    is for caught ideas, and an empty line would be fake data.
    """
    verb, arg = route("park:")
    assert verb == "reject"
    assert arg is None


# --- plan: the composition body verb ------------------------------------------

class TestPlanVerb:
    def test_plan_with_path_routes(self) -> None:
        verb, arg = route("plan ~/plans/shoegaze.json")
        assert verb == "plan"
        assert arg == "~/plans/shoegaze.json"

    @pytest.mark.parametrize(
        "typed",
        [
            "plan",       # no path — nothing to compile
            "plan ",      # whitespace only
            "plan:",      # colon form is not a plan verb
        ],
    )
    def test_plan_fail_closed(self, typed: str) -> None:
        assert route(typed) == ("reject", None)

    def test_plan_is_not_a_ladder_decision(self) -> None:
        """plan is a compile, not a decision: never decide/next/park."""
        verb, _ = route("plan /tmp/x.json")
        assert verb == "plan"
        assert verb not in {"decide", "next", "park"}

    def test_plan_argv_is_the_nonsend_compile(self) -> None:
        """The window may compile but must never play: argv has no --go."""
        argv = cli_argv("plan", "/tmp/x.json")
        assert argv == [
            "-m", "gnomo", "--quiet", "--json", "plan", "--file", "/tmp/x.json",
        ]
        assert "--go" not in argv
        assert "play" not in argv