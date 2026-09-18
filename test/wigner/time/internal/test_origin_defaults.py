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


def test_a_start_value_does_not_depend_on_unrelated_variables():
    """
    The bound was recomputed inside the per-variable loop while the loop mutated the
    times it measured from, so adding an unrelated variable to the same `ramp` moved
    another variable's start value -- 20.0 alone, 10.0 in company.
    """
    base = tl.stack(
        tl.create(b__A=10.0, a__A=0.0, t=0.0, context="s"),
        tl.anchor(5.0, context="s"),
        tl.update(b__A=20.0, t=6.0, context="s", origin=0.0),
    )
    alone = tl.ramp(timeline=base, duration=1.0, b__A=[[0.5, 0.0], [0.5, 3.0]])
    company = tl.ramp(
        timeline=base, duration=1.0, b__A=[[0.5, 0.0], [0.5, 3.0]], a__A=1.0
    )
    value__b = lambda t: t[(t["variable"] == "b__A") & (t["function"].notna())][
        "value"
    ].tolist()[0]
    assert value__b(alone) == value__b(company) == pytest.approx(10.0)


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
