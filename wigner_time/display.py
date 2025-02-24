# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

# Block module based on dependency
import importlib.util

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from wigner_time import timeline as tl

from wigner_time.adwin import display as adwin_display


def display(
    timeline,
    variables=None,
    suffixes__analogue={"Voltage": "__V", "Current": "__A", "Frequency": "__MHz"},
):
    # TODO:
    # - This should be ADwin-independent
    # - Branch based on whether ADwin is installed??
    # - Allow for expansion and time-resolution.
    # suffixes__analogue is temporarily part of the API until we understand what to replace it with
    return adwin_display.channels(timeline, variables, suffixes__analogue)


def display_old(df, xlim=None, variables=None):
    """
    Plot the experimental plan.

    Note that the last value for a device is taken as the end value.

    # DEPRECATED:
    # - Haven't actually checked how different the two displays are, but assuming the one above to be the current one.

    """
    # TODO: display works on the operational level, where the (low)init and the actual t=0 of the timeline both have t=0, which can mess up the display of identical variables
    # - What is `xlim` for ?
    df = df.sort_values("time", ignore_index=True)
    if variables is None:
        variables = df["variable"].unique()
    variables = sorted(variables, key=(lambda s: s[s.find("_") + 1]))

    invalid_variables = np.setdiff1d(variables, df["variable"])
    if invalid_variables.size > 0:
        raise ValueError(
            f"Variables {list(invalid_variables)} are invalid. The list of variables must be a subset of the following list: {list(df['variable'].unique())}"
        )

    time_end = df["time"].max()

    ylim_margin_ratio = 0.05  # so that lines remain visible at the edges of ylim
    ylim_margin_equal = 0.01  # in case of identical low and high ylim

    plt.style.use("seaborn-v0_8")
    cmap = plt.get_cmap("tab10")

    fig, axes = plt.subplots(
        len(variables), sharex=True, squeeze=False, figsize=(7.5, 7.5)
    )  # TODO: make this more flexible, preferably sth like %matplotlib

    for i, a, d in zip(range(len(variables)), axes[:, 0], variables):
        dff = df.query("variable=='{}'".format(d))

        if (
            dff["time"].max() != time_end
        ):  # to stretch each timeline to the same time_end
            row = dff.iloc[[-1]].copy()
            row["time"] = time_end

            dff = pd.concat([dff, row]).reset_index(drop=True)

        a.step(
            dff["time"],
            dff["value"],
            where="post",
            marker="o",
            ls="--",
            ms=5,
            color=cmap(i),
        )  # using the step function for plotting, stepping only after we reach the next value
        a.set_ylabel("Value")
        a.set_title(d, y=0.5, ha="center", va="center", alpha=0.6)

        if "__" not in d:  # digital variables
            a.set_ylim(0 - ylim_margin_ratio, 1 + ylim_margin_ratio)

        if xlim != None:
            plt.xlim(
                xlim[0], xlim[1]
            )  # xlim has to be a list, if given, we look at only the desired interval

            if "__" in d:  # analog variables
                t0, t1 = [
                    dff["time"][dff["time"] <= lim].max() for lim in xlim
                ]  # time of last change of value before the start and end of xlim
                y_in = dff[np.logical_and(dff["time"] >= t0, dff["time"] <= t1)][
                    "value"
                ]  # y values within xlim
                if y_in.min() != y_in.max():
                    ylim_margin = ylim_margin_ratio * (y_in.max() - y_in.min())
                    a.set_ylim(y_in.min() - ylim_margin, y_in.max() + ylim_margin)
                else:
                    a.set_ylim(
                        y_in.min() - ylim_margin_equal, y_in.max() + ylim_margin_equal
                    )

    axes[-1][0].set_xlabel("Time /s")

    plt.plot()
    plt.show()
