# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

# Block module based on dependency
import importlib.util

from wigner_time.anchor import LABEL__ANCHOR

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")

# Normal imports
import matplotlib.axes as mpa
import matplotlib.pyplot as plt
import numpy as np

from wigner_time.adwin import core as adwin
from wigner_time import timeline as tl


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


def channels(
    timeline,
    variables=None,
    suffixes__analogue={"Voltage": "__V", "Current": "__A", "Frequency": "__MHz"},
    do_context=True,
    do_show=True,
):
    timeline.sort_values("time", inplace=True, ignore_index=True)

    info__context = tl.context_info(timeline)

    max_time = timeline.loc[
        timeline["context"] != "ADwin_Finish", "time"
    ].max()  # apart from the finish section

    # TODO: This shouldn't be necessary once the timeline is verified
    timeline.loc[timeline["context"] == "ADwin_LowInit", "time"] = -0.5
    timeline.loc[timeline["context"] == "ADwin_Init", "time"] = -0.25
    timeline.loc[timeline["context"] == "ADwin_Finish", "time"] = max_time + 0.25

    if variables is None:
        variables = timeline["variable"].unique()
    variables = sorted(variables, key=(lambda s: s[s.find("_") + 1]))

    # TODO:
    # - Analogue and digital devices should be identified by proper methods (defined in a reasonable place)
    # - Analog suffices shouldn't be defined here or in `timeline`; these are too experiment-specific.
    analog_variables = {
        key: value
        for key, value in {
            key: [s for s in variables if s.endswith(value)]
            for key, value in suffixes__analogue.items()
        }.items()
        if value
    }

    digital_variables = list(
        filter(
            lambda s: (LABEL__ANCHOR not in s) and ("__" not in s),
            variables,
        )
    )

    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]

    analogPanels = len(analog_variables)
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
    for key, axis in zip(analog_variables.keys(), axes[:-1]):
        axis.set_ylabel(key + " [{}]".format(suffixes__analogue[key][2:]))
        for variable, color in zip(analog_variables[key], colors):
            array = timeline[timeline["variable"] == variable]
            axis.plot(array["time"], array["value"], marker="o", ms=3)
            analogLabels.append(axis.text(0, array.iat[0, 2], variable, color=color))
        if do_context:
            _draw_context(axis, info__context)

    divider = 1.5 * len(digital_variables)
    digitalLabels = []
    axes[-1].set_ylabel("Digital channels")

    for variable, offset, color in zip(
        digital_variables, range(len(list(digital_variables))), colors
    ):

        baseline = offset / divider
        array = timeline[timeline["variable"] == variable]
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
    axes[-1].set_yticks([i / divider for i in range(len(list(digital_variables)))])
    axes[-1].set_yticklabels([])
    if do_context:
        _draw_context(axes[-1], info__context)

    # shade init and finish:
    for ax in axes:
        ax.axvspan(-0.75, 0, color="gray", alpha=0.3)
        ax.axvspan(max_time, max_time + 0.5, color="gray", alpha=0.3)

    anchors = timeline[timeline["variable"] == "Anchor"]
    for anchorTime in anchors["time"]:
        for axis in axes:
            axis.axvline(anchorTime, color="0.5", linestyle="--")

    ax2 = axes[0].twiny()
    ax2.set_xlim(axes[0].get_xlim())
    ax2.set_xticks(list(anchors["time"]))  # Set ticks at the specified x-values
    ax2.set_xticklabels(list(anchors["context"]))

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

    sys.path.append(str(pl.Path.cwd() / "doc"))
    import experiment as ex
    from wigner_time import timeline as tl

    tline = tl.stack(ex.init(), ex.MOT(), ex.MOT_detunedGrowth())
    channels(tline)
