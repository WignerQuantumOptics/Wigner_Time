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

from wigner_time import anchor as wt_anchor
from wigner_time import config as wt_config
from wigner_time import input as wt_input
from wigner_time import ramp_function as wt_ramp_function
from wigner_time.internal import dataframe as wt_frame
from wigner_time.internal import origin as wt_origin

###############################################################################
#                   Constants                                                 #
###############################################################################

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
    return wt_origin.previous(
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
) -> wt_frame.CLASS:
    """
    Does what it says on the tin: establishes a new timeline according to the given (flexible) input collection. If 'timeline' is also specified, then it concatenates the new creation with the existing one.


    Accepts programmatic and manual input.

    TODO:
    - document the possible combinations of arguments ordered according to usecases
    - change from default `t` to default `origin`?

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

    df_rows = wt_frame.new(rows, columns=schema.keys()).astype(schema)
    new = wt_origin.update(df_rows, timeline, origin=origin)

    if timeline is not None:
        if context is None:
            new["context"] = previous(timeline)["context"]

        return wt_frame.concat([timeline, new])

    return new


def update(
    *vtvc,
    timeline: wt_frame.CLASS | None = None,
    t=0.0,
    context=None,
    origin=None,
    origin__default="anchor",
    schema=_SCHEMA,
    **vtvc_dict,
):
    """
    Creates a timeline for a single or many variables, the same as for the `create` function.

    One difference is that when an existing timeline is not specified,
    then it returns an anonymous function for use in function chaining,
    like the other main functions in this module.

    For such chaining, see the `stack` function.

    Like other functions, when `context` is not specified for a given variable, it is taken to be the latest context in the timeline.
    WARNING: In this case, beware of accidentally putting timelines into special contexts.
    """
    if timeline is None:
        return lambda x: update(
            *vtvc,
            timeline=x,
            t=t,
            context=context,
            origin=origin,
            origin__default=origin__default,
            schema=schema,
            **vtvc_dict,
        )

    else:
        # Check if anchor is desired and available
        # TODO: Implement a fallback to 'last', if there's no anchor available
        if (
            (origin is None)
            and (origin__default is not None)
            and wt_anchor.is_available(timeline)
        ):
            origin = origin__default

        if context is None:
            context = previous(timeline)["context"]

        return create(
            *vtvc,
            timeline=timeline,
            t=t,
            context=context,
            origin=origin,
            schema=schema,
            **vtvc_dict,
        )


def anchor(
    t=None,
    timeline=None,
    context=None,
    origin=None,
    origin__default="anchor",
) -> wt_frame.CLASS | Callable:
    """
    Creates a special, non-physical `variable` (doesn't have a matching `connection`), that can be used for time references, particularly within individual `context`s.

    This can be very convenient in the context of `ramp`s, where the starting and ending times are often built around a hypothetical point in time, due to physical switching speeds.

    NB.
    - By default, the `origin` of `anchor` is `'anchor'` when available; `None` otherwise. This is for convenience.
    - Anchors are automatically numbered, for 'global' referencing, but these numbers are not necessary in normal use.
    """
    # NOTE: Makes use of a global variable (LABEL__ANCHOR).

    if timeline is None:
        return lambda tline: anchor(
            timeline=tline,
            t=t,
            context=context,
            origin=origin,
        )

    num_anchors = timeline["variable"].loc[wt_anchor.mask(timeline)].nunique()

    # Check if anchor origin is desired and available
    if (
        (origin is None)
        and (origin__default is not None)
        and wt_anchor.is_available(timeline)
    ):
        origin = origin__default

    return update(
        "{}__{:03d}".format(wt_config.LABEL__ANCHOR, num_anchors + 1),
        0,
        timeline=timeline,
        t=t,
        context=context,
        origin=origin,
    )


def ramp(
    timeline=None,
    duration=None,
    t1=None,
    context=None,
    origins=[["anchor", "variable"], ["variable"]],
    schema=_SCHEMA,
    function=wt_ramp_function.tanh,
    **vtvc_dict,
) -> wt_frame.CLASS | Callable:
    # TODO: Decide on arguments
    # - t = [0.0, 2.0]
    # - origins = [[,], [,]]
    #
    # - t1 = 0.0; duration=2.0
    # - t1 = 0.0; t2=2.0
    # - origin1=...;origin2=...
    #
    """
    Convenient ways of defining pairs of points and a function!

    A `ramp` defines ranges of values for each variable across time from a beginning time-value pair to an ending time-value pair. Primarily, for the sake of switching analogue devices on and off in a controllable way. Although a `ramp` can be as simple as a linear `value` progression from start to end, the default function for a `timeline` is hyperbolic tan. This allows the user to soften the value gradient at the beginning and end of the function.

    `ramp` has a slightly different interface to `create` and `update`. `**vtvc_dict` follows that of `create`, but it is assumed that `*vtvc` is not necessary, as if you wanted to specify the points manually (in big lists), you should use `create` or `update`. Also, ramps are defined in terms of the groups of points needed for the accompanying function. Usually, this will be starting and ending points. Supplying a different number of points will result in an error.

    *Examples of calling ramp*
    Normally, it will look something like
    `
    tl.stack(
        timeline,
        tl.ramp(
            coil_compensationX__A=0.0,
            coil_compensationY__A=0.0,
            coil_MOTlowerPlus__A=0.0,
            coil_MOTupperPlus__A=0.0,

            duration=duration,
            context="final_ramps"))
    `
    The variables are given end values independently and other options collectively. By default, the starting time is also inferred from the previous timeline and so chains of operations can be built up conveniently.

    For simpler ramps, it can still be easier, like in `create`, to supply everything in a list, e.g.
    `tl.ramp(lockbox_MOT__MHz=[500e-3,0.0])`
    or
    `tl.ramp(lockbox_MOT__MHz=[500e-3, 0.0, "final_ramps"])` - if you want a new `context`.
    This works because by default the ending time is relative to the starting time (see the `origin` keyword argument), such that 't_end' and 'duration' are the same.

    This will cover the vast majority of use cases, but sometimes there might be a need to control the start of a ramp explicitly, even with respect to the `origin`. This can be done similarly,  e.g.
    `lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]]`,
    but with the condition that the lists are not inhomogenous.
    """
    # TODO:
    # - check for ramps with 0 duration (shouldn't do anything)
    if timeline is None:
        return lambda x: ramp(
            timeline=x,
            duration=duration,
            context=context,
            origins=origins,
            function=function,
            **vtvc_dict,
        )
    else:
        if context is None:
            context = previous(timeline)["context"]

    _vtvcs = {k: np.array(v) for k, v in vtvc_dict.items()}
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
                *[], time=t1, context=context, **_vtvc_2d_0
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
    if t1 is None:
        df__no_start_points.loc[:, ["time", "value"]] = 0.0
    else:
        df__no_start_points.loc[:, "time"] = t1
        df__no_start_points.loc[:, "value"] = 0.0

    new1 = wt_origin.update(
        wt_frame.concat([df_1, df__no_start_points]), timeline, origin=origins[0]
    )
    new1["function"] = function
    new2 = wt_origin.update(df_2, new1, origin=origins[1])
    new2["function"] = function

    # TODO: Should we sort the new timelines before returning them?
    return wt_frame.drop_duplicates(
        wt_frame.concat([timeline, new1, new2]), subset=["variable", "time"]
    )


def stack(firstArgument, *fs: list[Callable]) -> Callable | wt_frame.CLASS:
    # TODO: Alternative names:
    # - sequence
    # - chain
    # - cascade
    # - domino
    # - generate (too similar to `create`: will cocnfuse the user)
    # - abstract
    """
    For chaining modifications to the timeline in a composable way.

    If the bottom of the stack is a timeline, the result is also a timeline
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


def expand(timeline, num__bounds=2, **function_args) -> wt_frame.CLASS:
    """
    Converts the functions marked in the timeline into individual rows, i.e. applies the functions to the given data.

    This is generally a one-way operation and so should only be carried out before the timeline is implemented on a device.

    `num__bounds` refers to the number of points (and so rows) needed to define the ramp function in the first place. Currently, this is implicitly assumed to be two, i.e. that `ramp`s are simply defined by the origin, terminus and expansion function.
    """
    # NOTE: Not implemented for `num__bounds` != 2
    #
    _mask_fs = timeline["function"].notna()
    _dff = timeline[_mask_fs].sort_values(by=['variable','time'])


    # Work out where the ramps start
    _indices_drop = _dff.index
    _inds__start = _dff.iloc[::num__bounds].index

    # Mark the beginning and end points (allowing for the number of points per ramp specification to increase in the future)
    _dff = _dff.reset_index(drop=True)
    _dff["ramp_group"] = _dff.index // num__bounds

    # Fill out the values
    _dfs = []

    # For adding back in the value of other columns, based on the first row, like `context` etc. Written this way to allow for more, unknown columns to continue.
    _columns__keep = _dff.columns.drop(
        ["time", "value", "variable", "function", "ramp_group"]
    )

    print(_dff[['time', 'variable', 'value', 'ramp_group']])
    print("got to groups")
    for _, _group in _dff.groupby("ramp_group"):
        _pt_start, _pt_end = _group[["time", "value"]].values
        print(_pt_start, _pt_end)

        # Apply the ramp function
        _dfs.append(
            create(
                [
                    _group["variable"].tolist()[0],
                    _group["function"].tolist()[0](_pt_start, _pt_end, **function_args),
                ],
            ).assign(**_group.iloc[0][_columns__keep].to_dict())
        )

    timeline.drop(index=_indices_drop, inplace=True)
    timeline.drop(columns=["function"], inplace=True)

    print(len(_indices_drop))
    print(len(_dfs))
    print(len(_inds__start))

    # Add the values back into the main timeline
    return wt_frame.insert_dataframes(timeline, _inds__start, _dfs)


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
