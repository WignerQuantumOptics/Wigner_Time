# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later


"""
The choice made here is to model our ADwin connections as little more than tables of data (DataFrames). This allows for the least amount of coupling with other implementations an convenience of interaction with timelines etc.

What follows are simply convenience functions to make the creation easier.
"""
from copy import deepcopy

import numpy as np
import pandas as pd

import wignertime.variable as variable
from wignertime import config as wt_config
from wignertime.internal import dataframe as wt_frame

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
            "Connection name(s) {} do not follow the naming convention `<device>__<UID>(__<unit>)` set by `config.VARIABLE__REGEX`.".format(
                offenders
            )
        )


def new(*variable_module_channel) -> pd.DataFrame:
    """
    Convenience for creating a table with 'variable', 'module' and 'channel' columns.

    'variable's have the form 'context_equipment__unit' or 'context_equipment'. In the latter case, the 'variable' is taken to be digital (unitless).

    vmcs:
    e.g.
        "AOM__MOT__V", 1, 1
    or
        ["shutter__MOT", 1, 11],
        ["shutter__repump", 1, 12],
        ["shutter__imaging", 1, 13],
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
    Removes the anchors from `timeline`, and refuses any other variable that has no
    `connection` (A24).

    An anchor is a time reference, not an output: it has no connection by design, and its
    name begins with `config.LABEL__ANCHOR`, as `timeline.anchor` names it. Every other
    variable is meant for an output. One without a connection used to be removed too,
    without a word, so a misspelled name, a channel the apparatus lacks, or a name a port of
    old code missed vanished from the arrays while the timeline still showed it. That is
    the silent kind of failure, so such a variable is now refused, with every one named.

    NOTE: Assumes timeline and connections are both pd.DataFrame-like things
    """
    timeline = deepcopy(timeline)
    connected = set(connections["variable"])
    unconnected = [v for v in timeline["variable"].unique() if v not in connected]
    anchors = [v for v in unconnected if v.startswith(wt_config.LABEL__ANCHOR)]
    outputs = sorted(set(unconnected) - set(anchors))

    if outputs:
        raise ValueError(
            "Variable(s) {} have no connection, so they cannot reach an output, and would"
            " vanish from what the machine plays. Add a connection for each, correct the"
            " name, or remove its rows. (An anchor, which has no connection by design, is a"
            " name beginning with {!r}.)".format(outputs, wt_config.LABEL__ANCHOR)
        )

    return timeline[~timeline["variable"].isin(anchors)]
