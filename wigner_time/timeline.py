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
import numpy as np

from wigner_time import input as wt_input
from wigner_time import ramp_function as wt_ramp_function
from wigner_time.internal import dataframe as wt_frame, origin
from wigner_time.internal import origin as wt_origin

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
    timeline: wt_frame.CLASS,
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
    return origin.previous(
        timeline=timeline,
        variable=variable,
        column=column,
        sort_by=sort_by,
        index=index,
    )


###############################################################################
#                   Main functions
###############################################################################
def create(
    *vtvc,
    timeline: wt_frame.CLASS | None = None,
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

    rows = wt_input.rows_from_arguments(*vtvc, time=t, context=context, **vtvc_dict)

    # DEPRECATED: Removing context column
    # If there are no errors here for a while then we can just remove the 'popping' code below.
    # if (len(rows[0]) != 4) and (context is None):
    #     schema.pop("context")

    df_rows = wt_frame.new(rows, columns=schema.keys()).astype(schema)
    new = wt_origin.update(df_rows, timeline, origin=origin)

    if timeline is not None:
        if context is None:
            new["context"] = previous(timeline)["context"]

        return wt_frame.concat([timeline, new])

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
    # TODO: Pass on origin argument
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
            **vtvc_dict,
        )


def anchor(t, timeline=None, relativeTime=True, context=None):
    """
    Sets the anchor, optionally relative to the previous anchor
    """
    # TODO: Anchors should be automatically numbered?
    # Making them uniquely identifiable would be good for debugging.
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
    timeline=None,
    duration=None,
    context=None,
    origins=[["ANCHOR", "variable"], ["variable"]],
    schema=_SCHEMA,
    function=wt_ramp_function.tanh,
    fargs={},
    is_compact=True,
    **vtvc_dict,
):
    """
    Convenient ways of defining two points and a function!

    Take care with the differences from the `create` function. Ramps are naturally defined relative to other starting points and so the interface is slightly different.

    It is assumed that `*vtvc` is not necessary, as if you wanted to specify the points manually (in a big list), you should just use `create` or `update`.

    `**vtvc_dict` follows that of 'create', but with the difference that it can be used to specify only one or two points (this may be extended in the future to allow for more complicated ramps). The default behaviour is simply to provide a [variable, value] pair and this will be taken to define the end point of the ramp. In many circumstances, e.g. as outlined in `demonstration.py`, this and the collective definition of the ramp duration is enough to define the ramp.
    """
    # TODO:
    # - check for ramps with 0 duration (shouldn't do anything)
    # - Limit data to two points per variable
    # - Let origin be a pair of pairs?
    # - Should fargs be a dictionary?
    # - Maybe not. List (with the option of a dictionary) would be most flexible.
    # - Making it a dictionary maximizes the readability though.
    if timeline is None:
        return lambda x: ramp(
            timeline=x,
            duration=duration,
            context=context,
            origins=origins,
            function=function,
            fargs=fargs,
            **vtvc_dict,
        )
    else:
        if context is None:
            context = previous(timeline)["context"]

    # Check vtvc for two separate points
    _vtvcs = {k: np.asarray(v) for k, v in vtvc_dict.items()}
    max_ndim = np.array([a.ndim for a in _vtvcs.values()]).flatten().max()

    match max_ndim:
        case 0 | 1:
            rows1 = None
            rows2 = wt_input.rows_from_arguments(
                *[], time=duration, context=context, **vtvc_dict
            )

        case 2:
            _vtvc_1d = {k: v for k, v in _vtvcs.items() if v.ndim != 2}
            _vtvc_2d_0 = {k: v[0] for k, v in _vtvcs.items() if v.ndim == 2}
            _vtvc_2d_1 = {k: v[1] for k, v in _vtvcs.items() if v.ndim == 2}

            rows1 = wt_input.rows_from_arguments(
                *[], time=duration, context=context, **_vtvc_2d_0
            )
            rows2 = wt_input.rows_from_arguments(
                *[], time=duration, context=context, **(_vtvc_1d | _vtvc_2d_1)
            )

        case _:
            raise ValueError(
                "Unsupported input to the `ramp` function. Only one or two tuples can be processed per variable."
            )

    # Prepare the starting points and then basically do two (shorcut-ed) `create`s. One depending on the previous timeline and one depending on the previous `create`.

    df_1 = wt_frame.new(rows1, columns=schema.keys()).astype(schema)
    df_2 = wt_frame.new(rows2, columns=schema.keys()).astype(schema)

    df__no_start_points = df_2[~df_2["variable"].isin(df_1["variable"])]
    df__no_start_points.loc[:, ["time", "value"]] = 0.0

    new1 = wt_origin.update(
        wt_frame.concat([df_1, df__no_start_points]), timeline, origin=origins[0]
    )
    new1["function"] = function
    new2 = wt_origin.update(df_2, new1, origin=origins[1])
    new2["function"] = function

    # TODO: Should we sort the new timelines before returning them?

    if is_compact:
        return wt_frame.drop_duplicates(
            wt_frame.concat([timeline, new1, new2]), subset=["variable", "time"]
        )
    else:
        raise ValueError("Non-compact ramps are not currently implemented.")

    # frames = []

    #         frames.append(
    #             create(
    #                 variable,
    #                 function(
    #                     point_start,
    #                     wt_ramp_function.to_point_end(
    #                         point_start,
    #                         t,
    #                         value,
    #                         relative=list(relative.values()),
    #                     ),
    #                     **fargs,
    #                 ),
    #                 context=context,
    #             )
    #         )

    # return wt_frame.concat([timeline] + frames)


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
    if isinstance(firstArgument, wt_frame.CLASS):
        return funcy.compose(*fs[::-1])(firstArgument)
    else:
        return funcy.compose(*fs[::-1], firstArgument)


def expand_ramps(timeline, function_args=None):
    """
    Filters the timeline for pairs of rows that depend on a function, creates the necessary ramps, and concats the resulting dfs back into the existing timeline.
    """
    # TODO: Should this be expanded to deal with other types of functions or does it make sense for each compression to define it's own expansion?
    mask_fs = timeline["function"].notna()
    dff = timeline[mask_fs]

    indices_drop = dff.index
    dff = dff.reset_index(drop=True)
    dff["ramp_group"] = dff.index // 2

    columns__keep = dff.columns.drop(["function", "ramp_group"])

    print(indices_drop)
    dfs = []
    for _, group in dff.groupby("ramp_group"):
        pt_start, pt_end = group[["time", "value"]].values
        dfs.append(
            create(
                [
                    group["variable"][0],
                    group["function"][0](pt_start, pt_end, time_resolution=0.2),
                ],
            ).add(group.iloc[0][columns__keep])
        )
    return dfs


def is_value_within_range(value, unit_range):
    # TODO: Shouldn't be here - internal function
    if wt_frame.isnull(unit_range):
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


def sanitize__drop_duplicates(timeline, subset=["variable", "time"]):
    """
    Drop duplicate rows and drop rows where the variable and time are duplicated.
    """
    return wt_frame.drop_duplicates(timeline, subset=subset)


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
    # TODO: Add check for negative times in the 'final' databases.

    return funcy.compose(
        sanitize__drop_duplicates,
        sanitize_values,
        lambda df: wt_frame.cast(
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
