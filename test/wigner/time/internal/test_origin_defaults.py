"""
Origin defaults complete a partial pair, slot by slot, over a terminal chain.

`None` in a slot means *defer to the caller's default for this slot*; `0.0` means
*absolute -- no shift*. Keeping those apart is what makes the documented interweaving
shorthand mean what it reads as (A6), and the chain's terminal step is what stops a
`ramp` landing before the rows it was appended to (A4).

Settled with the maintainer on 2026-09-18; see `docs/origin-resolution.md`.
"""

import pytest

from wignertime import config as wt_config
from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import origin as wt_origin


@pytest.fixture
def tline():
    """`coil__A` holds 2.0 through `stage1` (anchor at t=1.0), then 5.0 from t=1.5."""
    return tl.stack(
        tl.create(coil__A=2.0, t=0.0, context="stage1"),
        tl.anchor(1.0, context="stage1"),
        tl.update(coil__A=5.0, t=1.5, context="stage2", origin=0.0),
        tl.anchor(2.5, context="stage2"),
    )


def points(timeline):
    return timeline[timeline["function"].notna()][["time", "value"]].values.tolist()


# --- A6: a partial origin is completed, not replaced --------------------------


def test_the_interweaving_shorthand_keeps_ramps_value_default(tline):
    """
    `sec:interweaving` teaches `origin=<context>`. It pads to `[ctx, None]`, and while
    `None` meant "absolute" that cancelled `ramp`'s value default and started the ramp
    from 0.0 -- on a coil, a full-scale current swing at ramp speed, silently.
    """
    assert points(
        tl.ramp(timeline=tline, coil__A=9.0, duration=0.5, origin="stage1")
    ) == [
        [1.0, 2.0],
        [1.5, 9.0],
    ]


def test_the_shorthand_agrees_with_the_explicit_pair(tline):
    assert points(
        tl.ramp(timeline=tline, coil__A=9.0, duration=0.5, origin="stage1")
    ) == points(
        tl.ramp(
            timeline=tline, coil__A=9.0, duration=0.5, origin=["stage1", "variable"]
        )
    )


def test_a_deferred_time_slot_takes_the_chain(tline):
    """
    `[None, "variable"]` is the honest spelling of `ramp`'s own default: it asks for the
    caller's time reference rather than naming one it cannot guarantee. It used to be a
    raw `TypeError` (B7).
    """
    assert points(
        tl.ramp(timeline=tline, coil__A=9.0, duration=0.5, origin=[None, "variable"])
    ) == points(
        tl.ramp(
            timeline=tline, coil__A=9.0, duration=0.5, origin=["anchor", "variable"]
        )
    )


def test_update_values_stay_absolute(tline):
    """Completion must not give `update` a value origin it never had."""
    new = tl.update(tline, coil__A=1.0, t=0.0, origin="stage1")
    assert new.iloc[-1]["value"] == pytest.approx(1.0)


def test_zero_still_means_absolute(tline):
    new = tl.update(tline, coil__A=1.0, t=2.0, origin=0.0)
    assert new.iloc[-1]["time"] == pytest.approx(2.0)


# --- A4: the chain is terminal ------------------------------------------------


def test_a_ramp_onto_an_anchorless_timeline_does_not_precede_it():
    """
    `ramp`'s chain had no `"last"` step, so it fell off the end and the rows landed in
    absolute time -- here at 0.0 -> 1.0, i.e. *before* the entry at t=5.0 they were
    appended to. No exception, and the sequence was not merely mistimed but reordered.
    """
    base = tl.create(coil__A=0.0, t=5.0, context="stage1")
    assert points(tl.ramp(timeline=base, coil__A=2.0, duration=1.0)) == [
        [5.0, 0.0],
        [6.0, 2.0],
    ]


def test_ramps_chain_carries_the_value_default_at_every_step():
    """Both entries must name `"variable"`, or the fallback would silently change kind."""
    assert [entry[1] for entry in wt_config.ORIGIN__DEFAULTS__RAMP] == [
        "variable",
        "variable",
    ]


def test_the_chain_terminates_in_absolute_time_with_a_warning(caplog):
    assert wt_origin.auto(None, None, origin__defaults=wt_config.ORIGIN__DEFAULTS) == [
        0.0,
        None,
    ]
    assert "absolute time" in caplog.text


def test_an_explicit_anchor_without_one_says_so(tline):
    """The default path falls through; an explicit request cannot, so it must explain."""
    base = tl.create(coil__A=0.0, t=5.0, context="stage1")
    with pytest.raises(ValueError, match="holds no anchor"):
        tl.update(base, coil__A=1.0, t=1.0, origin="anchor")


# --- B2: the lookup bound does not depend on what else is being resolved ------


def test_the_bound_does_not_move_as_the_loop_runs():
    """
    The bound was recomputed inside the per-variable loop, from the very frame
    `_update_future` was mutating -- so once `x__A` had been shifted, the measured
    minimum rose and `y__A` was resolved against a later instant than the one its rows
    actually occupy.

    Here the fragment starts at t=5.0, and `y__A` still held 2.0 then; it does not step
    to 8.0 until t=7.0. Measured against `fba0fe0`, the commit before the hoist, this
    gave 8.0.
    """
    base = tl.stack(
        tl.create(x__A=1.0, y__A=2.0, t=0.0, context="s"),
        tl.anchor(5.0, context="s"),
        tl.update(y__A=8.0, t=7.0, context="s", origin=0.0),
        tl.update(x__A=9.0, t=10.0, context="s", origin=0.0),
    )
    new = tl.update(
        base, origin=["anchor", "variable"], x__A=[[0.0, 0.0]], y__A=[[3.0, 0.0]]
    )
    assert new.iloc[-1]["variable"] == "y__A"
    assert new.iloc[-1]["value"] == pytest.approx(2.0)


def test_the_bound_is_the_instant_the_rows_will_occupy(tline):
    """
    Not the variable's last value in the timeline as a whole: `coil__A` ends at 5.0, but
    at `stage1` it held 2.0, and that is what an operation interwoven there must see.
    """
    assert points(
        tl.ramp(
            timeline=tline, coil__A=9.0, duration=0.5, origin=["stage1", "variable"]
        )
    )[0][1] == pytest.approx(2.0)


# --- B8 and the diagnostics ---------------------------------------------------


def test_an_empty_timeline_says_it_is_empty():
    empty = wt_frame.new([], columns=tl._SCHEMA.keys()).astype(tl._SCHEMA)
    with pytest.raises(ValueError, match="the timeline is empty"):
        tl.update(empty, coil__A=1.0, t=1.0, origin="last")


def test_a_variable_with_no_history_says_so(tline):
    with pytest.raises(ValueError, match="No previous value of 'fresh__A'"):
        tl.ramp(timeline=tline, fresh__A=1.0, duration=0.5, origin=0.0)


# --- a variable appearing for the first time in a ramp ------------------------
#
# A ramp runs from where the variable currently sits, so a variable with no history has
# no start. Before the per-slot completion (2026-09-18) an explicit `origin=0.0` left
# the value slot empty and the ramp began at 0.0 -- an invented physical assumption (0 A
# on an uninitialised coil is a command, not a neutral default). Completion gives the
# value slot `"variable"`, so the same call now refuses, and the two ways of saying what
# was meant are both explicit.


def test_a_ramp_of_an_unset_variable_refuses(tline):
    with pytest.raises(ValueError, match="No previous value of 'fresh__A'"):
        tl.ramp(timeline=tline, fresh__A=5.0, duration=0.5)


def test_a_ramp_of_an_unset_variable_refuses_even_with_a_time_origin(tline):
    """This one used to start the ramp at 0.0 without comment."""
    with pytest.raises(ValueError, match="No previous value of 'fresh__A'"):
        tl.ramp(timeline=tline, fresh__A=5.0, duration=0.5, origin=0.0)


def test_an_unset_variable_can_start_from_a_stated_value(tline):
    """An absolute value origin: defer the time to the default, state the value."""
    assert points(
        tl.ramp(timeline=tline, fresh__A=5.0, duration=0.5, origin=[None, 0.0])
    ) == [[3.5, 0.0], [4.0, 5.0]]


def test_an_unset_variable_can_state_both_ends(tline):
    """The other escape, and the one the 2-D form exists for."""
    assert points(tl.ramp(timeline=tline, fresh__A=[[0.0, 0.0], [0.5, 5.0]])) == [
        [3.5, 0.0],
        [4.0, 5.0],
    ]


def test_a_per_variable_self_reference_places_each_on_its_own_history(tline):
    """
    `["variable", "variable"]` is the general form of what the 2025-era tests spelled by
    naming one variable in both slots. It differs from the default, which follows the
    most recent anchor rather than each variable's own last row.
    """
    assert points(
        tl.ramp(
            timeline=tline,
            coil__A=9.0,
            t=5.0,
            duration=1.0,
            origin=["variable", "variable"],
        )
    ) == points(
        tl.ramp(
            timeline=tline,
            coil__A=9.0,
            t=5.0,
            duration=1.0,
            origin=["coil__A", "variable"],
        )
    )
