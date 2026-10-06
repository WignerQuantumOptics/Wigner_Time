# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Multiple layers of abstraction:
- operational (time sequence: probe-on, probe-off etc.) – this should go to notebooks / experiment specific packages
- variable (time sequence of independent degrees of freedom: AOM_probe_power 5V)
- ADwin (ADwin-specific details)

It is a goal to be able to go up and down through the layers of abstraction.
"""

from typing import Callable

import numpy as np

from wignertime import config as wt_config
from wignertime import ramp_function as wt_ramp_function
from wignertime.internal.timeline import anchor as wt_anchor
from wignertime.internal.timeline import input as wt_input
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import origin as wt_origin
from wignertime.internal.timeline import inherit


from wignertime.internal import util as wt_util

as_deferred = wt_util.mark_deferred
"""
Mark a user-written function as a deferred timeline function, so that `stack` will
accept it as a constituent. See `stack`.
"""

ANCHOR = wt_config.ANCHOR
"""An origin at the most recent anchor. See `config.Origin`."""

LAST = wt_config.LAST
"""An origin at the latest entry of the timeline. See `config.Origin`."""

VARIABLE = wt_config.VARIABLE
"""An origin at each variable's own most recent entry, in time or value. See `config.Origin`."""

noop = wt_util.mark_deferred(lambda timeline, **kwargs: timeline)
"""
A `stack` constituent that contributes nothing, for the branch of a conditional that
should add no rows.

Not `funcy.identity`: it has to carry the deferred tag, and tagging a shared library
function would mark it for every other user of `funcy`. Taking `**kwargs` also means it
survives a `stack` that forwards keywords -- `identity` did not, and raised
`TypeError: identity() got an unexpected keyword argument 'context'`.
"""


def __getattr__(name):
    """
    Say what replaced a public name that is gone, rather than only that it is missing.

    `create` initialised a timeline, and was the one core function a `stack` could not
    begin with anything but. Since #85 a `stack` composes stages only, and the first rows
    of a timeline are an `update` applied to an empty timeline by `to_timeline`.
    """
    if name == "create":
        raise AttributeError(
            "\n".join(
                [
                    "`create` is gone (#85). The first rows of a timeline are an `update`"
                    " like any other, applied to an empty timeline by `to_timeline`:",
                    "",
                    '    to_timeline(update(AOM__MOT=1, shutter__MOT=0, time=0.0, context="init"))',
                    "",
                    "On an empty timeline the origin is absolute zero, and the rows must"
                    " name their context (#156). In a `stack`, write the `update` itself.",
                ]
            )
        )
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))


###############################################################################
#                   Constants                                                 #
###############################################################################

_SCHEMA = {"time": float, "variable": str, "value": float, "context": str}
"""These column names are assumed to exist and are used in core functions. Be careful about editing them."""

###############################################################################
#                   Utility functions
###############################################################################


def context_info(timeline):
    """
    Useful data (currently 'variables' and 'times') concerning every context. The result is a dictionary, indexed by context.

    e.g. To get the start and end times of the 'MOT' context, call `context_info(timeline)['MOT']['times]`.
    """
    if {"context", "time", "variable"}.issubset(timeline.columns):
        tlg = timeline.groupby("context")
        return {
            k: {
                "variables": tlg["variable"].agg(set).to_dict()[k],
                "times": tlg["time"]
                .agg(["first", "last"])
                .apply(list, axis=1)
                .to_dict()[k],
            }
            for k in tlg.groups.keys()
        }

    else:
        return None


###############################################################################
#                   Main functions
###############################################################################
def _populate_timeline(
    *vtvc,
    timeline: wt_frame.CLASS | None = None,
    time=0.0,
    context=None,
    origin=None,
    schema=_SCHEMA,
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
    default, `wt_config.INFER`, as `None` before calling this (see `inherit.resolve` and
    `origin.auto`).
    """
    rows = wt_input.rows_from_arguments(*vtvc, time=time, context=context, **vtvc_dict)

    df_rows = wt_frame.new(rows, columns=schema.keys())

    # A value that is neither a number nor convertible to one reaches `astype` and fails
    # there as `TypeError: float() argument must be a string or a real number, not
    # 'dict'` -- from inside pandas, naming neither the variable nor the call. One
    # vectorised check instead, before the cast (C5).
    values__bad = wt_frame.not_numeric(df_rows["value"])
    if values__bad.any():
        raise ValueError(
            "Not a numeric value for {}: {}. A variable's value must be a number.".format(
                sorted(set(df_rows.loc[values__bad, "variable"])),
                sorted(set(map(repr, df_rows.loc[values__bad, "value"]))),
            )
        )

    df_rows = df_rows.astype(schema)
    new = wt_origin.update(df_rows, timeline, origin=origin)

    if timeline is not None:
        inherit.context(new, timeline, context=context)
        return wt_frame.concat([timeline, inherit.require(new)])

    return inherit.require(new)


def update(
    *,
    time=0.0,
    context=wt_config.CONTEXT__INFER,
    origin=wt_config.ORIGIN__INFER,
    **vtvc_dict,
) -> Callable:
    """
    Commands variables at instants: the rows of a timeline.

    It returns a stage, for a `stack` and for `to_timeline`. The first rows of a
    timeline are an `update` like any other, applied to an empty timeline::

        initial = to_timeline(update(AOM__MOT=1, shutter__MOT=0, time=0.0, context="init"))

    Input grammar
    -------------
    A variable is named as a keyword, and followed by what it does::

        update(AOM__MOT=<follows>)

    where ``<follows>`` is one of

    ======================================  ==========================================
    ``value``                               at ``time``
    ``[time, value]``
    ``[time, value, context]``
    ``[[time, value], [time, value], ...]``  several instants for one variable
    ======================================  ==========================================

    Several variables are given at once, and a computed set through ``**``::

        update(AOM__MOT=1, shutter__MOT=[0.1, 1, "MOT"])
        update(**{name: value for name, value in ...})

    ``time`` and ``context`` are **defaults, not overrides** — a variable stating its own
    keeps it. The keyword namespace is open by design, so an unrecognised keyword is
    read as a variable name rather than rejected (see the manuscript's `sec:forwarding`);
    that is what makes the injection idiom work, and it is why there is no second,
    positional way in to be confused with it.

    Origin and context
    ------------------
    `origin` defaults to `wt_config.INFER`: the anchor-then-last chain
    (`config.ORIGIN__DEFAULTS`) fills whichever slots are left unstated, so `time` is a
    duration from the end of the preceding stage. `None` means the same. For absolute
    time, write `origin=0.0`. On an empty timeline there is nothing to be relative to,
    and the origin is absolute zero.

    `time=-math.inf` is before the run and `time=math.inf` after it (#154): the initial
    and the final state, in the contexts a backend reserves for them (`ADwin_LowInit`,
    `ADwin_Finish`). Neither is an instant, so nothing is placed relative to them, and
    until something is written at an instant the origin is absolute zero.

    `context` defaults to `wt_config.INFER` too: an unstated row inherits the latest
    context of the timeline it joins, from a row at an instant. `None` means the same.
    Every row has a context (#156): on an empty timeline, or one holding only the state
    before the run, there is nothing to inherit, so the rows must name theirs, and
    `context=""` is refused. A row added to a finished timeline inherits from the last
    stage of the run, not from the final state at +∞.
    """
    _refuse_timeline("update", vtvc_dict)
    inherit.resolve(context)  # refused where it is written, not where it is applied

    return wt_util.stage(
        _update, update, dict(time=time, context=context, origin=origin, **vtvc_dict)
    )


def _update(timeline, time, context, origin, **vtvc_dict):
    """`update`, applied."""
    timeline = _given(timeline, "update")
    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS
    )
    return _populate_timeline(
        timeline=timeline,
        time=time,
        context=inherit.resolve(context),
        origin=origin,
        **vtvc_dict,
    )


def _refuse_timeline(name, vtvc_dict):
    """
    `timeline=` would otherwise land in the open `**vtvc_dict` namespace and be read as a
    variable named `timeline`, whose value is a table -- refused with the mistake named
    rather than as "not a numeric value".
    """
    if "timeline" in vtvc_dict:
        raise TypeError(
            "\n".join(
                [
                    "`{}` takes no timeline (#85). It returns a stage, and"
                    " `to_timeline` applies it:".format(name),
                    "",
                    "    to_timeline({}(...), onto=timeline)".format(name),
                ]
            )
        )


def _refuse_infinite_ends(**times):
    """
    A ramp runs between two instants, and ±∞ is before or after the run (#154). Refused
    where written: applied, a start at −∞ failed on its value lookup instead, as though
    the variable had never been set.
    """
    infinite = sorted(
        k for k, t in times.items() if t is not None and not np.isfinite(t)
    )
    if infinite:
        raise ValueError(
            "A ramp runs between two instants, and ±∞ is before or after the run, not an"
            " instant (#154): {}.".format(
                ", ".join("{}={}".format(k, times[k]) for k in infinite)
            )
        )


def _refuse_value_origin(origin):
    """
    A ramp starts where its variable is (#142), so the value slot of its `origin` has
    nothing to set: only `INFER`, `None` or `VARIABLE`, which all say the same. A value
    written there -- a number, or another variable's name -- is refused rather than
    added to the start, which is what made a stated `1.0` come out as `8.0` (A8).
    """
    if origin is None or origin is wt_config.ORIGIN__INFER:
        return
    value = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))[1]
    if value is None or value is wt_config.ORIGIN__INFER:
        return
    if value is wt_config.VARIABLE:
        return
    raise ValueError(
        "\n".join(
            [
                "A ramp starts where its variable is (#142): the value slot of its"
                " `origin` has nothing to set, and was given {!r}.".format(value),
                "",
                "`origin` places the ramp's start in time. To start from another value,"
                " `update` the variable first, so that the jump shows in the table:",
                "",
                "    stack(update(coil__A=1.0), ramp(coil__A=3.0, duration=0.1))",
            ]
        )
    )


def _given(timeline, name):
    """The timeline a stage is applied to, checked (`util.ensure_timeline`)."""
    if timeline is None:
        raise TypeError(
            "`{}` needs a timeline and was given none. A stage is applied to one by"
            " `to_timeline`.".format(name)
        )
    return wt_util.ensure_timeline(timeline, name, columns__required=_SCHEMA)


def anchor(
    time,
    *,
    context=wt_config.CONTEXT__INFER,
    origin=wt_config.ORIGIN__INFER,
) -> Callable:
    """
    Creates a special, non-physical `variable` (will never have a matching `connection`), that can be used for time references, particularly within individual `context`s.

    This can be very convenient in the context of `ramp`s, where the starting and ending times are often built around a hypothetical point in time, due to physical switching speeds.

    `time` is required. There is no sensible default: it is a displacement from whatever
    the `origin` resolves to, and the two readings a default would have to choose
    between are genuinely different instants (see below).

    *Where the anchor lands*

    By default the `origin` is the most recent anchor where one exists and the last
    entry otherwise, so `time` is normally a duration measured **from the end of the
    preceding stage**. That is what makes stages chain: a stage may write rows past its
    own closing anchor -- `optical_pumping` reinitialises shutters 0.1 s later -- without
    dragging the next stage along with them.

    To mark the end of everything written so far instead, ask for it explicitly:

        anchor(0.0, origin=LAST)       # here, at the last entry in the timeline
        anchor(0.0)                    # here, at the most recent anchor

    The two coincide until some stage writes past its own anchor, and then they do not:
    in the shipped demo they differ by ~0.1 s from `optical_pumping` onwards. Which one
    is meant is therefore worth stating at the call site rather than defaulting.

    NB.
    - Anchors are automatically numbered, for 'global' referencing, but these numbers are not necessary in normal use.
    """
    # NOTE: Makes use of a global variable (LABEL__ANCHOR).

    if time is None:
        raise TypeError(
            "\n".join(
                [
                    "`anchor` requires `time`, a displacement from whatever `origin`"
                    " resolves to.",
                    "",
                    "    anchor(0.0)                    # at the most recent anchor",
                    "    anchor(0.0, origin=LAST)       # at the last entry so far",
                    "    anchor(duration)               # `duration` after the"
                    " preceding stage",
                ]
            )
        )
    if not np.isfinite(time):
        # An anchor marks an instant, and ±∞ is none: it is before or after the run
        # (#154), where nothing can be placed relative to anything.
        raise ValueError(
            "`anchor` was given `time={}`. An anchor marks an instant to place stages"
            " relative to, and ±∞ is before or after the run, not an instant"
            " (#154).".format(time)
        )

    inherit.resolve(context)  # refused where it is written, not where it is applied

    return wt_util.stage(
        _anchor, anchor, dict(time=time, context=context, origin=origin)
    )


def _anchor(timeline, time, context, origin):
    """`anchor`, applied."""
    timeline = _given(timeline, "anchor")
    num_anchors = timeline["variable"].loc[wt_anchor.mask(timeline)].nunique()

    # `origin` and `context` are passed through unresolved: `_update` resolves both, with
    # the same defaults `anchor` would use.
    return _update(
        timeline,
        time=time,
        context=context,
        origin=origin,
        **{"{}__{:03d}".format(wt_config.LABEL__ANCHOR, num_anchors + 1): 0},
    )


def ramp(
    *,
    duration=None,
    time=None,
    time2=None,
    context=wt_config.CONTEXT__INFER,
    origin=wt_config.ORIGIN__INFER,
    origin2=[wt_config.VARIABLE, 0.0],
    function=wt_ramp_function.tanh,
    **vtvc_dict,
) -> Callable:
    """
    Convenient ways of defining pairs of points and a function!

    A `ramp` defines ranges of values for each variable across time from a beginning time-value pair to an ending time-value pair. Primarily, for the sake of switching analogue devices on and off in a controllable way. Although a `ramp` can be as simple as a linear `value` progression from start to end, the default function for a `timeline` is hyperbolic tan. This allows the user to soften the value gradient at the beginning and end of the function.

    `ramp` has a slightly different interface to `update`. `**vtvc_dict` follows that of `update`; to specify the points manually (in big lists), use `update`.

    A ramp is two points and a function between them: its start, which is always where the
    variable is at that instant, and its end, which is written.

    *Examples of calling ramp*
    Normally, it will look something like
    `
    tl.stack(
        tl.ramp(
            coil__compensation_X__A=0.0,
            coil__compensation_Y__A=0.0,
            coil__MOT_lower_plus__A=0.0,
            coil__MOT_upper_plus__A=0.0,

            duration=duration,
            context="final_ramps"))
    `
    The variables are given end values independently and other options collectively. By default, the starting time is also inferred from the previous timeline and so chains of operations can be built up conveniently.

    For simpler ramps, it can still be easier, like in `update`, to supply everything in a list, e.g.
    `tl.ramp(lockbox__MOT__MHz=[500e-3,0.0])`
    or
    `tl.ramp(lockbox__MOT__MHz=[500e-3, 0.0, "final_ramps"])` - if you want a new `context`.
    This works because by default the ending time is relative to the starting time (see the `origin` keyword argument), such that 't_end' and 'duration' are the same.

    **A ramp always starts where its variable is** (#142, 2026-09-29). A start value that
    differs from the current one is a step hidden inside a ramp, the discontinuity a ramp
    exists to avoid. A jump that is wanted is an `update` before the ramp, where it shows
    in the table::

        stack(update(coil__A=1.0), ramp(coil__A=3.0, duration=0.1))

    So a start is never written: the 2-D form that stated one is refused, and so is a
    value in the value slot of `origin`. A variable not yet set has to be set first.
    Nor may a ramp start or end inside another ramp of the same variable (#157).

    `origin` places the start in time. It defaults to `wt_config.INFER`, the
    anchor-then-last chain, and `None` means the same; `origin=0.0` is absolute time, as
    for `update`.

    `context` defaults to `wt_config.INFER`, and `None` means the same: an unstated row
    inherits the latest context of `timeline`. Every row has a context (#156), so
    `context=""` is refused.

    NOTE: `duration` is a human-readable convenience for normal API usage. This is because the temporal origin of the second point is almost always in reference to the first point. Where there is a conflict, `time2` will have supremacy. It is `time2` because `origin2` places the same point, the end.
    """
    _refuse_timeline("ramp", vtvc_dict)
    inherit.resolve(context)  # refused where it is written, not where it is applied
    _refuse_value_origin(origin)
    _refuse_infinite_ends(time=time, time2=time2, duration=duration)

    return wt_util.stage(
        _ramp,
        ramp,
        dict(
            duration=duration,
            time=time,
            time2=time2,
            context=context,
            origin=origin,
            origin2=origin2,
            function=function,
            **vtvc_dict,
        ),
    )


def _ramp(
    timeline, duration, time, time2, context, origin, origin2, function, **vtvc_dict
):
    """`ramp`, applied."""
    timeline = _given(timeline, "ramp")

    context = inherit.resolve(context)
    _refuse_value_origin(origin)

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

    df_2 = wt_frame.new(
        wt_input.rows_from_arguments(*[], time=time2, context=context, **vtvc_dict),
        columns=_SCHEMA.keys(),
    ).astype(_SCHEMA)

    # Copied, not sliced: these rows have their time and value overwritten to make start
    # points out of them, and writing through would zero the very end values the ramp is
    # aiming at (B4/#111; pandas 3 makes copy-on-write unconditional, #88).
    df_1 = df_2.copy()
    df_1.loc[:, "time"] = 0.0 if time is None else time
    df_1.loc[:, "value"] = 0.0

    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS__RAMP
    )
    new1 = wt_origin.update(df_1, timeline, origin=origin)
    new1["function"] = function
    inherit.context(new1, timeline, context=context)
    inherit.require(new1)

    new2 = wt_origin.update(df_2, new1, origin=origin2)
    new2["function"] = function
    new2["context"] = new1["context"]

    # `new1` is a copy of `df_2`, so the two frames hold the same variables in the same
    # order. They used to be built from different dictionaries, one per input form, and
    # subtracting them positionally compared one variable's boundary against another's
    # whenever the forms were mixed in one call (B1/#108); with one form there is nothing
    # to mix, and the alignment below only states what holds by construction.
    new2__aligned = wt_frame.align_to(new2, new1["variable"])

    # A ramp runs between two instants, and ±∞ is before or after the run (#154). Unlike
    # the degeneracies below, which are about the interval, this is about the ends.
    ends = np.concatenate([new1["time"].to_numpy(float), new2["time"].to_numpy(float)])
    if not np.isfinite(ends).all():
        raise ValueError(
            "A ramp runs between two instants, and ±∞ is before or after the run, not an"
            " instant (#154). Check `time`, `time2` and `duration`: {}.".format(
                ", ".join(sorted(set(new1["variable"])))
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
    duration__actual = new2__aligned["time"] - new1["time"]
    time__degenerate = np.abs(duration__actual) < TOL
    time__reversed = duration__actual < -TOL

    if time__degenerate.any() or time__reversed.any():
        raise ValueError(
            "\n".join(
                [
                    "A ramp must end after it begins.",
                    "",
                    "  zero duration : {}".format(
                        sorted(set(new1.loc[time__degenerate, "variable"])) or "none"
                    ),
                    "  ends earlier  : {}".format(
                        sorted(set(new1.loc[time__reversed, "variable"])) or "none"
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
        for variable, start, end in zip(
            new1["variable"], new1["time"], new2__aligned["time"]
        )
        for before in _intervals__ramp(timeline, variable)
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


def _intervals__ramp(timeline, variable):
    """
    The intervals over which `variable` already ramps in `timeline`, as `(start, end)`.

    Read from the ramp rows, which carry their `function`: each ramp is as many rows as
    its function is made of (`ramp_function.points`), in time order -- which is how
    `expand` pairs them, and valid for exactly as long as no two ramps of one variable
    overlap.
    """
    if "function" not in timeline.columns:
        return []

    rows = timeline[
        (timeline["variable"] == variable) & timeline["function"].notna()
    ].sort_values("time", kind="stable")
    times, functions = rows["time"].tolist(), rows["function"].tolist()

    out, i = [], 0
    while i < len(times):
        chunk = times[i : i + wt_ramp_function.points(functions[i])]
        out.append((chunk[0], chunk[-1]))
        i += len(chunk)
    return out


# def stack(firstArgument, *fs: list[Callable]) -> Callable | wt_frame.CLASS:
#     if isinstance(firstArgument, wt_frame.CLASS):
#         return funcy.compose(*fs[::-1])(firstArgument)
#     else:
#         return funcy.compose(*fs[::-1], firstArgument)


def _ensure_stackable(f):
    """
    A `stack` constituent must be a *stage*: a function of a timeline. Not a timeline,
    and not a stage function that has yet to be called.

    A timeline is refused in any position (#85). `stack` composes stages and returns one,
    and `to_timeline` is the one way from a stage to a table. A table used to be accepted
    in front, which made `stack` return a table or a stage depending on its first
    argument, and let a `context` given to the stack skip that table's rows (#145); after
    the front it was accepted here and then failed inside the composition as
    `'DataFrame' object is not callable` (D17's correction).

    The other distinction is invisible to Python: a deferred call, a composed `stack` and
    an uncalled user stage are all plain `function` objects with unhelpfully similar
    signatures. So the deferral machinery tags what it produces, and this checks the tag.
    The mistake it exists for is writing a stage's name where its call belongs --
    `stack(MOT)` for `stack(MOT(...))` -- which would bind the timeline to the stage's
    first parameter, silently.
    """
    if isinstance(f, wt_frame.CLASS):
        raise TypeError(
            "\n".join(
                [
                    "`stack` was given a timeline. It composes stages, and returns one;"
                    " `to_timeline` applies it:",
                    "",
                    "    to_timeline(stack(update(...), ramp(...)), onto=timeline)",
                    "",
                    "`onto` is the timeline the stage starts from, and an empty one when"
                    " it is not given.",
                ]
            )
        )

    if wt_util.is_deferred(f):
        return f

    if callable(f) and wt_util.takes_one_timeline(f):
        # A hand-written `lambda tline: ...` is a legitimate constituent and carries no
        # tag. It is told apart from an uncalled stage by arity: see `takes_one_timeline`.
        return f

    if callable(f):
        name = getattr(f, "__name__", repr(f))
        raise TypeError(
            "\n".join(
                [
                    "`stack` was given the function `{}` itself, rather than the result"
                    " of calling it.".format(name),
                    "",
                    "A constituent must be a stage -- what a core function or a stage"
                    " function returns when called:",
                    "",
                    "    stack({}(...), update(...))".format(name),
                    "",
                    "If `{}` is your own timeline function, mark it with"
                    " `timeline.as_deferred`.".format(name),
                ]
            )
        )

    raise TypeError(
        "`stack` was given {} as a constituent, where a deferred timeline function was"
        " expected.".format(type(f).__name__)
    )


def _empty():
    """A timeline with no rows: what a stage is applied to when nothing precedes it."""
    return wt_frame.new([], columns=_SCHEMA.keys()).astype(_SCHEMA)


def to_timeline(stage: Callable, onto: wt_frame.CLASS | None = None) -> wt_frame.CLASS:
    """
    The one way from a stage to a timeline: `stage` applied to `onto`, or to an empty
    timeline when `onto` is not given.

    A *stage* is what `update`, `ramp`, `anchor`, `stack` and `cascade` return, and what
    a user-defined stage returns: a function of a timeline. So it is written once,
    relative to its own beginning, and can be placed anywhere. A timeline is data -- the
    table that is plotted, archived and converted for the hardware. `to_timeline` is
    where the one becomes the other, and nothing else is::

        timeline = to_timeline(cascade(init, MOT, molasses, finish, MOT_duration=15))

    `onto` is first-class, not a convenience. Building a timeline can be expensive, so a
    parameter scan keeps its base as a table and places each variation onto it::

        base = to_timeline(experiment)
        shots = [to_timeline(imaging(delay), onto=base) for delay in delays]

    `to_timeline(b, onto=to_timeline(a))` is the same table as `to_timeline(stack(a, b))`.

    On an empty timeline there is nothing to be relative to, so the first rows are
    placed in absolute time, and nothing to inherit a context from, so they must name
    theirs (#156).
    """
    if isinstance(stage, wt_frame.CLASS):
        raise TypeError(
            "`to_timeline` was given a timeline, which is one already. To add a stage"
            " to it, pass it as `onto`: `to_timeline(stage, onto=timeline)`."
        )
    _ensure_stackable(stage)

    onto = (
        _empty()
        if onto is None
        else wt_util.ensure_timeline(
            onto, "to_timeline", name__argument="onto", columns__required=_SCHEMA
        )
    )

    out = stage(onto)
    if not isinstance(out, wt_frame.CLASS):
        raise TypeError(
            "A stage must return a timeline, and {} returned {}.".format(
                getattr(stage, "__name__", repr(stage)), type(out).__name__
            )
        )
    return out


def stack(*stages: Callable, **kws) -> Callable:
    """
    Composes stages, in execution order, into one stage::

        stage = stack(update(...), ramp(...), anchor(...))
        timeline = to_timeline(stage, onto=timeline)

    `stack` takes stages only and returns one. To apply it, use `to_timeline`.

    Constituents must **already have been called**: `stack(MOT(duration=15))`, never
    `stack(MOT)`, which raises. This is the opposite of `cascade`, which takes the stage
    functions themselves and calls them with the keywords routed to each.

    Keywords given to `stack` are passed on to its constituents. This is particularly
    convenient for a shared context::

        stack(update(...), ramp(...), anchor(...), context="MOT")

    A forwarded keyword is a **default** for the constituents, not an override: it fills
    what a constituent left unstated and leaves what it stated alone, so
    `stack(update(x=1, context="ADwin_Finish"), anchor(1.0), context="finalRamps")` keeps
    `x` in its reserved context. The same holds between stacks: a stage is itself a
    `stack`, and a keyword given to an outer one reaches the stages inside it, where each
    stack's own keywords, stated closer, take precedence.
    """

    for f in stages:
        _ensure_stackable(f)

    constituents = list(stages)

    keywords__available = _keywords_available(constituents)
    if keywords__available is not None:
        unplaced = sorted(k for k in kws if k not in keywords__available)
        if unplaced:
            raise TypeError(_message__unplaced(unplaced, keywords__available))

    # Where no constituent says what it consumes, a keyword that none of them can even
    # accept would otherwise be dropped below without a word.
    unaccepted = sorted(
        k for k in kws if not any(wt_util.accepts_keyword(f, k) for f in constituents)
    )
    if unaccepted:
        raise TypeError(_message__unplaced(unaccepted, keywords__available or set()))

    # One closure that threads the keywords through, rather than a `funcy.compose` of
    # single-argument wrappers. That composition took the timeline and nothing else, so a
    # keyword forwarded into a nested stack -- every stage is one -- raised a `TypeError`
    # naming a lambda (B10, #136). A constituent that takes no keywords, such as a
    # hand-written `lambda tline: ...`, is given none: the guard above has already made
    # sure that each keyword reaches something that uses it.
    def composed(timeline, **kws__outer):
        kws__all = {**kws__outer, **kws}
        for f in constituents:
            timeline = f(
                timeline,
                **{k: v for k, v in kws__all.items() if wt_util.accepts_keyword(f, k)},
            )
        return timeline

    return wt_util.mark_keywords(
        wt_util.mark_deferred(composed), keywords__available or ()
    )


def _keywords_available(constituents):
    """
    The keywords this stack's constituents can between them consume, or `None` if none of
    them says.

    A constituent that does not record a set is **neutral** -- it neither vouches for a
    keyword nor objects to one. `noop` and a hand-written `lambda tline: ...` are of that
    kind, and treating them as permissive instead would switch the guard off for any
    stack containing one, which the lab's conditional stages make common.
    """
    sets = [
        declared
        for declared in (wt_util.keywords_declared(f) for f in constituents)
        if declared is not None
    ]
    return set().union(*sets) if sets else None


def _message__unplaced(unplaced, keywords__available):
    """
    Say that a forwarded keyword reached no constituent, and why that is not harmless.
    """
    return "\n".join(
        [
            "`stack` could not place {} keyword(s): {}.".format(
                len(unplaced), ", ".join(repr(k) for k in unplaced)
            ),
            "",
            "A keyword given to `stack` is forwarded to every constituent, and the core",
            "functions read an unrecognised keyword as a *variable name*. So an unplaced",
            "keyword does not merely go unused: the parameter you meant to set stays at",
            "its default, and a variable of that name enters the timeline, to be dropped",
            "again without comment at export for having no connection.",
            "",
            "Placeable here: {}.".format(
                ", ".join(sorted(keywords__available)) or "nothing"
            ),
            "",
            "To set a parameter of one stage rather than all of them, call that stage",
            "with it -- `stack(MOT(duration=15))` -- or use `cascade`, which",
            "routes `MOT_duration=15` by prefix.",
        ]
    )


def _route_keyword(key, names__by_length, stages__by_name):
    """
    Resolve one `cascade` keyword to a `(stage name, parameter name)` pair, or to
    `None` with the reason it could not be resolved.

    Matching is anchored to the start of the key and to a `_` boundary, so a parameter
    that merely *contains* a stage name is not captured by it. Candidates are tried
    longest first, because a shorter stage name can be a prefix of a longer one
    (`MOT_` also begins `MOT_detuned_growth_duration`).

    Longest-first alone is not enough to settle the genuine collision, though: if
    `MOT_detuned_growth` does not take the remainder but `MOT` does, the key belongs to
    `MOT`. So a split is accepted only when the target actually takes the parameter --
    or has `**kwargs`, which is how `init` and `finish` stay open for the injection
    idiom of `sec:forwarding`.
    """
    near_misses = []

    for name in names__by_length:
        if not key.startswith(name + "_"):
            continue
        parameter = key[len(name) + 1 :]
        if wt_util.accepts_keyword(stages__by_name[name], parameter):
            return (name, parameter), None
        near_misses.append((name, parameter))

    return None, near_misses


def cascade(*fs: Callable, **kws) -> Callable | wt_frame.CLASS:
    """
    Similarly to `stack`, a convenience that combines an arbitrary chain of functions with an arbitrary selection of associated keywords.

    `kws` are routed to the associated functions by prefixing, e.g. `cascade(MOT, molasses, MOT_duration=1.0)` creates a `stack` of `MOT` and `molasses`, with `duration=1.0` passed into the `MOT` function before evaluation.

    The motivation for this feature is that different experimental contexts should be built modularly, but, at final composition, the user often just wants a single point of contact to add/change nested variables.

    *How this differs from `stack`, which is easy to get wrong*

    `stack` takes stages that have **already been called**; `cascade` takes the stage
    functions **themselves** and calls them::

        stack(MOT(duration=15), molasses())               # called here
        cascade(MOT, molasses, MOT_duration=15)           # called by cascade

    In the first, `MOT(duration=15)` has had every argument but `timeline` supplied, and
    what it returns is a function of the timeline alone -- partial application, not
    currying, since the remaining argument is supplied in one call rather than one at a
    time. `stack` then threads the timeline through that chain.

    In the second, nothing has been called: `cascade` routes `MOT_duration=15` to `MOT`,
    calls it, and hands the results to `stack`. So a stage reaches `cascade` bare and
    reaches `stack` applied, and the two are not interchangeable -- writing
    `stack(MOT)` raises (see `_ensure_stackable`), and `cascade(MOT(...))` fails because
    the result takes no keywords to route.

    *What it returns*

    A stage, like `stack`: `to_timeline(cascade(...))` is the experiment's timeline, and
    a `cascade` is itself stackable, so one beginning mid-experiment composes like any
    other stage.

    Routing is **strict**: a keyword that names no stage, or that names one but is not a
    parameter of it, raises rather than being dropped. The alternative -- letting an
    unrouted keyword broadcast to every stage -- was considered and rejected, because
    every stage would turn it into rows, and into different *kinds* of row depending on
    whether the stage ends in an `update` or a `ramp`.

    Strictness is not configured but derived, from whether the target has `**kwargs`.
    That is only safe because the operation layer confines the open namespace to
    `default_state` and the two functions that wrap it; a stage that collects `**kwargs`
    is, correctly, still permissive here.
    """
    # NOTE: keyed by `__name__`, so a stage appearing twice receives the same keywords
    # both times. That is relied upon; see `KNOWN_ISSUES.md` §C.
    for f in fs:
        _ensure_cascadable(f)

    stages__by_name = {f.__name__: f for f in fs}
    names__by_length = sorted(stages__by_name, key=len, reverse=True)

    args__dict = {}
    unroutable = {}
    for key, value in kws.items():
        routed, near_misses = _route_keyword(key, names__by_length, stages__by_name)
        if routed is None:
            unroutable[key] = near_misses
        else:
            name, parameter = routed
            args__dict.setdefault(name, {})[parameter] = value

    if unroutable:
        raise TypeError(_message__unroutable(unroutable, names__by_length))

    # Apply keywords to function stack
    return stack(*[f(**args__dict.get(f.__name__, {})) for f in fs])


def _ensure_cascadable(f):
    """
    Refuse a `cascade` argument that is not a stage function.

    The mirror of `_ensure_stackable`. `cascade(timeline, MOT)` reads as reasonable and
    used to fail with `AttributeError: 'DataFrame' object has no attribute '__name__'`,
    from the dictionary comprehension that keys stages by name -- naming neither cascade,
    nor the timeline, nor what to write instead.
    """
    if isinstance(f, wt_frame.CLASS):
        raise TypeError(
            "\n".join(
                [
                    "`cascade` was given a timeline. It takes stage functions, calls"
                    " them, and returns a stage; `to_timeline` applies it:",
                    "",
                    "    to_timeline(cascade(MOT, molasses, MOT_duration=15),"
                    " onto=timeline)",
                ]
            )
        )

    if wt_util.is_deferred(f):
        raise TypeError(
            "\n".join(
                [
                    "`cascade` was given a stage that has already been called.",
                    "",
                    "    cascade(MOT, molasses, MOT_duration=15)     # not MOT(...)",
                    "",
                    "`cascade` supplies the arguments itself, by routing its keywords to",
                    "the stage named in each prefix; a stage that has already been",
                    "called has none left to route, and would be keyed under",
                    "`<lambda>`. Use `stack` for stages you have called yourself.",
                ]
            )
        )

    if not callable(f) or not hasattr(f, "__name__"):
        raise TypeError(
            "`cascade` takes named stage functions; {!r} is neither. Keywords are"
            " routed by the stage's `__name__`, so an anonymous callable cannot"
            " receive any.".format(f)
        )


def _message__unroutable(unroutable, names__by_length):
    """
    Say which keywords could not be routed and why, rather than only that some could not.

    A keyword that named a stage but not one of its parameters is the more interesting
    case -- usually a misspelled parameter rather than a misspelled stage -- so it is
    reported against the stage it nearly reached.
    """
    lines = []
    for key, near_misses in unroutable.items():
        if near_misses:
            name, parameter = near_misses[0]
            lines.append(
                "  {} -> `{}` is not a parameter of `{}`".format(key, parameter, name)
            )
        else:
            lines.append("  {} -> matches no stage name".format(key))

    return "\n".join(
        [
            "`cascade` could not route {} keyword(s):".format(len(unroutable)),
            *lines,
            "",
            "Keywords are routed by stage-name prefix, e.g. `MOT_duration=1.0` reaches",
            "`MOT`'s `duration`. The stages given were: {}.".format(
                ", ".join("`{}`".format(n) for n in sorted(names__by_length))
            ),
            "",
            "An unroutable keyword is an error rather than a default, because silently",
            "dropping it would run the stage with its default value -- a physically",
            "different sequence that still executes.",
        ]
    )


def expand(timeline, **function_args) -> wt_frame.CLASS:
    """
    Converts the functions marked in the timeline into individual rows, i.e. applies the functions to the given data.

    This is generally a 'one-way' operation and so should only be carried out before the timeline is implemented on a device.

    It takes a timeline and returns one, and is not a stage (#85, C7 item 6). Unlike
    `update`, `ramp` and `anchor`, which add rows, it transforms the whole timeline it is
    given, so inside a `stack` it expanded every ramp built so far and dropped `function`,
    and the `expand` in `adwin.core.convert` then did nothing.

    **A keyword given to `expand` is a default, never an override** (#65, C7 item 7). It
    reaches only the ramp functions that leave it unstated (`util.function__defaults`),
    so `expand(timeline, time_resolution=...)` samples the ramps that bind no resolution,
    and a ramp that binds one keeps it: `function=functools.partial(tanh,
    time_resolution=1e-3)` is a coarse ramp in a timeline expanded at the cycle period.
    That binding used to be overridden silently, since a `partial` still declares the
    keyword. A ramp binding none, expanded with none given, raises.

    How many rows make up one ramp is read from the ramp function itself
    (`ramp_function.points`), not passed in. It used to be the `num__bounds` argument,
    which could be given a number the data did not match and was named for the two-point
    case in which it need not have been given at all -- start and end are the *bounds*
    only while there is nothing between them (B6).
    """
    timeline = _given(timeline, "expand")

    if "num__bounds" in function_args:
        raise TypeError(
            "`expand` no longer takes `num__bounds`: how many points a ramp is made of"
            " is a property of its interpolating function, and is read from it. Declare"
            " it with `ramp_function.with_points(n)` if you are writing one."
        )

    if "function" not in timeline.columns:
        return timeline

    # Labels are the written positions from here on, which is what each ramp's rows are
    # put back at, and what makes the label-based `drop` below exact.
    timeline = timeline.reset_index(drop=True)
    _mask_fs = timeline["function"].notna()
    _dff = timeline[_mask_fs].sort_values(by=["variable", "time"])
    _indices_drop = _dff.index

    # For adding back in the value of other columns, based on the first row, like `context` etc. Written this way to allow for more, unknown columns to continue.
    _columns__keep = _dff.columns.drop(["time", "value", "variable", "function"])

    # Grouped per variable rather than by striding the whole frame. The old global stride
    # meant one variable with an odd number of rows silently misaligned the pairing of
    # *every* variable after it, and the failure surfaced as a bare
    # `ValueError: not enough values to unpack` from the tuple assignment, naming
    # nothing (B6). Per variable, the arithmetic is local and the offender has a name.
    _inds__start = []
    _dfs = []
    for variable, rows in _dff.groupby("variable", sort=False):
        points__required = wt_ramp_function.points(rows["function"].iloc[0])

        if len(rows) % points__required:
            raise ValueError(
                "\n".join(
                    [
                        "{} has {} ramp row(s), which is not a whole number of ramps:"
                        " {} makes each one out of {}.".format(
                            variable,
                            len(rows),
                            getattr(
                                rows["function"].iloc[0],
                                "__name__",
                                repr(rows["function"].iloc[0]),
                            ),
                            points__required,
                        ),
                        "",
                        "A ramp row is one carrying a `function`. Rows written by hand"
                        " into that column, or a `function` left on a row that was"
                        " meant to be a plain entry, are the usual causes.",
                    ]
                )
            )

        for i in range(0, len(rows), points__required):
            group = rows.iloc[i : i + points__required]
            _inds__start.append(group.index[0])

            # A default, never an override: each keyword reaches only the functions that
            # leave it unstated, so a ramp keeps a resolution it binds (#65, C7 item 7).
            function = group["function"].iloc[0]
            if "time_resolution" not in function_args and (
                "time_resolution" in wt_util.parameters__unstated(function)
            ):
                raise ValueError(
                    "{}'s ramp at {} s binds no `time_resolution`, and `expand` was given"
                    " none. Give one, `expand(timeline, time_resolution=1e-4)`, or bind"
                    " one into the ramp: `function=functools.partial(tanh,"
                    " time_resolution=1e-4)`. `adwin.core.convert` gives the cycle"
                    " period.".format(variable, group["time"].iloc[0])
                )
            func = wt_util.function__defaults(function, **function_args)

            # The internal constructor, because this is the one caller that assembles
            # rows rather than being handed them: `update` takes keywords only.
            _dfs.append(
                _populate_timeline(
                    [variable, func(*group[["time", "value"]].values)],
                    context=group["context"].iloc[0],
                ).assign(**group.iloc[0][_columns__keep].to_dict())
            )

    # Dropped into a new frame rather than in place. Every other function here returns a
    # new timeline and leaves its argument alone, and the "description is data" story
    # depends on a frame not changing under whoever is holding it -- `expand` was the one
    # exception, and it took both the ramp rows and the `function` column with it (B5).
    #
    # `adwin.core.convert` was unharmed only by accident of pipeline order:
    # `remove_unconnected_variables` runs first and hands `expand` a fresh frame.
    timeline = timeline.drop(index=_indices_drop).drop(columns=["function"])

    # Each ramp's rows go back where the ramp was written: before the first row kept from
    # after its start, in the order the ramps were written. Among a variable's rows at
    # one instant the last written is in effect, so this is not cosmetic. The ramps used
    # to land after rows written after them, and a ramp's end then superseded the
    # `update` written to supersede it (A18).
    ramps = sorted(zip(_inds__start, _dfs), key=lambda ramp: ramp[0])
    return wt_frame.insert_dataframes(
        timeline,
        list(timeline.index.searchsorted([start for start, _ in ramps])),
        [rows for _, rows in ramps],
    )
