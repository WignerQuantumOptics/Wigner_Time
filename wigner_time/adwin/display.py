# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

# ============================================================
# Block module based on dependency
import importlib.util

from wigner_time import anchor

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")

# ============================================================
# Normal imports
import matplotlib.axes as mpa
import matplotlib.pyplot as plt
import numpy as np
import wigner_time.variable as wt_variable

# ^^^ TODO: will use for special contexts
from wigner_time import timeline as tl
from wigner_time.adwin import core as wt_adwin
import wigner_time.anchor as anchor
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


def _draw_context(axis: mpa.Axes, info__context, alpha=0.1):
    ys = axis.get_ylim()
    y__center = np.mean(ys)

    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    for con, col in zip(info__context.keys(), colors):
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
):
    """
    Displays the given `tline`, filtered by `variable`, in terms of different quantites, i.e. by common `unit`. The mapping between `unit` and 'quantity' can be provided as a dictionary.
    """
    # TODO:
    # - Separate style and content
    # - abstract out ADwin-only things
    if variables:
        tline = wt_frame.subframe(timeline, "variable", variables)
    else:
        tline = timeline
    tline.sort_values("time", inplace=True, ignore_index=True)

    info__context = tl.context_info(tline)

    max_time = tline.loc[
        tline["context"] != "ADwin_Finish", "time"
    ].max()  # apart from the finish section

    # TODO: This shouldn't be necessary once the tline is verified

    tline.loc[tline["context"] == "ADwin_LowInit", "time"] = -0.5
    tline.loc[tline["context"] == "ADwin_Init", "time"] = -0.25

    tline.loc[tline["context"] == "ADwin_Finish", "time"] = max_time + 0.25

    if variables is None:
        variables = tline["variable"].unique()

    units = wt_variable.units(tline)

    unit_variables__analog = {
        u: [v for v in variables if wt_variable.unit(v) == u]
        for u in units
        if u not in ["digital", LABEL__ANCHOR]
    }
    unit_variables__digital = {
        u: [v for v in variables if wt_variable.unit(v) == u]
        for u in units
        if u in ["digital"]
    }
    tline__anchors = tline[anchor.mask(tline)]

    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    analogPanels = len(unit_variables__analog)
    fig, axes = plt.subplots(
        analogPanels + 1,
        sharex=True,
        figsize=(7.5, 7.5),
        height_ratios=[1] * analogPanels + [2],
    )
    if analogPanels == 0:
        axes = [axes]

    fig.tight_layout()

    analogLabels = []
    for key, axis in zip(unit_variables__analog.keys(), axes[:-1]):
        (
            axis.set_ylabel(symbol_quantities[key] + " [{}]".format(key))
            if key in symbol_quantities
            else key
        )
        for variable, color in zip(unit_variables__analog[key], colors):
            array = tline[tline["variable"] == variable]
            axis.plot(array["time"], array["value"], marker="o", ms=3)
            analogLabels.append(axis.text(0, array.iat[0, 2], variable, color=color))
        if do_context:
            _draw_context(axis, info__context)

    divider = 1.5 * len(unit_variables__digital)
    digitalLabels = []
    axes[-1].set_ylabel("Digital channels")

    for variable, offset, color in zip(
        unit_variables__digital, range(len(list(unit_variables__digital))), colors
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
        digitalLabels.append(axes[-1].text(0, baseline, variable + "_OFF", color=color))
        digitalLabels.append(
            axes[-1].text(0, baseline + 1, variable + "_ON", color=color)
        )
    axes[-1].set_yticks(
        [i / divider for i in range(len(list(unit_variables__digital)))]
    )
    axes[-1].set_yticklabels([])
    if do_context:
        _draw_context(axes[-1], info__context)

    # shade init and finish:
    for ax in axes:
        ax.axvspan(-0.75, 0, color="gray", alpha=0.3)
        ax.axvspan(max_time, max_time + 0.5, color="gray", alpha=0.3)

    for anchorTime in tline__anchors["time"]:
        for axis in axes:
            axis.axvline(anchorTime, color="0.5", linestyle="--")

    ax2 = axes[0].twiny()
    ax2.set_xlim(axes[0].get_xlim())
    ax2.set_xticks(list(tline__anchors["time"]))  # Set ticks at the specified x-values
    ax2.set_xticklabels(list(tline__anchors["context"]))

    def sync_axes(event):
        xlim = axes[0].get_xlim()
        ax2.set_xlim(xlim)
        for label in analogLabels + digitalLabels:
            label.set_position((0.9 * xlim[0] + 0.1 * xlim[1], label.get_position()[1]))

    # Connect the sync function to the 'xlim_changed' event
    axes[0].callbacks.connect("xlim_changed", sync_axes)

    if do_show:
        plt.show()

    return fig, axes


if __name__ == "__main__":

    import pathlib as pl
    import sys

    sys.path.append(str(pl.Path.cwd() / "doc"))
    import experiment as ex
    from wigner_time import timeline as tl

    tline = tl.stack(ex.init(), ex.MOT(), ex.MOT_detunedGrowth())
    quantities(tline)
