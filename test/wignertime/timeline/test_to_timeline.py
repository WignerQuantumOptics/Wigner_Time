"""
#85: `stack` and `cascade` compose stages only, and `to_timeline` is the one way from a
stage to a timeline (C7 in `KNOWN_ISSUES.md`).
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util as wt_util


@pytest.fixture
def initial():
    return tl.update(AOM_MOT=1, coil__A=0.0, t=0.0, context="init")


# --- to_timeline ------------------------------------------------------------------


def test_a_stage_applied_to_nothing_starts_from_an_empty_timeline(initial):
    timeline = tl.to_timeline(tl.stack(initial, tl.anchor(1.0)))
    assert list(timeline["variable"])[:2] == ["AOM_MOT", "coil__A"]
    assert list(timeline["time"])[:2] == [0.0, 0.0]


def test_onto_places_a_stage_onto_an_existing_timeline(initial):
    base = tl.to_timeline(tl.stack(initial, tl.anchor(1.0)))
    placed = tl.to_timeline(tl.update(AOM_MOT=0, t=0.5), onto=base)
    assert len(placed) == len(base) + 1
    assert placed.iloc[-1]["time"] == pytest.approx(1.5)
    assert len(base) == 3, "the timeline placed onto is left alone"


def test_onto_a_resolved_stage_is_the_same_as_one_stack(initial):
    """
    The property that lets a scan keep its base as a table (C7): building a timeline can
    be expensive, and placing onto the resolved base must give what one stack gives.
    """
    a = tl.stack(initial, tl.anchor(1.0), context="init")
    b = tl.stack(tl.ramp(coil__A=2.0, duration=0.5), tl.anchor(1.0), context="MOT")
    wt_frame.assert_equal(
        tl.to_timeline(b, onto=tl.to_timeline(a)), tl.to_timeline(tl.stack(a, b))
    )


def test_a_timeline_is_not_a_stage(initial):
    table = tl.to_timeline(initial)
    with pytest.raises(TypeError, match="one already.*onto=timeline"):
        tl.to_timeline(table)


def test_an_uncalled_stage_function_is_refused():
    def MOT(duration=15):
        return tl.anchor(duration)

    with pytest.raises(TypeError, match="the function `MOT` itself"):
        tl.to_timeline(MOT)


def test_a_stage_must_return_a_timeline():
    with pytest.raises(TypeError, match="returned int"):
        tl.to_timeline(tl.as_deferred(lambda timeline: 1))


# --- stack and cascade compose stages only ------------------------------------------


@pytest.mark.parametrize("position", ["first", "later"])
def test_stack_refuses_a_timeline_in_any_position(initial, position):
    """
    In front it used to be accepted, making `stack` return a table or a stage depending
    on its first argument (#85); after the front it was accepted and then failed as
    `'DataFrame' object is not callable` (D17's correction).
    """
    table = tl.to_timeline(initial)
    stages = [table, tl.anchor(1.0)] if position == "first" else [initial, table]
    with pytest.raises(TypeError, match="was given a timeline.*to_timeline"):
        tl.stack(*stages)


def test_stack_and_cascade_always_return_a_stage(initial):
    def init():
        return initial

    assert wt_util.is_deferred(tl.stack(initial))
    assert wt_util.is_deferred(tl.cascade(init))


def test_a_context_given_to_stack_reaches_the_first_rows():
    """
    #145. The first rows used to come from `create`, a table by the time `stack` saw it,
    so a `context` given to the stack skipped them -- with a reserved context, silently
    moving the initial state out of the initialisation phase. Now they are a stage like
    any other.
    """
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(AOM_MOT=1, shutter_MOT=0, t=-1e-6),
            tl.anchor(0.0),
            context="ADwin_LowInit",
        )
    )
    assert set(timeline["context"]) == {"ADwin_LowInit"}
