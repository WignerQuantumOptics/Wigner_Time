# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

"""
Multiple layers of abstraction:
- operational (time sequence: probe-on, probe-off etc.) – this should go to notebooks / experiment specific packages
- variable (time sequence of independent degrees of freedom: AOM_probe_power 5V)
- ADwin (ADwin-specific details)

It is a goal to be able to go up and down through the layers of abstraction.
"""

from copy import deepcopy
from typing import Callable

import funcy

from wigner_time import input as WTinput
from wigner_time import ramp_function as WTramp_function
from wigner_time.internal import dataframe as WTframe
from wigner_time.internal import origin as WTorigin

###############################################################################
#                   Constants                                                 #
###############################################################################

TIME_RESOLUTION = 1.0e-6

ANALOG_SUFFIXES = {"Voltage": "__V", "Current": "__A", "Frequency": "__MHz"}
# TODO: Should be deleted, but currently needed by display

_SCHEMA = {"time": float, "variable": str, "value": float, "context": str}
_COLUMN_NAMES__RESERVED = list(_SCHEMA.keys()) + [
    "unit_range",
    "safety_range",
]
"""These column names are assumed to exist and are used in core functions. Be careful about editing them."""

###############################################################################
#                   Utility functions
###############################################################################


def previous(
    timeline: WTframe.CLASS,
    variable=None,
    column="variable",
    sort_by=None,
    index=-1,
):
    """
    Returns a row from the previous timeline. By default, this is done by finding the highest value for time and returning that row. If `sort_by` is specified (e.g. 'time'), then the dataframe is sorted and then the row indexed by `index` is returned.

    Raises ValueError if the specified variable, or timeline, doesn't exist.
    """
    # DEPRECATED:
    # TODO: Delete this in favour of the implementation in origin?
    # Can be exposed through the package API
    if variable is not None:
        tl__filtered = timeline[timeline[column] == variable]
        if tl__filtered.empty:
            raise ValueError("Previous {} not found".format(variable))
    else:
        tl__filtered = timeline

    if sort_by is None:
        return WTframe.row_from_max_column(tl__filtered)
    else:
        if not timeline[sort_by].is_monotonic_increasing:
            tl__filtered.sort_values(sort_by, inplace=True)
            return tl__filtered.iloc[index]
        else:
            return timeline.iloc[index]


###############################################################################
#                   Main functions
###############################################################################
def create(
    *vtvc,
    timeline=None,
    t=0.0,
    context=None,
    origin=None,
    schema=_SCHEMA,
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

    If you supply an additional timeline, the result will be concatenated with this and the new timeline (if one isn't specified) will inherit the old context.

    NOTE: It seems to be the case that dataframes use less memory than lists of dictionaries or dictionaries of lists (in general).
    """

    rows = WTinput.rows_from_arguments(*vtvc, time=t, context=context, **vtvc_dict)
    if (len(rows[0]) != 4) and (context is None):
        schema.pop("context")
    new = WTframe.new(rows, columns=schema.keys()).astype(schema)

    if timeline is not None:
        newnew = WTorigin.update(timeline, new, origin=origin)

        if context is None:
            newnew['context'] = previous(timeline)['context']

        return WTframe.concat([timeline, newnew])

    return new


def update(
    *vtvc,
    timeline=None,
    context=None,
    t=0.0,
    relativeTime=True,
    relativeValue=False,
    **vtvc_dict,
):
    """
    Creates a timeline for a single or many variables the same as the 'create' function.

    One difference is that when an existing timeline is not specified,
    then it returns an anonymous function for use in function chaining,
    like the other main functions in this module.

    The chaining can be effected by the `stack` function.

    When context is not specified for a given variable, it is taken to be the latest context in the timeline.
    WARNING: this can lead to subtle bugs if the latest context is a special context
    """
    if timeline is None:
        return lambda x: update(
            *vtvc,
            timeline=x,
            context=context,
            t=t,
            relativeTime=relativeTime,
            relativeValue=relativeValue,
            **vtvc_dict,
        )

    else:
        if context is None:
            context = previous(timeline)["context"]

        return create(
            *vtvc,
            timeline=timeline,
            context=context,
            t=t,
            relativeTime=relativeTime,
            relativeValue=relativeValue,
            **vtvc_dict,
        )


def anchor(t, timeline=None, relativeTime=True, context=None):
    """
    Sets the anchor, optionally relative to the previous anchor
    """
    if timeline is None:
        return lambda x: anchor(
            t=t, timeline=x, relativeTime=relativeTime, context=context
        )

    try:
        return update(
            "Anchor",
            t,
            0,
            timeline=timeline,
            context=context,
            relativeTime=relativeTime,
        )
    except ValueError:
        return update(
            "Anchor", t, 0, timeline=timeline, context=context, relativeTime=False
        )


def ramp(
    *vtvc,
    timeline=None,
    context=None,
    t=None,
    origin="anchor",
    function=WTramp_function.tanh,
    fargs={},
    **vtvc_dict,
):
    """
    vtvc is variable,t,value,context (following that of 'create')

    Here, `t` is interpreted as time_end if `relative={"time": True, ...}`
    NOTE: The order of variables and time are different in `wait`.

    """
    # TODO: If origin is None, tries for anchor and then falls back to 'time'.
    # TODO: Should fargs be a dictionary?
    # - Maybe not. List (with the option of a dictionary) would be most flexible.
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
            **vtvc_dict,
        )

    if (t is not None) and (t < 0):
        raise ValueError(
            'cannot go back in time or create quantum superpositions with "timeline.ramp"!'
        )

    input = WTinput.convert(*vtvc, time=t, context=context, **vtvc_dict)

    frames = []
    if input is not None:
        for variable, values in input:
            if len(values) > 1:
                raise ValueError(
                    "Badly formatted input to 'next'. There should only be one collection of t and value per variable."
                )
            t, value = values[0][:2]
            if not (t > 0):
                raise ValueError("Duration cannot be zero for changing values.")

            prev = previous(timeline, variable)

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
                        WTramp_function.to_point_end(
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

        return WTframe.concat([timeline] + frames)


def stack(firstArgument, *fs: list[Callable]):
    """
    For stacking modifications to the timeline in a composable way.

    If the bottom of the stack is a timeline, the result is also timeline
    e.g.:
    stack(
        timeline,
        update(…),
        ramp(…)
    )
    the action of `update` and `ramp` is added to the existing `timeline` in this case.
    Equivalently:
    stack(
        update(…,timeline=timeline),
        ramp(…)
    )

    Otherwise, the result is a functional, which can be later be applied on an existing timeline.
    """
    if isinstance(firstArgument, WTframe.CLASS):
        return funcy.compose(*fs[::-1])(firstArgument)
    else:
        return funcy.compose(*fs[::-1], firstArgument)


def is_value_within_range(value, unit_range):
    # TODO: Shouldn't be here - internal function
    if WTframe.isnull(unit_range):
        # If unit_range is NaN, consider it as within range
        return True
    else:
        min_value, max_value = unit_range
        return min_value <= value <= max_value


def sanitize_values(timeline):
    """
    Ensures that the given timeline doesn't contain values outside of the given unit or safety range.
    """
    # TODO: Check for efficiency
    #
    if ("unit_range" in timeline.columns) or ("safety_range" in timeline.columns):
        df = deepcopy(timeline)

        # List to store rows with values outside the range
        rows__out_of_unit_range = []
        rows__out_of_safety_range = []

        # Iterate through each row
        for index, row in df.iterrows():
            if not is_value_within_range(row["value"], row["unit_range"]):
                print(
                    f"Value {row['value']} is outside device unit range {row['unit_range']} for {row['variable']} at time {row['time']} at dataframe index {index}."
                )

                # Append the row index to the list
                rows__out_of_unit_range.append(index)

            if not is_value_within_range(row["value"], row["safety_range"]):
                print(
                    f"Value {row['value']} is outside device safety range {row['safety_range']} for {row['variable']} at time {row['time']} at dataframe index {index}."
                )

                # Append the row index to the list
                rows__out_of_safety_range.append(index)

        # Raise ValueError after printing all relevant information
        if rows__out_of_unit_range or rows__out_of_safety_range:
            raise ValueError(
                f"Values outside the unit range: {rows__out_of_unit_range}!\n Values outside the safety range: {rows__out_of_safety_range}! \n\nPlease update these before proceeding."
            )
    return timeline


def sanitize__drop_duplicates(timeline):
    """
    Drop duplicate rows and drop rows where the variable and time are duplicated.
    """
    return funcy.compose(
        WTframe.drop_duplicates,
        lambda timeline: WTframe.drop_duplicates(timeline, subset=["variable", "time"]),
    )(timeline)


def sanitize__round_value(timeline, num_decimal_places=6):
    """
    Rounds the 'value' column to the given number of decimal places and returns the updated timeline.
    """
    df = deepcopy(timeline)
    df["value"] = df["value"].round(num_decimal_places)
    return df


def sanitize(timeline):
    """
    Check for duplicate, range and type errors in the current dataframe and either return an updated dataframe or an error.

    `sanitize__round_value` is not by default because this might be unexpected by the user.
    """

    return funcy.compose(
        sanitize__drop_duplicates,
        sanitize_values,
        lambda df: WTframe.cast(
            df,
            {
                "variable": str,
                "time": float,
                "value": float,
                # "context": str, # Currently, context can sometimes be None - this should be questioned though
            },
        ),
    )(timeline)


def time_from_anchor_to_context(timeline, t=None, anchorToContext=None):
    if anchorToContext is not None:
        s = timeline.loc[
            (timeline["variable"] == "Anchor")
            & (timeline["context"] == anchorToContext),
            "time",
        ]
        if s.empty and t is None:
            raise ValueError(
                "Anchor in context {} not found, and absolute time is not supplied".format(
                    anchorToContext
                )
            )
        t = (s.max() if not s.empty else 0.0) + (t if t is not None else 0.0)

    return t
