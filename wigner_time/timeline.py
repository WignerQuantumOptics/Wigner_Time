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

from wigner_time import config as wt_config
from wigner_time import input as wt_input
from wigner_time import ramp_function as wt_ramp_function
from wigner_time.internal import dataframe as wt_frame, origin
from wigner_time.internal import origin as wt_origin

###############################################################################
#                   Constants                                                 #
###############################################################################

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
            schema=schema,
            **vtvc_dict,
        )

    else:
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
) -> wt_frame.CLASS | Callable:
    """
    Creates a special, non-physical `variable` (doesn't have a matching `connection`), that can be used for time references, particularly within individual `context`s.

    This can be very convenient in the context of `ramp`s, where the starting and ending times are often built around a hypothetical point in time, due to physical switching speeds.

    NB. Anchors are automatically numbered, for 'global' referencing, but these numbers are not necessary in normal use.
    """
    # NOTE: Makes use of a global variable (LABEL__ANCHOR).

    if timeline is None:
        return lambda tline: anchor(
            timeline=tline,
            t=t,
            context=context,
            origin=origin,
        )

    print("t: {t}")

    num_anchors = (
        timeline["variable"]
        .loc[timeline["variable"].str.startswith(wt_config.LABEL__ANCHOR)]
        .nunique()
    )

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
    context=None,
    origins=[["anchor", "variable"], ["variable"]],
    schema=_SCHEMA,
    function=wt_ramp_function.tanh,
    fargs={},
    is_compact=True,
    **vtvc_dict,
) -> wt_frame.CLASS | Callable:
    """
    Convenient ways of defining two points and a function!

    Take care with the differences from the `create` function. Ramps are naturally defined relative to other starting points and so the interface is slightly different.

    It is assumed that `*vtvc` is not necessary, as if you wanted to specify the points manually (in a big list), you should just use `create` or `update`.

    `**vtvc_dict` follows that of 'create', but with the difference that it can be used to specify only one or two points (this may be extended in the future to allow for more complicated ramps). The default behaviour is simply to provide a [variable, value] pair and this will be taken to define the end point of the ramp. In many circumstances, e.g. as outlined in `demonstration.py`, this and the collective definition of the ramp duration is enough to define the ramp.
    """
    # TODO:
    # - check for ramps with 0 duration (shouldn't do anything)
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


def stack(firstArgument, *fs: list[Callable]) -> Callable | wt_frame.CLASS:
    # TODO: Alternative names:
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
    `num__bounds` refers to the number of points (and so rows) needed to define the ramp function in the first place. Currently, this is implicitly assumed to be two, i.e. that `ramp`s are simply defined by the origin, terminus and expansion function.
    """
    # TODO: Make these variables 'private'
    _mask_fs = timeline["function"].notna()
    _dff = timeline[_mask_fs]

    # Work out where the ramps start
    _indices_drop = _dff.index
    _inds = np.asarray(_indices_drop)
    _diff = np.diff(_inds)
    _inds__split = np.where(_diff > 1)[0] + 1
    _inds__start = [a[0] for a in np.split(_inds, _inds__split)]

    # Mark the beginning and end points (allowing for the number of points per ramp specification to increase in the future)
    _dff = _dff.reset_index(drop=True)
    _dff["ramp_group"] = _dff.index // num__bounds

    # Fill out the values
    _dfs = []

    # For adding back in the value of other columns, based on the first row, like `context` etc. Written this way to allow for more, unknown columns to continue.
    _columns__keep = _dff.columns.drop(
        ["time", "value", "variable", "function", "ramp_group"]
    )

    for _, _group in _dff.groupby("ramp_group"):
        _pt_start, _pt_end = _group[["time", "value"]].values

        # Apply the ramp function
        _dfs.append(
            create(
                [
                    _group["variable"][0],
                    _group["function"][0](_pt_start, _pt_end, **function_args),
                ],
            ).assign(**_group.iloc[0][_columns__keep].to_dict())
        )

    timeline.drop(index=_indices_drop, inplace=True)
    timeline.drop(columns=["function"], inplace=True)

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
