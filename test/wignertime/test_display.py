import numpy as np
import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as frame

# `adwin.display` needs the optional `display` extra.
pytest.importorskip("matplotlib", reason="the `display` extra is not installed")

from wignertime.adwin import display as adwin_display

import sys
import pathlib as pl

from wignertime.demo import full_experiment as ex


def test_displayIndividualTypes():
    tl__new = tl.to_timeline(
        tl.stack(
            ex.init(shutter__imaging=0, AOM__imaging=1, trigger__camera=0),
            ex.MOT(),
            ex.MOT_detuned_growth(),
        )
    )

    tl__new = frame.drop_columns(tl__new, ["function"])

    adwin_display.quantities(
        tl__new, variables=["lockbox__MOT__MHz"], do_show=False, range__x=[14.99, 15.02]
    )
    adwin_display.quantities(tl__new, variables=["shutter__MOT"], do_show=False)
    adwin_display.quantities(
        tl__new,
        variables=["lockbox__MOT__MHz", "shutter__MOT"],
        do_show=False,
        range__x=[14.99, 15.02],
    )


def test_displaying_leaves_the_timeline_alone():
    """#153: `quantities` sorted the caller's own frame in place, and renumbered it."""
    timeline = frame.drop_columns(ex.timeline_demo, ["function"])
    before = frame.copy(timeline)
    adwin_display.quantities(timeline, do_show=False)
    frame.assert_equal(timeline, before)


def test_rows_before_and_after_the_run_are_drawn_in_its_margins():
    """#154: the special contexts used to be 0.5 s bands inside the run."""
    placed, margin = adwin_display._into_margins(ex.timeline_demo)
    times = frame.column(ex.timeline_demo, "time")
    finite = times[np.abs(times) != float("inf")]
    start, end = finite.min(), finite.max()
    assert margin == pytest.approx(0.05 * (end - start))
    assert set(frame.column(placed, "time")[times == -float("inf")]) == {start - margin}
    assert set(frame.column(placed, "time")[times == float("inf")]) == {end + margin}
