"""
#154, settled 2026-09-29 as option (b): rows before the run are at −∞ and rows after it
at +∞. Neither is an instant anything can be placed relative to or inherit a context
from; a value lookup, bounded by a finite instant, sees −∞ and never +∞.
"""

import logging
import math

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame


def before(**values):
    return tl.update(time=-math.inf, context="ADwin_LowInit", **values)


def after(**values):
    return tl.update(time=math.inf, context="ADwin_Finish", **values)


def test_the_first_timed_stage_is_placed_at_absolute_zero_without_a_word(caplog):
    """`MOT` used to have to say `origin=0.0` twice, since `init` sat at −1 µs."""
    with caplog.at_level(logging.DEBUG):
        timeline = tl.to_timeline(
            tl.stack(
                before(x__A=0.0, y=0),
                tl.stack(tl.update(y=1), tl.anchor(2.0), context="MOT"),
            )
        )
    assert list(wt_frame.column(timeline, "time"))[2:] == [0.0, 2.0]
    assert not caplog.records


def test_a_row_after_the_initial_state_inherits_no_context():
    """It used to inherit `ADwin_LowInit`, and was played in the initial state."""
    with pytest.raises(ValueError, match="or the first at an instant"):
        tl.to_timeline(tl.stack(before(y=0), tl.update(y=1)))


def test_a_row_added_to_a_finished_timeline_inherits_from_the_run():
    """It used to inherit `ADwin_Finish`, and was played in the final state."""
    finished = tl.to_timeline(
        tl.stack(
            before(y=0),
            tl.update(y=1, context="run"),
            tl.anchor(1.0),
            after(y=0),
        )
    )
    added = tl.to_timeline(tl.update(y=1, time=0.5), onto=finished)
    assert wt_frame.row(added, -1)["context"] == "run"
    assert wt_frame.row(added, -1)["time"] == pytest.approx(1.5)


def test_a_value_lookup_sees_the_state_before_the_run_and_never_after_it():
    timeline = tl.to_timeline(
        tl.stack(
            before(x__A=1.0),
            tl.anchor(1.0, context="run"),
            after(x__A=5.0),
        )
    )
    ramped = tl.to_timeline(tl.ramp(x__A=2.0, duration=1.0), onto=timeline)
    starts = wt_frame.filter(
        ramped, ~wt_frame.isnull(wt_frame.column(ramped, "function"))
    )
    assert list(wt_frame.column(starts, "value")) == [1.0, 2.0]


@pytest.mark.parametrize(
    "origin,names",
    [
        ("ADwin_LowInit", "every row of 'ADwin_LowInit' is"),
        (tl.LAST, "every row of this timeline is"),
    ],
    ids=["a context", "LAST"],
)
def test_a_time_reference_with_no_row_at_an_instant_names_none(origin, names):
    with pytest.raises(ValueError, match="names no instant: {}".format(names)):
        tl.to_timeline(tl.stack(before(y=0), tl.update(y=1, origin=origin)))


def test_an_anchor_at_infinity_is_refused():
    with pytest.raises(ValueError, match="An anchor marks an instant"):
        tl.anchor(math.inf)


@pytest.mark.parametrize(
    "arguments", [dict(duration=math.inf), dict(time=-math.inf, duration=1.0)]
)
def test_a_ramp_to_or_from_infinity_is_refused(arguments):
    with pytest.raises(ValueError, match="A ramp runs between two instants"):
        tl.to_timeline(
            tl.ramp(x__A=1.0, **arguments),
            onto=tl.to_timeline(tl.update(x__A=0.0, time=0.0, context="run")),
        )
