# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

from wignertime.internal import dataframe as wt_frame

from wignertime import config as wt_config
from wignertime.internal import origin as wt_origin


def resolve(context):
    """
    Reads `wt_config.INFER`, the signature default of `context` in the public functions,
    as the `None` that `context` below has always taken to mean "inherit" (#142). It has
    to happen before the rows are built, or the marker itself would land in the
    `context` column.

    `None` and `INFER` therefore mean the same: an unstated row inherits the context of
    the timeline it joins.

    There is no way to switch inheritance off. Every row has a context, stated or
    inherited (#156), so `context=""` -- which used to be the spelling of "no
    inheritance", and before that of "no context" (#28) -- is refused here, where it is
    written.
    """
    if isinstance(context, str) and context == "":
        raise ValueError(
            "\n".join(
                [
                    '`context=""` is not a context. Every row has one, stated or'
                    " inherited from the timeline it joins (#156).",
                    "",
                    'Name it -- `context="MOT"` -- or leave `context` out to inherit.',
                ]
            )
        )
    return None if context is wt_config.CONTEXT__INFER else context


def require(rows):
    """
    Refuse rows that, after inheritance, still have no context (#156).

    That happens only where there was nothing to inherit from: the first rows of a
    timeline, or the first at an instant, since the rows at ±∞ pass no context on
    (#154). Refused here rather than left
    as the empty string, because a row without a context does none of the three things a
    context is for (`sec:context`), and the one silent failure recorded in this area,
    #145, produced exactly such rows: the conversion played them at cycle 0 rather than
    in the reserved context they were meant for.
    """
    contexts = wt_frame.column(rows, "context")
    missing = wt_frame.isnull(contexts) | (contexts == "")
    if missing.any():
        raise ValueError(
            "\n".join(
                [
                    "Every row needs a context (#156), and these would have none: {}.".format(
                        ", ".join(
                            sorted(set(wt_frame.column(rows, "variable")[missing]))
                        )
                    ),
                    "",
                    "A context is stated or inherited from the timeline the rows join,"
                    " and here there is nothing to inherit it from: these are the first"
                    " rows, or the first at an instant (rows at ±∞, before or after the"
                    ' run, pass none on). Name it -- `context="MOT"` for the call, or'
                    " `[time, value, context]` for one variable.",
                ]
            )
        )
    return rows


def _mask__no_context(timeline):
    """
    Rows whose context is the empty string, i.e. those that should inherit one.

    The empty string is what a row stating no context is built with, and it survives only
    until inheritance: every row of a timeline has a context (#156), and `require` refuses
    one left without. `context` is a required column (`timeline._SCHEMA`), so there is no
    case here for a timeline that lacks it -- see #28.
    This used to fall back to "every row" when the column was absent, which promised a
    tolerance the rest of the pipeline did not honour: such a frame raised `KeyError`
    four lines further down.
    """
    return wt_frame.column(timeline, "context") == ""


def context(timeline, timeline__previous, context=None, time__max=None):
    """
    `timeline` with the context filled in where it is unspecified: taken from the
    previous rows, or `context` when there are none. A new frame; `timeline` is left alone.

    Allows for situations where the new timelines are inserted at earlier times.
    """
    if (timeline__previous is not None) and (context is None):
        # Inherited from a row at an instant only. The state before the run, at −∞, and
        # the state after it, at +∞, are in contexts a backend may reserve, and inheriting
        # one put rows written after `init` into the initial state, or rows added to a
        # finished timeline into the final one, without a word (#154).
        timeline__previous = wt_origin.instants(timeline__previous)
        if time__max == "min":
            time__max = wt_frame.column(timeline, "time").min()
        if time__max is not None:
            timeline__previous = wt_frame.filter(
                timeline__previous,
                wt_frame.column(timeline__previous, "time") <= time__max,
            )
        if wt_frame.is_empty(timeline__previous):
            # Nothing to inherit from. `require` says so, naming the context -- asking
            # `origin.previous` instead raised a message about the *origin*, whose advice
            # (`origin=0.0`) gave the same error again (#145).
            return timeline

        return wt_frame.with_column(
            timeline,
            "context",
            wt_origin.previous(timeline__previous)["context"],
            where=_mask__no_context(timeline),
        )

    elif (timeline__previous is None) and (context is not None):
        return wt_frame.with_column(
            timeline, "context", context, where=_mask__no_context(timeline)
        )

    else:
        return timeline
