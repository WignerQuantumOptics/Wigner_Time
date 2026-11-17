import functools
import itertools

import numpy as np
import pytest

from wignertime import ramp_function
from wignertime import timeline as tl
from wignertime.internal import dataframe as frame

# `adwin.display` needs the optional `display` extra.
pytest.importorskip("matplotlib", reason="the `display` extra is not installed")

import matplotlib.pyplot as plt
from matplotlib.cbook import STEP_LOOKUP_MAP

from wignertime.adwin import display as adwin_display
from wignertime.demo import full_experiment as ex


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_displayIndividualTypes():
    tl__new = tl.to_timeline(
        tl.stack(
            ex.init(shutter__imaging=0, AOM__imaging=1, trigger__camera=0),
            ex.MOT(),
            ex.MOT_detuned_growth(),
        )
    ).drop(columns="function")

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
    timeline = ex.timeline_demo.drop(columns="function")
    before = timeline.copy()
    adwin_display.quantities(timeline, do_show=False)
    frame.assert_equal(timeline, before)


def test_rows_before_and_after_the_run_are_drawn_in_its_margins():
    """#154: the special contexts used to be 0.5 s bands inside the run."""
    placed, margin = adwin_display._into_margins(ex.timeline_demo)
    times = ex.timeline_demo["time"]
    start, end = times[times.abs() != float("inf")].agg(["min", "max"])
    assert margin == pytest.approx(0.05 * (end - start))
    assert set(placed.loc[times == -float("inf"), "time"]) == {start - margin}
    assert set(placed.loc[times == float("inf"), "time"]) == {end + margin}


###############################################################################
#   #173 (D24) -- ramps drawn from an expanded copy, and a zoomed figure
###############################################################################


def _ramp(*ramps):
    """`coil__MOT__A` at 0 from 0 s, then each of `ramps`, a dict of `ramp` keywords."""
    return tl.to_timeline(
        tl.stack(
            tl.update(coil__MOT__A=0.0, time=0.0, context="run"),
            *[tl.ramp(**ramp) for ramp in ramps],
        )
    )


def _drawn(axis):
    """Each solid line of `axis` as it appears, with its steps, if it is drawn in steps."""
    return [
        STEP_LOOKUP_MAP[line.get_drawstyle()](*map(np.asarray, line.get_data()))
        for line in axis.get_lines()
        if line.get_linestyle() == "-"
    ]


def _dots(axis):
    """Each line of `axis` drawn as markers only."""
    return [
        tuple(map(np.asarray, line.get_data()))
        for line in axis.get_lines()
        if line.get_linestyle() == "None"
    ]


def _instants(x, start, end):
    """How many distinct instants the line `x` has from `start` to `end`."""
    return len(np.unique(x[(x >= start - 1e-12) & (x <= end + 1e-12)]))


def test_an_unexpanded_ramp_is_drawn_through_the_values_between_its_ends():
    """
    #173: a ramp's two rows were joined by a step, so it was drawn as its start value held
    to its end and a jump there. On Lab2's run, two coil ramps that overlap looked like
    one coil switched on after the other had been switched off.
    """
    _, axes = adwin_display.quantities(
        _ramp(dict(coil__MOT__A=1.0, time=1.0, duration=1.0)), do_show=False
    )
    ((x, y),) = _drawn(axes[0])
    assert np.interp(1.5, x, y) == pytest.approx(0.5)
    assert 0.0 < np.interp(1.25, x, y) < 0.5


def test_drawing_leaves_an_unexpanded_timeline_alone():
    """The ramps are expanded in a copy; the caller's timeline keeps its `function`s."""
    timeline = ex.timeline_demo
    assert timeline["function"].notna().any()
    before = timeline.copy()
    adwin_display.quantities(timeline, do_show=False)
    frame.assert_equal(timeline, before)


@pytest.mark.parametrize("duration", [9e-4, 0.45])
def test_a_ramp_is_drawn_from_twenty_samples_whatever_its_length(duration):
    """The molasses coil ramp of the demo and a transport ramp of Lab2, alike."""
    _, axes = adwin_display.quantities(
        _ramp(dict(coil__MOT__A=1.0, time=1.0, duration=duration)), do_show=False
    )
    ((x, _),) = _drawn(axes[0])
    assert _instants(x, 1.0, 1.0 + duration) == adwin_display.SAMPLES__RAMP + 1


def test_a_ramp_that_binds_its_resolution_is_drawn_at_it():
    """As `expand` keeps it (#65): the display's resolution is a default, too."""
    bound = functools.partial(ramp_function.tanh, time_resolution=0.1)
    _, axes = adwin_display.quantities(
        _ramp(dict(coil__MOT__A=1.0, time=1.0, duration=1.0, function=bound)),
        do_show=False,
    )
    ((x, _),) = _drawn(axes[0])
    assert _instants(x, 1.0, 2.0) == 11


def test_the_dots_are_the_rows_of_the_timeline():
    """Markers only where a row was written: a ramp's two, not its samples."""
    timeline = _ramp(dict(coil__MOT__A=1.0, time=1.0, duration=1.0))
    _, axes = adwin_display.quantities(timeline, do_show=False)
    ((x, y),) = _dots(axes[0])
    np.testing.assert_array_equal(x, [0.0, 1.0, 2.0])
    np.testing.assert_array_equal(y, [0.0, 0.0, 1.0])


def test_an_expanded_timeline_is_drawn_as_it_is(capsys):
    """Every row held until the next, as `step(where="post")` drew it, and no notice."""
    timeline = tl.expand(
        _ramp(dict(coil__MOT__A=1.0, time=1.0, duration=1.0)), time_resolution=0.25
    )
    fig, axes = adwin_display.quantities(timeline, do_show=False)
    ((x, y),) = _drawn(axes[0])
    expected = STEP_LOOKUP_MAP["steps-post"](
        timeline["time"].to_numpy(), timeline["value"].to_numpy()
    )
    np.testing.assert_allclose(x, expected[0])
    np.testing.assert_allclose(y, expected[1])
    ((x, _),) = _dots(axes[0])
    np.testing.assert_allclose(x, timeline["time"])
    assert capsys.readouterr().out == ""
    assert not fig.texts


def test_the_ramps_expanded_for_drawing_are_listed(capsys):
    """In the output, one row each, and in a line of the figure."""
    bound = functools.partial(ramp_function.tanh, time_resolution=0.1)
    fig, _ = adwin_display.quantities(
        _ramp(
            dict(coil__MOT__A=1.0, time=1.0, duration=1.0),
            dict(coil__MOT__A=0.0, time=1.0, duration=0.5, function=bound),
        ),
        do_show=False,
    )
    out = capsys.readouterr().out
    assert out.startswith("quantities: 2 ramp(s) drawn from an expanded copy")
    rows = [line.split() for line in out.splitlines()[2:]]
    assert [row[:2] for row in rows] == [["coil__MOT__A", "run"]] * 2
    np.testing.assert_allclose(
        [[float(cell) for cell in row[2:6]] for row in rows],
        [[1.0, 1.0, 21, 0.05], [3.0, 0.5, 6, 0.1]],
    )
    assert [row[6] for row in rows] == ["False", "True"]
    assert [text.get_text() for text in fig.texts] == [
        "Ramps drawn from ~20 samples each, 1 at a resolution of its own; dots are the"
        " timeline's rows."
    ]


@pytest.mark.parametrize("unit", ["", "__A"])
def test_a_panel_of_more_variables_than_colours_draws_them_all(unit):
    """
    #173: each panel's variables were zipped against the ten colours of the cycle, so the
    eleventh and after were left out, without a word.
    """
    names = ["shutter__{}{}".format(uid, unit) for uid in "ABCDEFGHIJKL"]
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(time=0.0, context="run", **{name: 0.0 for name in names}),
            tl.update(time=1.0, **{name: 1.0 for name in names}),
        )
    )
    _, axes = adwin_display.quantities(timeline, do_show=False)
    assert len(_drawn(axes[0])) == len(names)


def test_a_final_state_written_at_a_finite_time_is_drawn_after_the_run():
    """
    Before #154 the special contexts were written at finite times, as in the Lab2 fixture,
    and the band of `ADwin_Finish` was stretched back over the run's last 5 %.
    """
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(coil__MOT__A=0.0, time=0.0, context="run"),
            tl.update(coil__MOT__A=1.0, time=10.0),
            tl.update(coil__MOT__A=0.0, time=10.0, origin=0.0, context="ADwin_Finish"),
        )
    )
    _, axes = adwin_display.quantities(timeline, do_show=False)
    spans = sorted(
        (patch.get_x(), patch.get_x() + patch.get_width()) for patch in axes[0].patches
    )
    assert spans == [pytest.approx((0.0, 10.0)), pytest.approx((10.0, 10.5))]


ZOOM = (15.099, 15.1085)
"""Where D24 was measured: the demo's molasses and optical pumping, 9.5 ms."""


def test_the_names_of_the_variables_are_in_a_zoomed_window():
    """
    D24, point 1: `range__x` was applied before the names existed and before the callback
    that moves them was connected, so they stayed at 0 s, 15 s outside the window.
    """
    fig, axes = adwin_display.quantities(ex.timeline_demo, do_show=False, range__x=ZOOM)
    fig.canvas.draw()
    variables = set(ex.timeline_demo["variable"])
    for axis in axes:
        panel = axis.get_window_extent()
        names = [text for text in axis.texts if text.get_text() in variables]
        assert names
        for name in names:
            extent = name.get_window_extent()
            assert panel.x0 <= extent.x0 < panel.x0 + 0.05 * panel.width
            assert panel.y0 <= extent.y0 and extent.y1 <= panel.y1


def test_a_zoomed_figure_is_no_larger_than_itself():
    """
    D24, point 2: the names of stages outside the view still counted towards the figure's
    extent, 12 066 in wide, and a tight `savefig` did not finish.
    """
    fig, _ = adwin_display.quantities(ex.timeline_demo, do_show=False, range__x=ZOOM)
    extent = fig.get_tightbbox()
    assert extent.width <= fig.get_figwidth()
    assert extent.height <= fig.get_figheight()


def test_no_two_names_in_a_panel_print_over_one_another():
    """The stages' names, and the variables', in the window D24 was measured in."""
    fig, axes = adwin_display.quantities(ex.timeline_demo, do_show=False, range__x=ZOOM)
    fig.canvas.draw()
    for axis in axes:
        extents = [
            text.get_window_extent()
            for text in axis.texts
            if text.get_visible() and text.get_text()
        ]
        assert extents
        for one, other in itertools.combinations(extents, 2):
            assert not one.overlaps(other)
