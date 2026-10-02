# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The bodies of `update`, `anchor` and `ramp` once applied to a timeline, and the row
construction they share. Private to `timeline.build`.
"""


import numpy as np

from wignertime import config as wt_config
from wignertime.timeline import ramp_function as wt_ramp_function
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import tags as wt_tags
from wignertime.internal import util as wt_util
from wignertime.timeline.internal import anchor as wt_anchor
from wignertime.timeline.internal import inherit
from wignertime.timeline.internal import input as wt_input
from wignertime.timeline.internal import origin as wt_origin
from wignertime.timeline.internal import checks as wt_checks


SCHEMA = {"time": float, "variable": str, "value": float, "context": str}
"""These column names are assumed to exist and are used in core functions. Be careful about editing them."""


def given(timeline, name):
    """The timeline a stage is applied to, checked (`util.ensure_timeline`)."""
    if timeline is None:
        raise TypeError(
            "`{}` needs a timeline and was given none. A stage is applied to one by"
            " `to_timeline`.".format(name)
        )
    return wt_util.ensure_timeline(timeline, name, columns__required=SCHEMA)


def empty():
    """A timeline with no rows: what a stage is applied to when nothing precedes it."""
    return wt_frame.cast(wt_frame.new([], columns=SCHEMA.keys()), SCHEMA)


def populate_timeline(
    *vtvc,
    timeline: wt_frame.CLASS | None = None,
    time=0.0,
    context=None,
    origin=None,
    schema=SCHEMA,
    **vtvc_dict,
) -> wt_frame.CLASS:
    """
    The body of `update`, and the constructor `expand` rebuilds a ramp's rows with.
    **Internal.**

    Resolves the flexible `*vtvc` / `**vtvc_dict` input into rows, places them with
    respect to `origin`, and — when a `timeline` is given — inherits its context and
    concatenates.

    The input grammar is documented on `update`, which publishes it through mkdocstrings;
    only the keyword forms are public. The positional forms are reachable only from here,
    where rows are assembled rather than named.

    `context` and `origin` are taken here already resolved: `update` reads the public
    default, `wt_tags.INFER`, as `None` before calling this (see `inherit.resolve` and
    `origin.auto`).
    """
    rows = wt_input.rows_from_arguments(*vtvc, time=time, context=context, **vtvc_dict)

    df_rows = wt_frame.new(rows, columns=schema.keys())

    # A value that is neither a number nor convertible to one reaches `astype` and fails
    # there as `TypeError: float() argument must be a string or a real number, not
    # 'dict'` -- from inside pandas, naming neither the variable nor the call. One
    # vectorised check instead, before the cast (C5).
    values = wt_frame.column(df_rows, "value")
    values__bad = wt_frame.not_numeric(values)
    if values__bad.any():
        raise ValueError(
            "Not a numeric value for {}: {}. A variable's value must be a number.".format(
                sorted(set(wt_frame.column(df_rows, "variable")[values__bad])),
                sorted(set(map(repr, values[values__bad]))),
            )
        )

    df_rows = wt_frame.cast(df_rows, schema)
    new = wt_origin.update(df_rows, timeline, origin=origin)

    if timeline is not None:
        new = inherit.context(new, timeline, context=context)
        return wt_frame.concat([timeline, inherit.require(new)])

    return inherit.require(new)


def update(timeline, time, context, origin, **vtvc_dict):
    """`update`, applied."""
    timeline = given(timeline, "update")
    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS
    )
    return populate_timeline(
        timeline=timeline,
        time=time,
        context=inherit.resolve(context),
        origin=origin,
        **vtvc_dict,
    )


def anchor(timeline, time, context, origin):
    """`anchor`, applied."""
    timeline = given(timeline, "anchor")
    num_anchors = len(
        set(wt_frame.column(timeline, "variable")[wt_anchor.mask(timeline)])
    )

    # `origin` and `context` are passed through unresolved: `update` resolves both, with
    # the same defaults `anchor` would use.
    return update(
        timeline,
        time=time,
        context=context,
        origin=origin,
        **{"{}__{:03d}".format(wt_tags.LABEL__ANCHOR, num_anchors + 1): 0},
    )


def ramp(
    timeline, duration, time, time2, context, origin, origin2, function, **vtvc_dict
):
    """`ramp`, applied."""
    timeline = given(timeline, "ramp")

    context = inherit.resolve(context)
    wt_checks.refuse_value_origin(origin)

    # A ramp always starts where its variable is (#142, 2026-09-29). A start value that
    # differs from the current one is a step hidden inside a ramp -- the discontinuity a
    # ramp exists to avoid -- so a jump that is wanted is an `update` before the ramp,
    # where it shows in the table. The 2-D form, which stated a start, is therefore gone,
    # and every start is inferred: the end rows' variables, placed at `time` from the
    # origin, at the value each has there.
    points__required = wt_ramp_function.points(function)
    if points__required != 2:
        raise ValueError(
            "\n".join(
                [
                    "{} is made of {} points, and a ramp of two: its start, where the"
                    " variable is, and its end.".format(
                        getattr(function, "__name__", repr(function)), points__required
                    ),
                    "",
                    "Interior points belong to the function: bind them as its"
                    " parameters, as a ramp's own resolution is bound.",
                ]
            )
        )

    written = sorted(k for k, v in vtvc_dict.items() if np.array(v).ndim >= 2)
    if written:
        raise ValueError(
            "\n".join(
                [
                    "A ramp starts where its variable is (#142), so its start is not"
                    " written: {}.".format(", ".join(written)),
                    "",
                    "Give the end only -- `v=target`, or `v=[time, target]` -- and `time`"
                    " for when the ramp starts. To start from another value, `update`"
                    " the variable first, so that the jump shows in the table:",
                    "",
                    "    stack(update(coil__A=1.0), ramp(coil__A=3.0, duration=0.1))",
                ]
            )
        )

    if time2 is None and duration is not None:
        time2 = duration

    df_2 = wt_frame.cast(
        wt_frame.new(
            wt_input.rows_from_arguments(*[], time=time2, context=context, **vtvc_dict),
            columns=SCHEMA.keys(),
        ),
        SCHEMA,
    )

    # A new frame, not a view: these rows have their time and value overwritten to make
    # start points out of them, and writing through would zero the very end values the
    # ramp is aiming at (B4/#111). The cast keeps `time` a float when given an int.
    df_1 = wt_frame.cast(
        wt_frame.with_column(
            wt_frame.with_column(df_2, "time", 0.0 if time is None else time),
            "value",
            0.0,
        ),
        SCHEMA,
    )

    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS__RAMP
    )
    new1 = wt_frame.with_column(
        wt_origin.update(df_1, timeline, origin=origin), "function", function
    )
    new1 = inherit.context(new1, timeline, context=context)
    inherit.require(new1)

    new2 = wt_frame.with_column(
        wt_origin.update(df_2, new1, origin=origin2), "function", function
    )
    new2 = wt_frame.with_column(new2, "context", wt_frame.column(new1, "context"))

    # `new1` is a copy of `df_2`, so the two frames hold the same variables in the same
    # order. They used to be built from different dictionaries, one per input form, and
    # subtracting them positionally compared one variable's boundary against another's
    # whenever the forms were mixed in one call (B1/#108); with one form there is nothing
    # to mix, and the alignment below only states what holds by construction.
    variables = wt_frame.column(new1, "variable")
    times__start = wt_frame.column(new1, "time", dtype=float)
    new2__aligned = wt_frame.align_to(new2, variables)
    times__end = wt_frame.column(new2__aligned, "time", dtype=float)

    # A ramp runs between two instants, and ±∞ is before or after the run (#154). Unlike
    # the degeneracies below, which are about the interval, this is about the ends.
    ends = np.concatenate([times__start, times__end])
    if not np.isfinite(ends).all():
        raise ValueError(
            "A ramp runs between two instants, and ±∞ is before or after the run, not an"
            " instant (#154). Check `time`, `time2` and `duration`: {}.".format(
                ", ".join(sorted(set(variables)))
            )
        )

    # A ramp has two degeneracies and they are not the same thing. The mask here used to
    # conflate them, compute cleaned frames, discard them, and then either drop the whole
    # ramp silently or keep every degenerate row (A3). Settled by the maintainer,
    # 2026-09-18:
    #
    # - A zero **duration** has no sensible expansion, since both boundaries occupy one
    #   instant, and is almost always a slip in the caller's arithmetic -- a `duration`
    #   that came out of a subtraction as 0. It raises, naming the variables.
    #
    # - A **negative** duration is the same error with a sign, and was the worse of the
    #   two while it went unchecked. `expand` sorts each ramp's boundaries by time, so a
    #   backwards ramp had its endpoints silently *swapped*: `ramp(c__A=9.0,
    #   duration=-1.0)` left the variable at its old value, not at 9.0, and placed the
    #   transition a second in the past, on top of whatever preceded it. It raises too.
    #
    # - A zero **value change** is a hold. It occupies time, so discarding it silently
    #   shortens the timeline and pulls everything after it forward. It is kept and
    #   expanded. The identical rows that produces are removed again by
    #   `adwin.validate.drop_repeats` before the hardware, which keeps the first and last
    #   row of each channel -- so the redundancy is paid for in the device-layer table
    #   only, and that table is the thing the user is meant to be able to read.
    TOL = 1e-15
    duration__actual = times__end - times__start
    time__degenerate = np.abs(duration__actual) < TOL
    time__reversed = duration__actual < -TOL

    if time__degenerate.any() or time__reversed.any():
        raise ValueError(
            "\n".join(
                [
                    "A ramp must end after it begins.",
                    "",
                    "  zero duration : {}".format(
                        sorted(set(variables[time__degenerate])) or "none"
                    ),
                    "  ends earlier  : {}".format(
                        sorted(set(variables[time__reversed])) or "none"
                    ),
                    "",
                    "Check `duration` (or `time2`) -- a duration computed as a difference"
                    " of two stage times is the usual way this comes out wrong. To"
                    " command a value at a single instant, use `update`.",
                ]
            )
        )

    # A variable is in at most one ramp at a time (#157). A ramp starts where its
    # variable is, and during another ramp that value is not in the table: a ramp holds
    # rows for its boundaries only, so a second one starting half-way through the first
    # took the first one's *start* value, and `expand`, pairing the boundaries in time
    # order, then rebuilt both from the wrong ones -- measured, a coil held at 0 A and
    # jumped to 10 A. One ramp starting exactly as another ends is the ordinary sequence
    # and is kept.
    #
    # The comparison is exact, with no tolerance for rounding, and deliberately so. Two
    # ramps placed by different sums can meet 4e-17 s apart -- `0.1 + 0.2` against
    # `0.3` -- and when the second then starts that little *before* the first ends, its
    # start value is looked up at an instant the first one's end row does not yet
    # precede. A tolerance here would let that ramp start from the wrong value; refusing
    # it says that which comes first is a matter of rounding.
    overlaps = [
        (variable, float(start), float(end), (float(before[0]), float(before[1])))
        for variable, start, end in zip(variables, times__start, times__end)
        for before in intervals__ramp(timeline, variable)
        if start < before[1] and before[0] < end
    ]
    if overlaps:
        by_rounding = any(min(e, b[1]) - max(s, b[0]) < 1e-9 for _, s, e, b in overlaps)
        raise ValueError(
            "\n".join(
                [
                    "A variable is in at most one ramp at a time (#157):",
                    "",
                    *[
                        "  {}: this ramp, {!r}..{!r} s, overlaps its ramp over"
                        " {!r}..{!r} s".format(v, s, e, b[0], b[1])
                        for v, s, e, b in overlaps
                    ],
                    "",
                    "A ramp starts where its variable is, and during another ramp that"
                    " value is not in the table. Start this ramp when the other ends,"
                    " or end the other earlier.",
                    *(
                        [
                            "",
                            "Here the two only touch, to within rounding: their times"
                            " were reached by different sums. Place this ramp from the"
                            " other's end -- `origin=\"last\"`, or its stage's anchor --"
                            " rather than by arithmetic in absolute time.",
                        ]
                        if by_rounding
                        else []
                    ),
                ]
            )
        )

    # NOTE: Don't drop duplicates until after the expansion. Currently, this messes things up.
    return wt_frame.concat([timeline, new1, new2])


def intervals__ramp(timeline, variable):
    """
    The intervals over which `variable` already ramps in `timeline`, as `(start, end)`.

    Read from the ramp rows, which carry their `function`: each ramp is as many rows as
    its function is made of (`ramp_function.points`), in time order -- which is how
    `expand` pairs them, and valid for exactly as long as no two ramps of one variable
    overlap.
    """
    if not wt_frame.has_columns(timeline, ["function"]):
        return []

    rows = wt_frame.sort(
        wt_frame.filter(
            timeline,
            (wt_frame.column(timeline, "variable") == variable)
            & ~wt_frame.isnull(wt_frame.column(timeline, "function")),
        ),
        "time",
    )
    times = wt_frame.column(rows, "time").tolist()
    functions = wt_frame.column(rows, "function").tolist()

    out, i = [], 0
    while i < len(times):
        chunk = times[i : i + wt_ramp_function.points(functions[i])]
        out.append((chunk[0], chunk[-1]))
        i += len(chunk)
    return out
