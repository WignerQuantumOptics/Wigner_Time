# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later


"""
The choice made here is to model our ADwin connections as little more than tables of data (DataFrames). This allows for the least amount of coupling with other implementations an convenience of interaction with timelines etc.

What follows are simply convenience functions to make the creation easier.
"""
from copy import deepcopy
import pandas as pd
import numpy as np

from wignertime.internal import dataframe as wt_frame
from wignertime import config as wt_config
import wignertime.variable as variable

# ======================================================================
_SCHEMA = {"variable": str, "module": int, "channel": int}
# ======================================================================


def is_valid_name(timeline):
    return timeline.variable.str.match(wt_config.VARIABLE__REGEX).all()


def _ensure_valid_names(timeline):
    if is_valid_name(timeline):
        return timeline
    else:
        offenders = [v for v in timeline.variable if not variable.is_valid(v)]
        raise ValueError(
            "Connection name(s) {} do not follow the naming convention `<device>_<UID>(__<unit>)` set by `config.VARIABLE__REGEX`.".format(
                offenders
            )
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
        frame = wt_frame.new_schema(np.atleast_2d(variable_module_channel), _SCHEMA)
    except:
        raise ValueError("=== Input to 'connection' not well formatted ===")

    # NOTE: deliberately outside the `try`. A badly shaped table and a badly named
    # variable are different mistakes, and the second one already says which name
    # offends -- information a blanket re-raise would throw away.
    return _ensure_valid_names(frame)


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
