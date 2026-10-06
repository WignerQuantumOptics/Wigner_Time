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
from wignertime.timeline import build as tl
from wignertime.internal import tags as wt_tags
from wignertime.timeline.internal import stages as wt_stages
from wignertime.internal import dataframe as wt_frame
from wignertime.timeline.internal import origin as wt_origin


@pytest.fixture
def tline():
    """`coil__A` holds 2.0 through `stage1` (anchor at t=1.0), then 5.0 from t=1.5."""
    return tl.to_timeline(
        tl.stack(
            tl.anchor(1.0, context="stage1"),
            tl.update(coil__A=5.0, time=1.5, context="stage2", origin=0.0),
            tl.anchor(2.5, context="stage2"),
        ),
        onto=tl.to_timeline(tl.update(coil__A=2.0, time=0.0, context="stage1")),
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
        tl.to_timeline(tl.ramp(coil__A=9.0, duration=0.5, origin="stage1"), onto=tline)
    ) == [
        [1.0, 2.0],
        [1.5, 9.0],
    ]


def test_the_shorthand_agrees_with_the_explicit_pair(tline):
    assert points(
        tl.to_timeline(tl.ramp(coil__A=9.0, duration=0.5, origin="stage1"), onto=tline)
    ) == points(
        tl.to_timeline(
            tl.ramp(coil__A=9.0, duration=0.5, origin=["stage1", wt_tags.VARIABLE]),
            onto=tline,
        )
    )


def test_a_deferred_time_slot_takes_the_chain(tline):
    """
    `[None, "variable"]` is the honest spelling of `ramp`'s own default: it asks for the
    caller's time reference rather than naming one it cannot guarantee. It used to be a
    raw `TypeError` (B7).
    """
    assert points(
        tl.to_timeline(
            tl.ramp(coil__A=9.0, duration=0.5, origin=[None, wt_tags.VARIABLE]),
            onto=tline,
        )
    ) == points(
        tl.to_timeline(
            tl.ramp(
                coil__A=9.0, duration=0.5, origin=[wt_tags.ANCHOR, wt_tags.VARIABLE]
            ),
            onto=tline,
        )
    )


def test_update_values_stay_absolute(tline):
    """Completion must not give `update` a value origin it never had."""
    new = tl.to_timeline(tl.update(coil__A=1.0, time=0.0, origin="stage1"), onto=tline)
    assert new.iloc[-1]["value"] == pytest.approx(1.0)


def test_zero_still_means_absolute(tline):
    new = tl.to_timeline(tl.update(coil__A=1.0, time=2.0, origin=0.0), onto=tline)
    assert new.iloc[-1]["time"] == pytest.approx(2.0)


# --- A4: the chain is terminal ------------------------------------------------


def test_a_ramp_onto_an_anchorless_timeline_does_not_precede_it():
    """
    `ramp`'s chain had no `"last"` step, so it fell off the end and the rows landed in
    absolute time -- here at 0.0 -> 1.0, i.e. *before* the entry at t=5.0 they were
    appended to. No exception, and the sequence was not merely mistimed but reordered.
    """
    base = tl.to_timeline(tl.update(coil__A=0.0, time=5.0, context="stage1"))
    assert points(tl.to_timeline(tl.ramp(coil__A=2.0, duration=1.0), onto=base)) == [
        [5.0, 0.0],
        [6.0, 2.0],
    ]


def test_ramps_chain_carries_the_value_default_at_every_step():
    """Both entries must name `VARIABLE`, or the fallback would silently change kind."""
    assert [entry[1] for entry in wt_config.ORIGIN__DEFAULTS__RAMP] == [
        wt_tags.VARIABLE,
        wt_tags.VARIABLE,
    ]


def test_the_chain_terminates_in_absolute_time_without_a_warning(caplog):
    """
    Nothing is satisfiable only on an empty timeline, where absolute zero is the one
    answer. The warning that came with it would fire once per experiment since #85, when
    every timeline starts from an empty one (C7, item 3).
    """
    assert wt_origin.auto(None, None, origin__defaults=wt_config.ORIGIN__DEFAULTS) == [
        0.0,
        None,
    ]
    assert caplog.text == ""


def test_an_explicit_anchor_without_one_says_so(tline):
    """The default path falls through; an explicit request cannot, so it must explain."""
    base = tl.to_timeline(tl.update(coil__A=0.0, time=5.0, context="stage1"))
    with pytest.raises(ValueError, match="holds no anchor"):
        tl.to_timeline(
            tl.update(coil__A=1.0, time=1.0, origin=wt_tags.ANCHOR), onto=base
        )


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
    base = tl.to_timeline(
        tl.stack(
            tl.anchor(5.0, context="s"),
            tl.update(y__A=8.0, time=7.0, context="s", origin=0.0),
            tl.update(x__A=9.0, time=10.0, context="s", origin=0.0),
        ),
        onto=tl.to_timeline(tl.update(x__A=1.0, y__A=2.0, time=0.0, context="s")),
    )
    new = tl.to_timeline(
        tl.update(
            origin=[wt_tags.ANCHOR, wt_tags.VARIABLE],
            x__A=[[0.0, 0.0]],
            y__A=[[3.0, 0.0]],
        ),
        onto=base,
    )
    assert new.iloc[-1]["variable"] == "y__A"
    assert new.iloc[-1]["value"] == pytest.approx(2.0)


def test_the_bound_is_the_instant_the_rows_will_occupy(tline):
    """
    Not the variable's last value in the timeline as a whole: `coil__A` ends at 5.0, but
    at `stage1` it held 2.0, and that is what an operation interwoven there must see.
    """
    assert points(
        tl.to_timeline(
            tl.ramp(coil__A=9.0, duration=0.5, origin=["stage1", wt_tags.VARIABLE]),
            onto=tline,
        )
    )[0][1] == pytest.approx(2.0)


def test_the_bound_admits_nothing_after_the_instant():
    """
    The bound used to be widened by `config.TIME_RESOLUTION`, so a value commanded up to
    1 us *after* the instant counted as already in effect, and this ramp started from
    2.0. Nothing else in the suite, the Lab2 fixture included, told the two apart (#94).
    """
    base = tl.to_timeline(
        tl.stack(
            tl.update(coil__A=1.0, time=0.0, context="setup"),
            tl.update(coil__A=2.0, time=0.5e-6, origin=0.0),
        )
    )
    ramped = tl.to_timeline(
        tl.ramp(coil__A=5.0, time=0.0, duration=1e-3, origin=[0.0, wt_tags.VARIABLE]),
        onto=base,
    )
    assert ramped[ramped["time"] == 0.0]["value"].iloc[-1] == pytest.approx(1.0)


# --- B8 and the diagnostics ---------------------------------------------------


def test_an_empty_timeline_says_it_is_empty():
    empty = wt_frame.new([], columns=wt_stages.SCHEMA.keys()).astype(wt_stages.SCHEMA)
    with pytest.raises(ValueError, match="the timeline is empty"):
        tl.to_timeline(
            tl.update(coil__A=1.0, time=1.0, origin=wt_tags.LAST), onto=empty
        )


def test_a_variable_with_no_history_says_so(tline):
    with pytest.raises(ValueError, match="No previous value of 'fresh__A'"):
        tl.to_timeline(tl.ramp(fresh__A=1.0, duration=0.5, origin=0.0), onto=tline)


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
        tl.to_timeline(tl.ramp(fresh__A=5.0, duration=0.5), onto=tline)


def test_a_ramp_of_an_unset_variable_refuses_even_with_a_time_origin(tline):
    """This one used to start the ramp at 0.0 without comment."""
    with pytest.raises(ValueError, match="No previous value of 'fresh__A'"):
        tl.to_timeline(tl.ramp(fresh__A=5.0, duration=0.5, origin=0.0), onto=tline)


def test_an_unset_variable_has_to_be_set_first(tline):
    """
    A ramp starts where its variable is (#142, 2026-09-29), so there is no start to state
    for one that has never been set. The two escapes this replaces -- an absolute value
    origin, `origin=[None, 0.0]`, and the 2-D form stating both ends -- are refused, and
    the message says what to write.
    """
    for stage in (
        tl.ramp(fresh__A=5.0, duration=0.5),
        tl.ramp(fresh__A=5.0, duration=0.5, origin=[None, wt_tags.VARIABLE]),
    ):
        with pytest.raises(ValueError, match="update` it first"):
            tl.to_timeline(stage, onto=tline)

    with pytest.raises(ValueError, match="value slot of its `origin`"):
        tl.ramp(fresh__A=5.0, duration=0.5, origin=[None, 0.0])
    with pytest.raises(ValueError, match="its start is not written: fresh__A"):
        tl.to_timeline(tl.ramp(fresh__A=[[0.0, 0.0], [0.5, 5.0]]), onto=tline)

    set_first = tl.stack(tl.update(fresh__A=0.0), tl.ramp(fresh__A=5.0, duration=0.5))
    assert points(tl.to_timeline(set_first, onto=tline)) == [[3.5, 0.0], [4.0, 5.0]]


def test_a_per_variable_self_reference_places_each_on_its_own_history(tline):
    """
    `["variable", "variable"]` is the general form of what the 2025-era tests spelled by
    naming one variable in both slots. It differs from the default, which follows the
    most recent anchor rather than each variable's own last row.
    """
    assert points(
        tl.to_timeline(
            tl.ramp(
                coil__A=9.0,
                time=5.0,
                duration=1.0,
                origin=[wt_tags.VARIABLE, wt_tags.VARIABLE],
            ),
            onto=tline,
        )
    ) == points(
        tl.to_timeline(
            tl.ramp(
                coil__A=9.0,
                time=5.0,
                duration=1.0,
                origin=["coil__A", wt_tags.VARIABLE],
            ),
            onto=tline,
        )
    )


###############################################################################
#   D3 / #117
###############################################################################


def test_ramp_default_origin2_survives_being_used():
    """
    `ramp`'s `origin2` default is one list, shared by every call for the life of the
    process. Pin that a ramp cannot disturb it -- this is the failure D3 described as
    latent, and it would be silent: every later ramp in the session would take its end
    point from whatever the first one left behind.
    """
    import inspect

    from wignertime.timeline import build as tl

    default = inspect.signature(tl.ramp).parameters["origin2"].default
    assert default == [wt_tags.VARIABLE, 0.0]

    base = tl.to_timeline(
        tl.anchor(1.0), onto=tl.to_timeline(tl.update(coil__A=0.0, context="s"))
    )
    for _ in range(3):
        base = tl.to_timeline(
            tl.anchor(1.0),
            onto=tl.to_timeline(tl.ramp(coil__A=5.0, duration=1.0), onto=base),
        )

    assert inspect.signature(tl.ramp).parameters["origin2"].default == [
        wt_tags.VARIABLE,
        0.0,
    ]


def test_auto_requires_its_defaults():
    """
    `origin__defaults` has no signature default, so the rebindable
    `config.ORIGIN__DEFAULTS` is never captured at import time. Rebinding it must reach
    `ramp`/`update`/`anchor`, as rebinding `config.VARIABLE__REGEX` reaches `variable`.
    """
    import inspect

    with pytest.raises(TypeError):
        wt_origin.auto(None, None)

    assert (
        inspect.signature(wt_origin.auto).parameters["origin__defaults"].default
        is inspect.Parameter.empty
    )


# --- #142: `INFER` is a visible name for the default, not a second meaning ----


@pytest.mark.parametrize(
    "origin", [None, wt_config.INFER, [None, None], [wt_config.INFER, None]]
)
def test_none_and_infer_are_the_same_default(tline, origin):
    """
    The marker only makes the default visible in a signature. As the whole argument or
    in a slot, `None` and `INFER` both mean "use the default", for all three functions.
    """
    wt_frame.assert_equal(
        tl.to_timeline(tl.update(x=[[0.5, 1]], origin=origin), onto=tline),
        tl.to_timeline(tl.update(x=[[0.5, 1]]), onto=tline),
    )
    wt_frame.assert_equal(
        tl.to_timeline(tl.anchor(0.5, origin=origin), onto=tline),
        tl.to_timeline(tl.anchor(0.5), onto=tline),
    )
    wt_frame.assert_equal(
        tl.to_timeline(tl.ramp(coil__A=9.0, duration=0.5, origin=origin), onto=tline),
        tl.to_timeline(tl.ramp(coil__A=9.0, duration=0.5), onto=tline),
    )


def test_a_stage_forwarding_none_keeps_the_default(tline):
    """
    The usual way of writing a stage with no opinion of its own about `origin` is to
    take `origin=None` and pass it on. That must place it where leaving `origin` out
    would, `t` after the most recent anchor (3.5), not in absolute time.
    """

    def trigger_camera(t, exposure, context, origin=None):
        return tl.update(
            trigger__camera=[[t, 1], [t + exposure, 0]], context=context, origin=origin
        )

    new = tl.to_timeline(trigger_camera(0.5, 0.1, "imaging"), onto=tline)
    assert new[new["variable"] == "trigger__camera"]["time"].tolist() == [4.0, 4.1]


def test_absolute_placement_is_a_number(tline):
    """
    `origin=0.0` means the same in `update` and `ramp`: absolute time, with nothing added
    to the values written (#142). For a ramp that leaves its start where the variable is
    at that instant -- 2.0 at t=0.5, not the 5.0 it reaches later. `[0.0, 0.0]`, which
    used to be the ramp's own spelling of "no shift" and started it from zero, is refused.
    """
    assert tl.to_timeline(tl.update(x=[[0.5, 1]], origin=0.0), onto=tline).iloc[-1][
        ["time", "value"]
    ].tolist() == [0.5, 1.0]
    assert points(
        tl.to_timeline(
            tl.ramp(coil__A=9.0, time=0.5, duration=0.5, origin=0.0), onto=tline
        )
    ) == [[0.5, 2.0], [1.0, 9.0]]
    with pytest.raises(ValueError, match="value slot of its `origin`"):
        tl.ramp(coil__A=9.0, time=0.5, duration=0.5, origin=[0.0, 0.0])


def test_the_marker_is_one_object_that_prints_as_its_name():
    """
    `is` is how it is recognised, so copying or pickling it -- a deferred call holds its
    defaults -- must not make a second one. It prints as `INFER` in `help()`.
    """
    import copy
    import inspect
    import pickle

    assert copy.copy(wt_config.INFER) is wt_config.INFER
    assert copy.deepcopy(wt_config.INFER) is wt_config.INFER
    assert pickle.loads(pickle.dumps(wt_config.INFER)) is wt_config.INFER
    assert wt_config.ORIGIN__INFER is wt_config.CONTEXT__INFER is wt_config.INFER

    for f in (tl.update, tl.anchor, tl.ramp):
        parameters = inspect.signature(f).parameters
        assert parameters["origin"].default is wt_config.INFER
        assert parameters["context"].default is wt_config.INFER
    assert "origin=INFER" in str(inspect.signature(tl.update))
