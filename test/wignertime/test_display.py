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
            ex.init(shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
            ex.MOT(),
            ex.MOT__detuned_growth(),
        )
    ).drop(columns="function")

    adwin_display.quantities(
        tl__new, variables=["lockbox_MOT__MHz"], do_show=False, range__x=[14.99, 15.02]
    )
    adwin_display.quantities(tl__new, variables=["shutter_MOT"], do_show=False)
    adwin_display.quantities(
        tl__new,
        variables=["lockbox_MOT__MHz", "shutter_MOT"],
        do_show=False,
        range__x=[14.99, 15.02],
    )


def test_displaying_leaves_the_timeline_alone():
    """#153: `quantities` sorted the caller's own frame in place, and renumbered it."""
    timeline = ex.timeline__demo.drop(columns="function")
    before = timeline.copy()
    adwin_display.quantities(timeline, do_show=False)
    frame.assert_equal(timeline, before)
