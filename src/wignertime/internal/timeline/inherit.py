# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

from copy import deepcopy

from wignertime import config as wt_config
from wignertime.internal import origin as wt_origin


def resolve(context):
    """
    Translates the public `context=` sentinel vocabulary into what `context` below
    already understands, at the single point each public function resolves it (A8,
    2026-09-24) -- mirrors `internal.origin.auto_or_off`, which does the same job for
    `origin`.

    `context` defaults to `wt_config.CONTEXT__INFER` at every public entry point
    (`create`, `update`, `anchor`, `ramp`), not `None` -- so a caller who writes
    nothing, or the sentinel explicitly, gets exactly what has always happened:
    unstated rows inherit the previous timeline's context, via this module's
    `context` function's existing `context is None` branch. Translating the sentinel to
    `None` here, rather than leaving `None` doing double duty as both "the default" and
    "an explicit request", is what frees `None` for its own, opposite meaning below.

    A caller who writes `context=None` explicitly asks for the opposite: no
    inheritance at all, every unstated row left at the plain default context, the empty
    string. Translating that request to `""` here -- rather than passing `None`
    through -- is what makes it work with zero changes to `context` itself: `""` is
    already the placeholder `__ensure_time_context` gives an unstated row, and it is
    not `None`, so `context`'s own "infer from previous" branch does not fire for it;
    it falls through to the no-op branch, and the rows already carry `""` from
    construction.

    Anything else -- a real context string -- passes through unchanged, exactly as
    today.
    """
    if context == wt_config.CONTEXT__INFER:
        return None
    if context is None:
        return ""
    return context


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
