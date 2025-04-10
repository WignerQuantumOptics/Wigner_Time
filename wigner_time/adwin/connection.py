# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)


"""
The choice made here is to model our ADwin connections as little more than tables of data (DataFrames). This allows for the least amount of coupling with other implementations an convenience of interaction with timelines etc.

What follows are simply convenience functions to make the creation easier.
"""
from copy import deepcopy
import pandas as pd
import numpy as np

from wigner_time.internal import dataframe as wt_frame
import wigner_time.variable as variable

# ======================================================================
_SCHEMA = {"variable": str, "module": int, "channel": int}
# ======================================================================


def is_valid_name(timeline):
    return timeline.variable.str.match(variable.REGEX).all()


def _ensure_valid_names(timeline):
    if is_valid_name(timeline):
        return timeline
    else:
        raise ValueError(
            "Connection name is not valid. Connection names should follow the REGEX specified in the `variable` module."
        )


def new(*variable_module_channel) -> pd.DataFrame:
    """
    Convenience for creating a table with 'variable', 'module' and 'channel' columns.

    'variable's have the form 'context_equipment__unit' or 'context_equipment'. In the latter case, the 'variable' is taken to be digital (unitless).

    vmcs:
    e.g.
        "AOM_MOT__V", 1, 1
    or
        ["shutter_MOT", 1, 11],
        ["shutter_repump", 1, 12],
        ["shutter_imaging", 1, 13],
    """

    try:
        return _ensure_valid_names(
            wt_frame.new_schema(np.atleast_2d(variable_module_channel), _SCHEMA)
        )
    except:
        raise ValueError("=== Input to 'connection' not well formatted ===")


def remove_unconnected_variables(timeline, connections):
    """
    Purges the given timeline of any `variable`s that do not have a matching `connection`.

    NOTE: Assumes timeline and connections are both pd.DataFrame-like things
    """
    timeline = deepcopy(timeline)
    _disconnections = [
        v
        for v in timeline["variable"].unique()
        if v not in connections["variable"].unique()
    ]

    for v in _disconnections:
        timeline.drop(timeline[timeline.variable == v].index, inplace=True)

    return timeline
