# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

from copy import deepcopy

from wignertime import config as wt_config
from wignertime.internal import origin as wt_origin


def resolve(context):
    """
    Reads `wt_config.INFER`, the signature default of `context` in the public functions,
    as the `None` that `context` below has always taken to mean "inherit" (#142). It has
    to happen before the rows are built, or the marker itself would land in the
    `context` column.

    `None` and `INFER` therefore mean the same: an unstated row inherits the context of
    the timeline it joins. No inheritance is written `context=""`, which is what an
    unstated row is built with and which `context` leaves alone.
    """
    return None if context is wt_config.CONTEXT__INFER else context


def _mask__no_context(timeline):
    """
    Rows whose context is the empty string, i.e. those that should inherit one.

    `context` is a required column (`timeline._SCHEMA`) and the empty string is its
    minimum value, so there is no case here for a timeline that lacks it -- see #28.
    This used to fall back to "every row" when the column was absent, which promised a
    tolerance the rest of the pipeline did not honour: such a frame raised `KeyError`
    four lines further down.
    """
    return timeline["context"] == ""


def context(
    timeline, timeline__previous, context=None, is_inPlace=True, time__max=None
):
    """
    Updates the context, taken from previous values where unspecified.

    Allows for situations where the new timelines are inserted at earlier times.
    """
    if is_inPlace:
        df = timeline
    else:
        df = deepcopy(timeline)

    if (timeline__previous is not None) and (context is None):
        if time__max == "min":
            time__max = timeline["time"].min()

        df.loc[_mask__no_context(timeline), "context"] = wt_origin.previous(
            timeline__previous, time__max=time__max
        )["context"]
        return df

    elif (timeline__previous is None) and (context is not None):
        df.loc[_mask__no_context(timeline), "context"] = context

    else:
        return timeline
