# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

from copy import deepcopy

from wignertime.internal import origin as wt_origin


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
