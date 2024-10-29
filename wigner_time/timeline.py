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
    - validation
"""

from collections.abc import Iterable
from copy import deepcopy
from datetime import time
from typing import Callable

import numpy as np
import pandas as pd
import funcy
from munch import Munch # TODO: do we really want to depend on this?

from wigner_time import connection as con
from wigner_time import ramp_utils as ramp_utils
from wigner_time import util as util
from wigner_time import input as wtinput

###############################################################################
#                   Constants                                                 #
###############################################################################

TIME_RESOLUTION = 1.0e-6

ANALOG_SUFFIXES = {"Voltage" : "__V", "Current" : "__A", "Frequency" : "__MHz"}


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


def previous_value(timeline, variable=None, sort_by="time", column="variable", index=-1):
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


def previous_context(timeline, variable=None, sort_by="time", column="variable", index=-1):
    prev = previous(timeline, variable, sort_by, column, index)
    if prev is not None:
        return prev["context"]
    else:
        return None


###############################################################################
#                   Main functions
###############################################################################
def create(
    *vtvc,
    timeline=None,
    context=None,
    t=0.0,
    relative=Munch({"time": False, "value":False}),
    **vtvc_dict,
):
    """
    Does what it says on the tin: establishes a new timeline according to the given (flexible) input collection. If 'timeline' is also specified, then it concatenates the new creation with the existing one.

    Accepts programmatic and manual input.

    TODO: implement relative value

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

    if timeline is not None and relative["time"] :
        tAnchor = previous_time(timeline,variable="Anchor")
        if tAnchor is None: raise ValueError("Previous time not found!")
        for index, row in new.iterrows() : new.at[index,"time"] += tAnchor

    result = pd.concat([timeline, new]) if timeline is not None else new

    return result.sort_values("time", ignore_index=True)



def set(
    *vtvc,
    timeline=None,
    context=None,
    t=0.0,
    relative=Munch({"time": True, "value": False}),
    **vtvc_dict,
):
    """
    Creates a timeline for a single or many variables the same as the 'create' function.

    One difference is that when an existing timeline is not specified, then it returns an anonymous function for use in function chaining, like the other main functions in this module.

    """
    if timeline is None:
        return lambda x: set(
            *vtvc,
            timeline=x,
            context=context,
            t=t,
            relative=relative,
            **vtvc_dict,
        )

    else:
        if context is None : context = previous_context(timeline)

        return create(
            *vtvc,
            timeline=timeline,
            context=context,
            t=t,
            relative=relative,
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

    OBSOLATE?

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


def anchor(t, timeline=None, relative=Munch({"time": True}), context=None) :
    if timeline is None :
        return lambda x : anchor(t=t,timeline=x,relative=relative,context=context)

    try :
        return set("Anchor",t,0,timeline=timeline,context=context,relative=relative)
    except ValueError :
        return set("Anchor",t,0,timeline=timeline,context=context,relative={"time": False})



def ramp(
    *vtvc,
    timeline=None,
    context=None,
    t=0.0,
    relative=Munch({"time": True, "value": False}),
    duration=None,
    function=ramp_utils.tanh,
    fargs={},
    **vtvc_dict,
):
    """
    vtvc is variable,t,value,context (following that of 'create')

    `t` is starting time, which is relative to the previous anchor if `relative={"time": True, ...}`

    the starting value of the ramp is the previous value of the variable, and if it doesn’t exist, an exception is thrown

    """
    # TODO: Should fargs be a dictionary?

    if timeline is None:
        return lambda x: ramp(
            *vtvc,
            timeline=x,
            context=context,
            t=t, # starting time
            relative=relative,
            duration=duration,
            function=function,
            fargs=fargs,
            **vtvc_dict,
            )
    input_data = wtinput.convert(*vtvc, time=t, context=context, **vtvc_dict)

    frames = []

    if input_data is not None:
        tAnchor=previous_time(timeline,variable="Anchor")

        for variable, values in input_data:
            if len(values) > 1:
                raise ValueError("Badly formatted input to 'ramp'. There should only be one collection of t and value per variable.")

            t, value = values[0][:2]

            if relative["time"] and tAnchor is not None : t+=tAnchor

            prev = previous(timeline, variable)

            if prev is None : raise ValueError("Tried to use 'ramp' without previous value for variable {}".format(variable))

            if context is None : context = prev["context"]
            if relative["value"] : value += prev["value"]

            point_start = [t, prev["value"]]

            frames.append(
                create(
                    variable,
                    function(point_start,[t+duration,value],**fargs),
                    context=context,
                    )
                )

        # Rounding up the values and dropping duplicates
        # TODO: process_dataframe can be replaced with sanitize here?
        frames = [process_dataframe(frame) for frame in frames]

    return combine(*([timeline] + frames))


def next(
    *vtvc,
    timeline=None,
    context=None,
    t=None,  # this is interpreted as time_end if !relative["time"] - maybe this should be renamed to `time` or maybe `duration`?
    relative=Munch({"time": True, "value": False}),
    function=ramp_utils.tanh,
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

    OBSOLATE?
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
                        ramp_utils.to_point_end(
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
    relative=Munch({"time": True, "value": True}),
    function=ramp_utils.tanh,
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


def time_from_anchor_to_context(timeline, t=None, anchorToContext=None) :
    if anchorToContext is not None :
        s=timeline.loc[(timeline['variable'] == "Anchor") & (timeline['context'] == anchorToContext), 'time']
        if s.empty and t is None : raise ValueError("Anchor in context {} not found, and absolute time is not supplied".format(anchorToContext))
        t = ( s.max() if not s.empty else 0. ) + ( t if t is not None else 0. )

    return t
