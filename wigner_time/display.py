# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from wigner_time import timeline as tl


def display_new(timeline, variables=None) :
    timeline = timeline.sort_values("time", ignore_index=True)

    max_time=timeline.loc[timeline["context"]!="ADwin_Finish","time"].max() # apart from the finish section

    timeline.loc[timeline["context"] == "ADwin_LowInit", "time"] = -0.5
    timeline.loc[timeline["context"] == "ADwin_Init",    "time"] = -0.25
    timeline.loc[timeline["context"] == "ADwin_Finish",  "time"] = max_time+0.25

    if variables is None : variables = timeline["variable"].unique()
    variables = sorted(variables, key=(lambda s: s[s.find("_") + 1]))

    analog_variables = { key: [s for s in variables if s.endswith(value)] for key, value in tl.ANALOG_SUFFIXES.items() }
    analog_variables = { key: value for key, value in analog_variables.items() if value }

    digital_variables = list( filter( lambda s : s not in [item for sublist in analog_variables.values() for item in sublist] and s!="Anchor" , variables ) )

    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']

    fig, axes = plt.subplots(
       len(analog_variables)+1 , sharex=True, figsize=(7.5, 7.5)
    )  # TODO: make this more flexible, preferably sth like %matplotlib

    fig.tight_layout()

    for key, axis in zip(analog_variables.keys(),axes[:-1]) :
        axis.set_ylabel(key+" [{}]".format(tl.ANALOG_SUFFIXES[key][2:]))
        for variable, color in zip(analog_variables[key],colors) :
            array=timeline.loc[ timeline["variable"] == variable, ["time", "value", "context"] ].to_numpy()
            axis.plot(array[:,0],array[:,1])
            axis.text(array[0,0],array[0,1],variable,color=color)

    axes[-1].set_ylabel("Digital channels")
    for variable, offset, color in zip(digital_variables,range(len(list(digital_variables))),colors) :
        baseline=offset/10.
        array=timeline.loc[ timeline["variable"] == variable, ["time", "value", "context"] ].to_numpy()
        axes[-1].step(array[:,0],array[:,1]+baseline,where="post",color=color)
        axes[-1].axhline(baseline, color=color, linestyle=":")
    axes[-1].set_yticks( [i/10. for i in range(len(list(digital_variables))) ] )
    axes[-1].set_yticklabels(digital_variables)

    # shade init and finish:
    axes[-1].axvspan(-.75, 0, color='gray', alpha=0.3)
    axes[-1].axvspan(max_time, max_time+.5, color='gray', alpha=0.3)

    anchors=timeline.loc[ timeline["variable"] == "Anchor", ["time", "context"] ].to_numpy()
    for anchorTime in anchors[:,0] :
        for axis in axes :
            axis.axvline(anchorTime, color='0.5', linestyle='--')

    ax2=axes[0].twiny()
    ax2.set_xlim(axes[0].get_xlim())
    ax2.set_xticks(list(anchors[:,0]))  # Set ticks at the specified x-values
    ax2.set_xticklabels(list(anchors[:,1]))

    def sync_axes(event):
        ax2.set_xlim(axes[0].get_xlim())

    # Connect the sync function to the 'xlim_changed' event
    axes[0].callbacks.connect('xlim_changed', sync_axes)

    # Display the plot
    plt.show()






def display(df, xlim=None, variables=None):
    """
    Plot the experimental plan.

    Note that the last value for a device is taken as the end value.

    TODO: display works on the operational level, where the (low)init and the actual t=0 of the timeline both have t=0, which can mess up the display of identical variables
    """
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
