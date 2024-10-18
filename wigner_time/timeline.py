# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

"""
Will use multiple layers of abstraction:
- operational (time sequence: probe-on, probe-off etc.)
- variable (time sequence of independent degrees of freedom: AOM_probe_power 5V)
- ADwin (ADwin-specific details )

It is a goal to be able to go up and down through the layers of abstraction.

TODO:
- Add proper basics of 'sanitize' function
- channel layer
    - think about how to deal with different modes (normal, burst etc.)
    - validation
"""

from collections.abc import Iterable
from copy import deepcopy
from datetime import time
from typing import Callable

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import funcy
from munch import Munch

from wigner_time import connection as con
from wigner_time import ramp as ramp
from wigner_time import util as util
from wigner_time import input as wtinput

###############################################################################
#                   Constants                                                 #
###############################################################################

TIME_RESOLUTION = 1.0e-6

###############################################################################
#                   Internal functions
###############################################################################


def combine(*dfs):
    return pd.concat(dfs, ignore_index=True)


def process_dataframe(df, num_decimal_places=6):
    """

    Rounds the values (of voltages) and drops duplicates of values in pandas dataframes.
    Should be used for one device at a time!
    """
    # TODO: make this more universal, connect the rounding sensitivity to ADwin or device specifications!

    df["value"] = df["value"].round(num_decimal_places)
    return df.drop_duplicates(subset="value", keep="first")


def previous(
    timeline: pd.DataFrame, variable=None, sort_by="time", column="variable", index=-1
):
    """
    Returns last occurence of `sort_by` - `value` pair of 'variable'.
    Usually the `time` - `value` pair.

    Returns `None` if no previous value exists.

    """
    # TODO: Allow for just latest row

    if not timeline[sort_by].is_monotonic_increasing:
        tl_sorted = timeline.sort_values(sort_by)
    else:
        tl_sorted = timeline

    if variable is not None:
        qy = tl_sorted.query("{}=='{}'".format(column, variable))
        if not qy.empty:
            return qy.iloc[index]
        else:
            return None
    else:
        return tl_sorted.iloc[index]


def previous_value(
    timeline, variable=None, sort_by="time", column="variable", index=-1
):
    prev = previous(timeline, variable, sort_by, column, index)
    if prev is not None:
        return prev["value"]
    else:
        return None


def previous_time(timeline, variable=None, sort_by="time", column="variable", index=-1):
    prev = previous(timeline, variable, sort_by, column, index)
    if prev is not None:
        return prev["time"]
    else:
        return None


def previous_context(
    timeline, context, sort_by="time", label_value="value", column="context"
):
    return previous(timeline, context, sort_by=sort_by, column=column)


###############################################################################
#                   Main functions
###############################################################################
def create(
    *vtvc,
    timeline=None,
    context=None,
    t=0.0,
    relative=False,
    labels=["time", "variable", "value", "context"],
    **vtvc_dict,
):
    """
    Does what it says on the tin: establishes a new timeline according to the given (flexible) input collection. If 'timeline' is also specified, then it concatenates the new creation with the existing one.


    Accepts programmatic and manual input.

    TODO: document the possible combinations of arguments ordered according to usecases 

    variable_time_values (*vtvc) has the form:
    variable, time, value, context
    OR
    variable, [[time, value],...]
    OR
    [['variable', value]]
    OR
    [['variable', [time, value]]]
    OR
    [['variable', [[time, value],
                  [time002,value002],
                  ...]]]

    but when unspecified, is replaced by the dictionary form (**vtvc_dict)

    The [time,value] list can also be replaced with [time,value,context] if you would like to specify data-specific context.

    NOTE: It seems to be the case (on the internet) that dataframes use less memory than lists of dictionaries or dictionaries of lists (in general).
    """

    schema = {"time": float, "variable": str, "value": float, "context": str}
    rows = wtinput.rows_from_arguments(*vtvc, time=t, context=context, **vtvc_dict)
    if (len(rows[0]) != 4) and (context is not None):
        schema.pop("context")
    new = pd.DataFrame(rows, columns=schema.keys()).astype(schema)
    if timeline is not None and relative :
        _pt_max = previous_time(timeline)
        if _pt_max is None: raise ValueError("Previous time not found!")
        for index, row in new.iterrows() : new.at[index,"time"] += _pt_max

    result = pd.concat([timeline, new]) if timeline is not None else new
    return result.sort_values(labels[0], ignore_index=True)



def set(
    *vtvc,
    timeline=None,
    context=None,
    t=None,
    relative=False,
    labels=["time", "variable", "value", "context"],
    **vtvc_dict,
):
    """
    Creates a timeline for a single or many variables the same as the 'create' function.

    One difference is that when an existing timeline is not specified, then it returns an anonymous function for use in function chaining, like the other main functions in this module. Also, the default starting time and context is inherited from previous timelines.

    """
    if timeline is None:
        return lambda x: set(
            *vtvc,
            timeline=x,
            context=context,
            t=t,
            relative=relative,
            labels=labels,
            **vtvc_dict,
        )

    else:
        prev = previous(timeline)
        if prev is not None:
            if (context is None) and "context" in prev.keys():
                context = prev["context"]
            if (t is None) and "time" in prev.keys():
                t = prev["time"]

        return create(
            *vtvc,
            timeline=timeline,
            context=context,
            t=t,
            relative=relative,
            labels=labels,
            **vtvc_dict,
        )


def wait(
    t=None, variables=None, timeline=None, relative=Munch({"time": True}), context=None
):
    """
    For specific circumstances. Makes sure that the variable has the same value at a later t or at `t`s later (depending on the value of relative.time).

    If no time is given (`t=None`) then `wait` simply makes sure that all variables remain the same at the last time.

    `t` - either the 'duration' to wait or the absolute 'time_end'.
    `relative` - `dict` must contain a 'time' keyword.

    """

    _variables = deepcopy(variables)

    if timeline is None:
        return lambda x: wait(
            variables=variables,
            t=t,
            timeline=x,
            relative=relative,
            context=context,
        )

    _pt_max = previous_time(timeline)
    if t is None:
        relative.time = False
        t = _pt_max

    if relative.time:
        tnew = t + _pt_max
    else:
        tnew = t

    # filter out variables that already have a value at the given time
    _variables_excluded = timeline.query(f"time=={tnew}")["variable"].values
    if variables is None:
        _variables = [
            v for v in timeline["variable"].unique() if v not in _variables_excluded
        ]

    _variables = util.ensure_iterable(_variables)

    if _variables:
        _rows = []
        for _var in _variables:
            _p = previous(timeline, _var)
            if _p is None:
                raise ValueError("Previous value ({}) doesn't exist!".format(_var))

            _pv = _p["value"]
            if _pv is None:
                raise ValueError("Previous value ({}) doesn't exist!".format(_var))

            if (context is None) and "context" in _p.keys():
                context = _p["context"]

            _rows.append([_var, [[tnew, _pv]]])

        return combine(*[timeline, create(_rows, context=context)])
    else:
        return timeline


def next(
    *vtvc,
    timeline=None,
    context=None,
    t=None,  # this is interpreted as time_end if !relative["time"] - maybe this should be renamed to `time` or maybe `duration`?
    relative={"time": True, "value": False},
    function=ramp.tanh,
    fargs={},
    time_start=None,
    value_start=None,
    globalRelative=True,
    **vtvc_dict,
):
    """
    vtvc is variable,t,value,context (following that of 'create')

    Here, `t` is interpreted as time_end if `relative={"time": True, ...}`
    NOTE: The order of variables and time are different in `wait`.
    """
    # TODO: Should fargs be a dictionary?
    if timeline is None:
        return lambda x: next(
            *vtvc,
            timeline=x,
            context=context,
            t=t,
            relative=relative,
            function=function,
            fargs=fargs,
            time_start=time_start,
            value_start=value_start,
            globalRelative=globalRelative,
            **vtvc_dict,
        )

    if (t is not None) and (t < 0):
        raise ValueError(
            'cannot go back in time or create quantum superpositions with "timeline.next"!'
        )

    input = wtinput.convert(*vtvc, time=t, context=context, **vtvc_dict)

    frames = []
    if input is not None:
        if globalRelative : _pt_max=previous_time(timeline)
        for variable, values in input:
            if len(values) > 1:
                raise ValueError(
                    "Badly formatted input to 'next'. There should only be one collection of t and value per variable."
                )
            t, value = values[0][:2]
            if not (t > 0):
                raise ValueError("Duration cannot be zero for changing values.")

            prev = previous(timeline, variable)
            if globalRelative : prev.values[0]=_pt_max

            point_start = [time_start, value_start]

            if prev is not None:
                if context is None and "context" in prev.keys():
                    context = prev["context"]

            if (time_start is None) or (value_start is None):
                if prev is not None:
                    ps = point_start
                    for i, l, p in zip(range(2), relative.keys(), point_start):
                        if p is None:
                            ps[i] = prev[l]
                    point_start = ps

            for x in point_start:
                if x is None:
                    raise ValueError(
                        "Tried to use 'next' without starting time and value. Check that you're trying to change an existing variable."
                    )

            frames.append(
                create(
                    variable,
                    function(
                        point_start,
                        ramp.to_point_end(
                            point_start,
                            t,
                            value,
                            relative=list(relative.values()),
                        ),
                        **fargs,
                    ),
                    context=context,
                )
            )

        # Rounding up the values and dropping duplicates
        # TODO: process_dataframe can be replaced with sanitize here?
        frames = [process_dataframe(frame) for frame in frames]

        return combine(*([timeline] + frames))


def shift(
    *vtvc,
    timeline=None,
    context=None,
    t=None,
    relative={"time": True, "value": True},
    function=ramp.tanh,
    fargs={},
    time_start=None,
    value_start=None,
    globalRelative=True,
    **vtvc_dict,
):
    """
    Convenience function. Just `next`, but with relative defaults.

    `time` and `value` are relative 'shift's with respect to the previous values.
    """
    return next(
        *vtvc,
        timeline=timeline,
        context=context,
        t=t,
        relative=relative,
        function=function,
        fargs=fargs,
        time_start=time_start,
        value_start=value_start,
        globalRelative=globalRelative,
        **vtvc_dict,
    )


def stack(firstArgument, *fs: list[Callable]):
    """
    For stacking modifications to the timeline in a composable way.
    """
    if isinstance(firstArgument, pd.DataFrame) :
        return funcy.compose(*fs[::-1])(firstArgument)
    else :
        return funcy.compose(*fs[::-1],firstArgument)


def update(timeline, *fs: list[Callable]):
    """
    For stacking modifications to the timeline in a composable way.

    TODO: probably OBSOLATE beside the above function
    """
    return funcy.compose(*fs[::-1])(timeline)


def is_value_within_range(value, unit_range):
    if pd.isnull(unit_range):
        # If unit_range is NaN, consider it as within range
        return True
    else:
        min_value, max_value = unit_range
        return min_value <= value <= max_value


def sanitize(df):
    """
    WARNING: The list of expected column names needs to be kept up to date.

    TODO:Remove points within a certain time interval (no point being too precise).
    TODO:Instead of list of rows, only modify the value of an integer (which gives the number of rows).
    """
    # List to store rows with values outside the range
    out_of_range_rows = []

    # Iterate through each row
    for index, row in df.iterrows():
        # Check if the 'value' is within the specified 'unit_range'
        if not is_value_within_range(row["value"], row["unit_range"]):
            # Print or handle the row where the value is outside the range
            print(
                f"Value {row['value']} is outside device unit range {row['unit_range']} for {row['variable']} at time {row['time']} at dataframe index {index}."
            )

            # Append the row index to the list
            out_of_range_rows.append(index)

    # Raise ValueError after printing all relevant information
    if out_of_range_rows:
        raise ValueError(
            f"Values outside the device unit range in {len(out_of_range_rows)} rows! YOU MUST CHANGE THESE BEFORE PROCEEDING!"
        )

    return df.astype(
        {
            "variable": str,
            "module": int,
            "channel": int,
            # "context": str,
            "cycle": int,
            "value_digits": int,
        },
        errors="ignore",
    )


###############################################################################
#                                VISUALISATION                                #
###############################################################################


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
