# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

# ============================================================
# Block module based on dependency
import importlib.util

from wignertime import adwin

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")

# ============================================================
# Normal imports
# ============================================================
import itertools

import matplotlib as mpl
import matplotlib.axes as mpa
import matplotlib.colors as mpc
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

import wignertime.variable as wt_variable
from wignertime import ramp_function as wt_ramp_function
from wignertime import timeline as tl
from wignertime.config import LABEL__ANCHOR
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util as wt_util
from wignertime.internal.timeline import anchor

# ============================================================

SYMBOL_QUANTITY = {
    "V": "Voltage",
    "A": "Current",
    "W": "Power",
    "MHz": "Frequency",
    "Hz": "Frequency",
    "Ω": "Resistance",
    "F": "Capacitance",
    "H": "Inductance",
    "J": "Energy",
    "N": "Force",
    "m": "Length",
    "s": "Time",
    "kg": "Mass",
    "K": "Temperature",
}

SAMPLES__RAMP = 20
"""
How finely a ramp is drawn from a timeline that has not been expanded: at its duration
over this, so from about this many samples whatever its length (#173). A ramp that binds a
resolution of its own is drawn at that one.
"""

_RAMP = "ramp__drawn"
"""
A column of the copy that is expanded for drawing: the position of each ramp row, and
nothing on the others. `expand` gives every row it samples from a ramp the start row's
columns, so the samples of one ramp share a number, which is how they are told apart
from the rows on either side without pairing any rows here.
"""

MARGIN = 0.05
"""The width of each margin, as a fraction of the run's duration."""

INSET = 0.01
"""Where the variables' names begin, as a fraction of the panel's width from its left."""

LIFT = 2
"""How far a variable's name sits above its line, in points, so the line does not strike
it through."""


def _width(string, font) -> float:
    """The width of `string` set in `font`, in points, with no renderer needed."""
    return TextPath((0, 0), string, prop=font).get_extents().width


def _draw_context(axis: mpa.Axes, info__context, alpha=0.1, cmap__context="magma"):
    """
    A band over each stage, and its name, which `_place_stage_names` places. Returns the
    names, each with the stage's extent and its width in points.
    """
    y__center = np.mean(axis.get_ylim())

    theme_colors = plt.get_cmap(cmap__context).colors
    names = []
    for con, col in zip(
        info__context.keys(), wt_util.sample(theme_colors, len(info__context))
    ):
        times = info__context[con]["times"]
        axis.axvspan(times[0], times[1], color=col, alpha=alpha)

        # Opaque and darkened, since the light end of the map at half opacity did not
        # read. Clipped, so that a name outside the view does not count towards the
        # figure's extent: on the demo zoomed to 9.5 ms, `MOT`'s made it 12 066 in wide
        # (D24).
        name = axis.text(
            np.mean(times),
            y__center,
            con,
            va="center",
            ha="center",
            color=0.6 * np.array(mpc.to_rgb(col)),
            clip_on=True,
        )
        names.append((name, times, _width(con, name.get_fontproperties())))

    return names


def _extent(tline):
    """The earliest and latest finite times of `tline`: the run, and (0, 0) if none."""
    times = tline["time"].to_numpy(dtype=float)
    finite = times[np.isfinite(times)]
    return (finite.min(), finite.max()) if finite.size else (0, 0)


def _into_margins(tline, fraction=MARGIN):
    """
    The timeline with its rows at −∞ drawn in a margin before the run, and those at +∞
    in one after it (#154), and the margin's width. The special contexts used to be drawn
    as hard-coded 0.5 s bands over the start of the first stage and the end of the last,
    inside the run, where neither happens.
    """
    times = tline["time"].to_numpy(dtype=float)
    start, end = _extent(tline)
    margin = fraction * (end - start) or 1.0
    if np.isfinite(times).all():
        return tline, margin
    placed = np.where(
        times == -np.inf, start - margin, np.where(times == np.inf, end + margin, times)
    )
    return tline.assign(time=placed), margin


def _sampled(function):
    """
    `function`, a ramp's, given `time_resolution` at the ramp's duration over
    `SAMPLES__RAMP`, the default `expand` would otherwise be handed: so a ramp that binds
    a resolution keeps it (#65). The duration is read off the points `expand` calls it
    with, which is why the ramp's rows need no pairing here.
    """

    @wt_ramp_function.with_points(wt_ramp_function.points(function))
    def drawn(*points):
        duration = points[-1][0] - points[0][0]
        return wt_util.function__defaults(
            function, time_resolution=duration / SAMPLES__RAMP
        )(*points)

    return drawn


def _expanded(tline):
    """
    `tline` as it is drawn, and a table of the ramps expanded for it, one row each, or
    `None` when nothing was.

    A timeline that has not been expanded holds a ramp as two rows, its start and its end,
    and `step` drew it as its start value held to the end and a jump there: on Lab2's
    run, two coil ramps that overlap looked like one coil switched on after the other was
    switched off (#173). It is drawn from an expanded copy instead, each ramp at its own
    duration over `SAMPLES__RAMP` (`_sampled`), so a 0.9 ms ramp and a 0.45 s one are
    drawn alike. A timeline with no ramp to expand is drawn as it is.
    """
    if "function" not in tline.columns or not tline["function"].notna().any():
        return tline, None

    ramps = tline["function"].notna().to_numpy()
    drawn = tl.expand(
        tline.assign(
            function=tline["function"].map(_sampled, na_action="ignore"),
            **{_RAMP: np.where(ramps, np.arange(len(tline)), np.nan)},
        )
    )

    samples = drawn[drawn[_RAMP].notna()].groupby(_RAMP, sort=False)
    listed = samples.agg(
        variable=("variable", "first"),
        context=("context", "first"),
        start=("time", "min"),
        end=("time", "max"),
        samples=("time", "size"),
    )
    duration = listed["end"] - listed["start"]
    listed = listed.assign(
        duration=duration,
        resolution=duration / (listed["samples"] - 1),
        # What `expand` takes for a ramp's own resolution, since it then needs none.
        own=[
            "time_resolution"
            not in wt_util.parameters__unstated(tline["function"].iloc[int(position)])
            for position in listed.index
        ],
    )
    listed = wt_frame.sort(listed, ["start", "variable"])
    return (
        drawn,
        listed[
            ["variable", "context", "start", "duration", "samples", "resolution", "own"]
        ],
    )


def _report(ramps):
    """Says which ramps were expanded for drawing, and how finely (#173)."""
    print(
        "quantities: {} ramp(s) drawn from an expanded copy of the timeline, each sampled"
        " at its duration over {} unless it binds a resolution of its own (`own`). The"
        " timeline is unchanged, and the dots are its rows.\n{}".format(
            len(ramps),
            SAMPLES__RAMP,
            ramps.rename(
                columns={
                    "start": "start [s]",
                    "duration": "duration [s]",
                    "resolution": "resolution [s]",
                }
            ).to_string(
                index=False,
                formatters={
                    "start [s]": "{:.9g}".format,
                    "duration [s]": "{:.4g}".format,
                    "resolution [s]": "{:.4g}".format,
                },
            ),
        )
    )


def _note(ramps) -> str:
    """The figure's own line about the ramps expanded for drawing."""
    own = int(ramps["own"].sum())
    exceptions = (
        ", {} at a resolution of {} own".format(own, "its" if own == 1 else "their")
        if own
        else ""
    )
    return "Ramps drawn from ~{} samples each{}; dots are the timeline's rows.".format(
        SAMPLES__RAMP, exceptions
    )


def _path(rows):
    """
    The line through one variable's `rows`, in time order: each value held until the next
    row, as the hardware holds it, but the samples of one ramp joined straight, which
    draws a ramp sampled coarsely for the figure as the ramp it is (#173). Rows without
    `_RAMP`, from a timeline that was expanded before it was given, are all held, as
    `step(where="post")` drew them.
    """
    t = rows["time"].to_numpy(dtype=float)
    v = rows["value"].to_numpy(dtype=float)
    ramp = (
        rows[_RAMP].to_numpy(dtype=float)
        if _RAMP in rows.columns
        else np.full(len(t), np.nan)
    )
    joined = ramp[:-1] == ramp[1:]  # `nan`, on a row of no ramp, equals nothing
    # From each point to the next, through the corner (next time, this value) unless the
    # two are joined.
    x = np.column_stack([t[1:], t[1:]]).ravel()
    y = np.column_stack([v[:-1], v[1:]]).ravel()
    keep = np.column_stack([~joined, np.ones_like(joined)]).ravel()
    return np.concatenate([t[:1], x[keep]]), np.concatenate([v[:1], y[keep]])


def _points_per_second(axis):
    x0, x1 = axis.get_xlim()
    return axis.get_position().width * axis.figure.get_figwidth() * 72 / (x1 - x0)


def _name(axis, variable, color):
    """
    A variable's name, at the left edge of the panel whatever its view, and just above the
    height `_place_variable_names` gives it. Clipped, as every name is (D24).
    """
    return axis.text(
        INSET,
        0,
        variable,
        color=color,
        fontsize="small",
        va="bottom",
        transform=mtransforms.offset_copy(
            axis.get_yaxis_transform(), fig=axis.figure, y=LIFT, units="points"
        ),
        clip_on=True,
    )


def _place_variable_names(names):
    """
    Each variable's name at the left edge of the view, on the value its line has there,
    and those of one panel moved apart where they would print over one another.

    `names` holds `(axis, text, x, y)`, with `x`, `y` the line drawn, the names of each
    panel together. They were drawn at the first value, at 0 s, and moved to the left
    edge by the callback on the view's limits, which `range__x` was applied before; so a
    figure zoomed when it was made had none in view (D24).
    """
    for axis, group in itertools.groupby(names, key=lambda name: name[0]):
        group = list(group)
        x0, x1 = axis.get_xlim()
        y0, y1 = axis.get_ylim()
        at = x0 + INSET * (x1 - x0)
        per_point = (y1 - y0) / (
            axis.get_position().height * axis.figure.get_figheight() * 72
        )
        gap = 1.2 * group[0][1].get_fontsize() * per_point
        top = y1 - gap - LIFT * per_point

        ys = np.array([np.interp(at, x, y) for _, _, x, y in group])
        order = np.argsort(ys, kind="stable")
        placed = ys[order]
        for k in range(1, len(placed)):
            placed[k] = max(placed[k], placed[k - 1] + gap)
        if placed[-1] > top:
            placed[-1] = top
            for k in range(len(placed) - 1, 0, -1):
                placed[k - 1] = min(placed[k - 1], placed[k] - gap)
        for k, i in enumerate(order):
            group[i][1].set_y(placed[k])


def _place_stage_names(names, reserved):
    """
    Each stage's name in the middle of the part of the stage in view, where it fits
    there, and nowhere otherwise. The names of short stages were printed over one another,
    and those outside the view stretched a saved figure (D24).

    `names` holds `(axis, text, (start, end), width)`, the width in points, the names of
    each panel together, and `reserved` the width of the widest variable's name in each
    panel, which a stage's name keeps clear of. Stages can overlap (B12), so a name that
    would print over one placed before it is left out too; the shortest stages in view
    are placed first, since they have the least room.
    """
    for axis, group in itertools.groupby(names, key=lambda name: name[0]):
        x0, x1 = axis.get_xlim()
        scale = _points_per_second(axis)
        begin = x0 + INSET * (x1 - x0) + reserved.get(axis, 0) / scale

        def in_view(name):
            start, end = name[2]
            return max(start, begin), min(end, x1)

        placed = []
        for name in sorted(group, key=lambda n: np.diff(in_view(n))[0]):
            text, width = name[1], name[3]
            left, right = in_view(name)
            middle, half = (left + right) / 2, 0.6 * width / scale
            shown = right - left > 2 * half and all(
                middle + half < other[0] or middle - half > other[1] for other in placed
            )
            text.set_visible(shown)
            text.set_x(middle)
            if shown:
                placed.append((middle - half, middle + half))


def _name_anchors(axis, anchors):
    """
    The top axis: the context of each anchor at its instant, leaving out a name that would
    print over the one before it. `anchors` holds `(time, context, width)` in time order,
    the width in points.
    """
    x0, x1 = axis.get_xlim()
    scale = _points_per_second(axis)
    right__named = -np.inf
    ticks, labels = [], []
    # In view only, since ticks outside it would widen the view to take them in.
    for time, context, width in (a for a in anchors if x0 <= a[0] <= x1):
        left = (time - x0) * scale - width / 2
        ticks.append(time)
        labels.append(context if left > right__named else "")
        if left > right__named:
            right__named = left + 1.2 * width
    axis.set_xticks(ticks, labels)


def quantities(
    timeline: wt_frame.CLASS,
    variables=None,
    do_context: bool = True,
    do_show: bool = True,
    symbol_quantities: dict = SYMBOL_QUANTITY,
    cmap__context="magma",
    range__x=None,
):
    """
    Draws `timeline` in panels by quantity: one for each unit, holding the variables in
    it, and one for the digital lines. Unit and quantity are meant as in the SI.

    A timeline that has not been expanded holds each ramp as two rows, its start and its
    end. It is drawn from an expanded copy, in which each ramp is sampled at its duration
    over `SAMPLES__RAMP`, so about as finely whatever its length, unless it binds a
    resolution of its own (#173). The ramps expanded are listed in the output, and a line
    in the figure says so. The dots are the timeline's own rows. A timeline that has been
    expanded is drawn as it is. The timeline given is not changed.

    A timeline reloaded from a text file holds its ramps' functions as strings, and cannot
    be drawn until D27 (#191) is fixed: it raises, as `expand` does.

    Parameters
    ----------
    timeline
        The timeline to draw.
    variables
        The variables to draw, all of them if not given. Name the anchors too, or the
        stages shrink to the rows of the variables named, and lose their boundaries and
        the names on the top axis.
    do_context
        Whether to draw the stages, as bands with their names.
    do_show
        Whether to show the figure, with `plt.show()`.
    symbol_quantities
        The quantity of each unit, for the panels' labels.
    cmap__context
        The colour map the stages' colours are taken from.
    range__x
        The times in view, `(start, end)` in seconds; the whole timeline if not given.

    Returns
    -------
    fig, axes
        The figure, and its panels from top to bottom.
    """
    if variables:
        tline = wt_frame.subframe(timeline, "variable", variables)
    else:
        tline = timeline

    # Expanded before it is sorted, since `expand` pairs a ramp's rows in the order they
    # were written (A21).
    drawn, ramps = _expanded(tline)
    if ramps is not None:
        _report(ramps)

    # Sorted copies, and stable ones (#153). This sorted the caller's own frame in place,
    # and not stably, so a value superseded at the same instant could be drawn as the one
    # in force.
    start, end = _extent(tline)
    tline, margin = _into_margins(wt_frame.sort(tline, "time"))
    drawn, _ = _into_margins(wt_frame.sort(drawn, "time"))

    # =====================================================================
    # ADwin
    # =====================================================================
    # To make the special contexts (where there is no time) visible, each spans a margin:
    # before the run for those whose sentinel is negative, after it otherwise. Spanning
    # the margin and not the rows, since rows written at a finite time, as before #154,
    # stretched the band into the run: Lab2's `ADwin_Finish` covered its last 0.6 s.
    if do_context:
        info__context = tl.context_info(tline)
        for label, sentinel in adwin.CONTEXTS__SPECIAL.items():
            if label in info__context.keys():
                info__context[label]["times"] = (
                    [start - margin, start] if sentinel < 0 else [end, end + margin]
                )
    # =====================================================================

    if variables is None:
        variables = tline["variable"].unique()

    # In the order the variables come, so that the panels keep their places from one
    # session to the next, as a set of units did not.
    units = dict.fromkeys(wt_variable.unit(v) for v in variables)
    unit_variables__analog = {
        u: [v for v in variables if wt_variable.unit(v) == u]
        for u in units
        if u not in ["digital", LABEL__ANCHOR]
    }
    variables__digital = [v for v in variables if wt_variable.unit(v) == "digital"]

    tline__anchors = tline[anchor.mask(tline)]

    # Cycled, so that a panel of more variables than there are colours draws them all.
    # Zipped against the colours, a panel stopped at the tenth, without a word: three of
    # the four lines left out of a lab shot were the ones its figure was for (#173).
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    num_analog_panels = len(unit_variables__analog)
    num_digital_panels = 1 if variables__digital else 0
    num_panels = num_analog_panels + num_digital_panels

    fig, axes = plt.subplots(
        num_analog_panels + num_digital_panels,
        sharex=True,
        figsize=(7.5, 7.5),
        height_ratios=[1] * num_analog_panels + num_digital_panels * [2],
    )
    if num_panels == 1:
        axes = [axes]

    # Each line runs on to the end of what is drawn, since a channel holds its last value:
    # one that is set once, before the run, was a dot and a name with no line.
    time__end = drawn["time"].max()
    names__variable = []

    def _draw(axis, variable, color, baseline=0.0):
        """
        The line from `drawn`, a dot at each of the timeline's own rows, so that a dot is
        a row someone wrote, and the variable's name.
        """
        x, y = _path(drawn[drawn["variable"] == variable])
        if x[-1] < time__end:
            x, y = np.append(x, time__end), np.append(y, y[-1])
        y = y + baseline
        rows = tline[tline["variable"] == variable]
        axis.plot(x, y, color=color)
        axis.plot(
            rows["time"],
            rows["value"] + baseline,
            color=color,
            linestyle="none",
            marker="o",
            ms=3,
        )
        names__variable.append((axis, _name(axis, variable, color), x, y))

    names__stage = []

    # =====================================================================
    # ANALOGUE
    # =====================================================================

    if num_analog_panels > 0:
        axes__analogue = axes[:-num_digital_panels] if num_digital_panels != 0 else axes
        for key, axis in zip(unit_variables__analog.keys(), axes__analogue):
            if key in symbol_quantities:
                axis.set_ylabel(f"{symbol_quantities[key]} [{key}]")
            else:
                axis.set_ylabel(f"[{key}]")

            for variable, color in zip(
                unit_variables__analog[key], itertools.cycle(colors)
            ):
                _draw(axis, variable, color)
            if do_context:
                names__stage += [
                    (axis, *name)
                    for name in _draw_context(
                        axis, info__context, cmap__context=cmap__context
                    )
                ]
    #
    # =====================================================================
    # DIGITAL
    # =====================================================================
    # One name to a line, on it, as in the other panels. Each line had a name at either
    # level, `_OFF` and `_ON`, and a dozen lines printed theirs over one another.
    if num_digital_panels > 0:
        axis = axes[-1]
        divider = 1.5 * len(variables__digital)
        axis.set_ylabel("Digital")

        for offset, (variable, color) in enumerate(
            zip(variables__digital, itertools.cycle(colors))
        ):
            baseline = offset / divider
            axis.axhline(baseline, color=color, linestyle=":", alpha=0.5)
            axis.axhline(baseline + 1, color=color, linestyle=":", alpha=0.5)
            _draw(axis, variable, color, baseline)
        axis.set_yticks([i / divider for i in range(len(list(variables__digital)))])
        axis.set_yticklabels([])
        if do_context:
            names__stage += [
                (axis, *name)
                for name in _draw_context(
                    axis, info__context, cmap__context=cmap__context
                )
            ]

    # The widest variable's name in each panel, in points, which stage names keep clear of.
    reserved = {}
    for axis, name, _, _ in names__variable:
        reserved[axis] = max(
            reserved.get(axis, 0), _width(name.get_text(), name.get_fontproperties())
        )

    for anchorTime in tline__anchors["time"]:
        for axis in axes:
            axis.axvline(anchorTime, color="0.5", linestyle="--")

    # Absolute times: zoomed into a run, the axis showed an offset (`+1.51e1`) instead.
    for axis in axes:
        axis.ticklabel_format(axis="x", useOffset=False)
    axes[-1].set_xlabel("Time [s]")

    ax2 = axes[0].twiny()
    font__tick = FontProperties(size=mpl.rcParams["xtick.labelsize"])
    anchors = [
        (time, context, _width(context, font__tick))
        for time, context in zip(tline__anchors["time"], tline__anchors["context"])
    ]

    def _sync_axes(event):
        xlim = axes[0].get_xlim()
        ax2.set_xlim(xlim)
        _place_variable_names(names__variable)
        _place_stage_names(names__stage, reserved)
        _name_anchors(ax2, anchors)

    # Connected before `range__x` is applied, which is what places the names for it: it
    # used to be applied first, so a figure zoomed when it was made had none in view
    # (D24). Resizing changes how much fits.
    axes[0].callbacks.connect("xlim_changed", _sync_axes)
    fig.canvas.mpl_connect("resize_event", _sync_axes)
    if range__x is not None:
        axes[0].set_xlim(*range__x)

    if ramps is not None:
        fig.text(0.01, 0.01, _note(ramps), fontsize="small", color="0.35")
    # Placed, laid out with the names in place, and placed again in the panels' new size.
    _sync_axes(None)
    fig.tight_layout(rect=(0, 0.03, 1, 1) if ramps is not None else None)
    _sync_axes(None)

    if do_show:
        plt.show()

    return fig, axes
