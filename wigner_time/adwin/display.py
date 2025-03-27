# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

# ============================================================
# Block module based on dependency
import importlib.util

from wigner_time import adwin, anchor

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")

# ============================================================
# Normal imports
# ============================================================
from copy import deepcopy

import matplotlib.axes as mpa
import matplotlib.pyplot as plt
import numpy as np
import wigner_time.anchor as anchor
import wigner_time.util as wt_util
import wigner_time.variable as wt_variable
from wigner_time import timeline as tl
from wigner_time.anchor import LABEL__ANCHOR
from wigner_time.internal import dataframe as wt_frame

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


def _draw_context(axis: mpa.Axes, info__context, alpha=0.1, cmap__context="magma"):
    ys = axis.get_ylim()
    y__center = np.mean(ys)

    theme_colors = plt.get_cmap(cmap__context).colors
    for con, col in zip(
        info__context.keys(), wt_util.sample(theme_colors, len(info__context))
    ):
        times = info__context[con]["times"]
        axis.axvspan(times[0], times[1], color=col, alpha=alpha)

        axis.text(
            np.mean(times),
            y__center,
            con,
            va="center",
            ha="center",
            color=col,
            alpha=0.5,
        )

    return axis


def quantities(
    timeline: wt_frame.CLASS,
    variables=None,
    do_context: bool = True,
    do_show: bool = True,
    symbol_quantities: dict = SYMBOL_QUANTITY,
    cmap__context="magma",
):
    """
    Displays the given `tline`, filtered by `variable`, in terms of different quantites, i.e. by common `unit`. The mapping between `unit` and 'quantity' can be provided as a dictionary.

    NOTE: Unit and quantity terminology taken from SI conventions.
    """
    # TODO:
    # - Separate style and content
    # - offer filtering by `context`
    if variables:
        tline = wt_frame.subframe(timeline, "variable", variables)
    else:
        tline = timeline
    tline.sort_values("time", inplace=True, ignore_index=True)

    # =====================================================================
    # ADwin
    # =====================================================================
    # To make the special contexts (where there is no time) visible
    if do_context:
        info__context = tl.context_info(tline)
        for label in adwin.CONTEXTS__SPECIAL:
            if label in info__context.keys():
                d = deepcopy(info__context[label]["times"])
                if "Init" in label:
                    info__context[label]["times"] = [d[0], d[1] + 0.5]
                if "Finish" in label:
                    info__context[label]["times"] = [d[0] - 0.5, d[1]]
    # =====================================================================

    if variables is None:
        variables = tline["variable"].unique()

    if variables is None:
        return None

    units = wt_variable.units(tline)
    unit_variables__analog = {
        u: [v for v in variables if wt_variable.unit(v) == u]
        for u in units
        if u not in ["digital", LABEL__ANCHOR]
    }
    variables__digital = [v for v in variables if wt_variable.unit(v) == "digital"]

    tline__anchors = tline[anchor.mask(tline)]

    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    num_analog_panels = len(unit_variables__analog)
    num_digital_panels = 1 if variables__digital else 0
    num_panels = num_analog_panels + num_digital_panels
    # =====================================================================
    # ANALOGUE
    # =====================================================================
    fig, axes = plt.subplots(
        num_analog_panels + num_digital_panels,
        sharex=True,
        figsize=(7.5, 7.5),
        height_ratios=num_digital_panels * [1] * num_analog_panels + [2],
    )
    if num_panels == 1:
        axes = [axes]
    fig.tight_layout()

    analogLabels = []
    if num_analog_panels > 0:
        for key, axis in zip(unit_variables__analog.keys(), axes[:-1]):
            (
                axis.set_ylabel(symbol_quantities[key] + " [{}]".format(key))
                if key in symbol_quantities
                else key
            )
            for variable, color in zip(unit_variables__analog[key], colors):
                array = tline[tline["variable"] == variable]
                axis.plot(array["time"], array["value"], marker="o", ms=3)
                analogLabels.append(
                    axis.text(0, array.iat[0, 2], variable, color=color)
                )
            if do_context:
                _draw_context(axis, info__context, cmap__context=cmap__context)
    #
    # =====================================================================
    # DIGITAL
    # =====================================================================
    digitalLabels = []
    if num_digital_panels > 0:
        divider = 1.5 * len(variables__digital)
        axes[-1].set_ylabel("Digital")

        for variable, offset, color in zip(
            variables__digital, range(len(list(variables__digital))), colors
        ):
            baseline = offset / divider
            array = tline[tline["variable"] == variable]
            axes[-1].axhline(baseline, color=color, linestyle=":", alpha=0.5)
            axes[-1].axhline(baseline + 1, color=color, linestyle=":", alpha=0.5)
            axes[-1].step(
                array["time"],
                array["value"] + baseline,
                where="post",
                color=color,
                marker="o",
                ms=3,
            )
            digitalLabels.append(
                axes[-1].text(0, baseline, variable + "_OFF", color=color)
            )
            digitalLabels.append(
                axes[-1].text(0, baseline + 1, variable + "_ON", color=color)
            )
        axes[-1].set_yticks([i / divider for i in range(len(list(variables__digital)))])
        axes[-1].set_yticklabels([])
        if do_context:
            _draw_context(axes[-1], info__context, cmap__context=cmap__context)

    for anchorTime in tline__anchors["time"]:
        for axis in axes:
            axis.axvline(anchorTime, color="0.5", linestyle="--")

    ax2 = axes[0].twiny()
    ax2.set_xlim(axes[0].get_xlim())
    ax2.set_xticks(list(tline__anchors["time"]))  # Set ticks at the specified x-values
    ax2.set_xticklabels(list(tline__anchors["context"]))

    def _sync_axes(event):
        xlim = axes[0].get_xlim()
        ax2.set_xlim(xlim)
        for label in analogLabels + digitalLabels:
            label.set_position((0.9 * xlim[0] + 0.1 * xlim[1], label.get_position()[1]))

    # Connect the sync function to the 'xlim_changed' event
    axes[0].callbacks.connect("xlim_changed", _sync_axes)

    if do_show:
        plt.show()

    return fig, axes
