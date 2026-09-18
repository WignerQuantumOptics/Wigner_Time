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

import funcy
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

noop = wt_util.mark_deferred(lambda timeline, **kwargs: timeline)
"""
A `stack` constituent that contributes nothing, for the branch of a conditional that
should add no rows.

Not `funcy.identity`: it has to carry the deferred tag, and tagging a shared library
function would mark it for every other user of `funcy`. Taking `**kwargs` also means it
survives a `stack` that forwards keywords -- `identity` did not, and raised
`TypeError: identity() got an unexpected keyword argument 'context'`.
"""

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
    # TODO: Remove dependence on pandas

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


def previous(
    timeline: wt_frame.CLASS,
    variable=None,
    time__max=None,
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
    return wt_origin.previous(
        timeline=timeline,
        variable=variable,
        time__max=time__max,
        column=column,
        sort_by=sort_by,
        index=index,
    )


###############################################################################
#                   Main functions
###############################################################################
def _populate_timeline(
    *vtvc,
    timeline: wt_frame.CLASS | None = None,
    t=0.0,
    context=None,
    origin=None,
    schema=_SCHEMA,
    **vtvc_dict,
) -> wt_frame.CLASS:
    """
    The shared body of `create` and `update`. **Internal**: the argument resolution is
    common to both, but the two public entry points expose different parts of it.

    Resolves the flexible `*vtvc` / `**vtvc_dict` input into rows, places them with
    respect to `origin`, and — when a `timeline` is given — inherits its context and
    concatenates.

    The input grammar itself is documented on `create`, not here: only `create` exposes
    the positional forms (`update` lost `*vtvc` with #71, `ramp` never had it), and this
    function is private, so mkdocstrings would not publish a description written here —
    which matters because `tab:inputSpecs` defers to the API documentation for exactly
    those forms.

    The split exists because `create` and `update` differ only in how they compose, and
    that difference is entirely about `timeline` and `origin`:

    - `create` starts a timeline from scratch, so neither argument means anything to it
      and neither is part of its signature. See §sec:functions of the manuscript, where
      `create` is documented as `create(*vtvc, t=0.0, context=None, **vtvc_dict)`.
    - `update` extends an existing one, so it takes both — and routes `origin` through
      `origin.auto` first, which is what makes its times relative by default.

    Positional `*vtvc` combined with a `timeline` is reachable only from here: `create`
    has the positional forms but no timeline, and `update` has the timeline but no
    positional forms.
    """
    rows = wt_input.rows_from_arguments(*vtvc, time=t, context=context, **vtvc_dict)

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

    # `anchor`, `last` and `variable` are reserved as origin labels
    # (`internal.origin._ORIGINS`), and `origin.find` tests them before it looks for a
    # variable or a context of that name -- so a name colliding with one is silently
    # unreachable as an origin (A9). Refused where the name is written rather than where
    # it fails to resolve, because by then the timeline no longer records that anything
    # else was meant.
    names__shadowing = {
        column: sorted(set(df_rows[column]) & set(wt_origin._ORIGINS))
        for column in ("variable", "context")
    }
    if any(names__shadowing.values()):
        raise ValueError(
            "\n".join(
                [
                    "Reserved origin label used as a name: {}.".format(
                        ", ".join(
                            "{} {}".format(column, names)
                            for column, names in names__shadowing.items()
                            if names
                        )
                    ),
                    "",
                    "{} are reserved for `origin`, and are resolved before any variable"
                    " or context of the same name -- so such a name could never be"
                    " referred to.".format(", ".join(map(repr, wt_origin._ORIGINS))),
                    "",
                    "Rename it: `molasses_end` rather than `last`.",
                ]
            )
        )

    df_rows = df_rows.astype(schema)
    new = wt_origin.update(df_rows, timeline, origin=origin)

    if timeline is not None:
        inherit.context(new, timeline, context=context)
        return wt_frame.concat([timeline, new])

    return new


def create(t=0.0, context=None, **vtvc_dict) -> wt_frame.CLASS:
    """
    Establishes a new timeline from the given (flexible) input collection.

    `create` initialises a timeline *from scratch*. It deliberately takes no `timeline`
    and no `origin`: there is nothing for the new rows to be relative to, which is the
    whole of the difference between it and `update`. To add to an existing timeline,
    use `update` — `update(..., origin=0.0)` reproduces exactly what passing a timeline
    to `create` used to do, and the default (anchor-then-last) origin is usually what
    was actually wanted.

    Input grammar
    -------------
    A variable is named as a keyword, and followed by what it does::

        create(AOM_MOT=<follows>)

    where ``<follows>`` is one of

    ======================================  ==========================================
    ``value``                               at ``t``
    ``[time, value]``
    ``[time, value, context]``
    ``[[time, value], [time, value], ...]``  several instants for one variable
    ======================================  ==========================================

    Several variables are given at once, and a computed set through ``**``::

        create(AOM_MOT=1, shutter_MOT=[0.1, 1, "MOT"])
        create(**{name: value for name, value in ...})

    ``t`` and ``context`` are **defaults, not overrides** — a variable stating its own
    keeps it. The keyword namespace is open by design, so an unrecognised keyword is
    read as a variable name rather than rejected (see the manuscript's `sec:forwarding`);
    that is what makes the injection idiom work, and it is why there is no second,
    positional way in to be confused with it.

    NOTE: It seems to be the case that dataframes use less memory than lists of
    dictionaries or dictionaries of lists (in general).
    """
    # `**vtvc_dict` is an open namespace -- an unrecognised keyword is read as a
    # variable name -- so `timeline=` and `origin=` would otherwise be swallowed by it
    # and then re-bound by `_populate_timeline`, which does declare them. That would
    # reinstate the very arguments this signature exists to withhold, silently. Neither
    # is a valid `variable` name (`config.VARIABLE__REGEX` requires two segments), so
    # intercepting them cannot shadow a legitimate one.
    for name, instead in [
        (
            "timeline",
            "`update(..., timeline=...)`; add `origin=0.0` for the absolute placement `create` used to give",
        ),
        ("origin", "`update(..., origin=...)`, or fold the offset into `t`"),
    ]:
        if name in vtvc_dict:
            raise TypeError(
                "`create` does not take `{n}`: it starts a timeline from scratch, so "
                "there is nothing for the new rows to be placed relative to. Use "
                "{i}.".format(n=name, i=instead)
            )

    return _populate_timeline(t=t, context=context, **vtvc_dict)


def update(
    timeline: wt_frame.CLASS | None = None,
    t=0.0,
    context=None,
    origin=None,
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
    timeline = wt_util.ensure_timeline(timeline, "update", columns__required=_SCHEMA)

    if timeline is None:
        return wt_util.function__lambda()

    else:
        # Check if anchor is desired and available
        origin = wt_origin.auto(
            timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS
        )

        return _populate_timeline(
            timeline=timeline,
            t=t,
            context=context,
            origin=origin,
            **vtvc_dict,
        )


def anchor(
    t,
    timeline=None,
    context=None,
    origin=None,
) -> wt_frame.CLASS | Callable:
    """
    Creates a special, non-physical `variable` (will never have a matching `connection`), that can be used for time references, particularly within individual `context`s.

    This can be very convenient in the context of `ramp`s, where the starting and ending times are often built around a hypothetical point in time, due to physical switching speeds.

    `t` is required. There is no sensible default: it is a displacement from whatever
    the `origin` resolves to, and the two readings a default would have to choose
    between are genuinely different instants (see below).

    *Where the anchor lands*

    By default the `origin` is the most recent anchor where one exists and the last
    entry otherwise, so `t` is normally a duration measured **from the end of the
    preceding stage**. That is what makes stages chain: a stage may write rows past its
    own closing anchor -- `optical_pumping` reinitialises shutters 0.1 s later -- without
    dragging the next stage along with them.

    To mark the end of everything written so far instead, ask for it explicitly:

        anchor(0.0, origin="last")     # here, at the last entry in the timeline
        anchor(0.0)                    # here, at the most recent anchor

    The two coincide until some stage writes past its own anchor, and then they do not:
    in the shipped demo they differ by ~0.1 s from `optical_pumping` onwards. Which one
    is meant is therefore worth stating at the call site rather than defaulting.

    NB.
    - Anchors are automatically numbered, for 'global' referencing, but these numbers are not necessary in normal use.
    """
    # NOTE: Makes use of a global variable (LABEL__ANCHOR).
    # TODO: Can include an example plot for illustration?

    if t is None:
        raise TypeError(
            "\n".join(
                [
                    "`anchor` requires `t`, a displacement from whatever `origin`"
                    " resolves to.",
                    "",
                    "    anchor(0.0)                    # at the most recent anchor",
                    "    anchor(0.0, origin='last')     # at the last entry so far",
                    "    anchor(duration)               # `duration` after the"
                    " preceding stage",
                ]
            )
        )

    timeline = wt_util.ensure_timeline(timeline, "anchor", columns__required=_SCHEMA)

    if timeline is None:
        return wt_util.function__lambda()

    num_anchors = timeline["variable"].loc[wt_anchor.mask(timeline)].nunique()

    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS
    )

    return update(
        timeline=timeline,
        t=t,
        context=context,
        origin=origin,
        **{"{}_{:03d}".format(wt_config.LABEL__ANCHOR, num_anchors + 1): 0},
    )


def ramp(
    timeline=None,
    duration=None,
    t=None,
    t2=None,
    context=None,
    origin=None,
    origin2=["variable", 0.0],
    function=wt_ramp_function.tanh,
    **vtvc_dict,
) -> wt_frame.CLASS | Callable:
    """
    Convenient ways of defining pairs of points and a function!

    A `ramp` defines ranges of values for each variable across time from a beginning time-value pair to an ending time-value pair. Primarily, for the sake of switching analogue devices on and off in a controllable way. Although a `ramp` can be as simple as a linear `value` progression from start to end, the default function for a `timeline` is hyperbolic tan. This allows the user to soften the value gradient at the beginning and end of the function.

    `ramp` has a slightly different interface to `create` and `update`. `**vtvc_dict` follows that of `create`, but it is assumed that `*vtvc` is not necessary, as if you wanted to specify the points manually (in big lists), you should use `create` or `update`. Also, ramps are defined in terms of the groups of points needed for the accompanying function. Usually, this will be starting and ending points. Supplying a different number of points will result in an error.

    *Examples of calling ramp*
    Normally, it will look something like
    `
    tl.stack(
        timeline,
        tl.ramp(
            coil_compensationX__A=0.0,
            coil_compensationY__A=0.0,
            coil_MOTlowerPlus__A=0.0,
            coil_MOTupperPlus__A=0.0,

            duration=duration,
            context="final_ramps"))
    `
    The variables are given end values independently and other options collectively. By default, the starting time is also inferred from the previous timeline and so chains of operations can be built up conveniently.

    For simpler ramps, it can still be easier, like in `create`, to supply everything in a list, e.g.
    `tl.ramp(lockbox_MOT__MHz=[500e-3,0.0])`
    or
    `tl.ramp(lockbox_MOT__MHz=[500e-3, 0.0, "final_ramps"])` - if you want a new `context`.
    This works because by default the ending time is relative to the starting time (see the `origin` keyword argument), such that 't_end' and 'duration' are the same.

    This will cover the vast majority of use cases, but sometimes there might be a need to control the start of a ramp explicitly, even with respect to the `origin`. This can be done similarly,  e.g.
    `lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]]`,
    but with the condition that the lists are not inhomogenous.

    NOTE: `duration` is a human-readable convenience for normal API usage. This is because the temporal origin of the second point is almost always in reference to the first point. Where there is a conflict, `t2` will have supremacy.
    """
    timeline = wt_util.ensure_timeline(timeline, "ramp", columns__required=_SCHEMA)

    if timeline is None:
        return wt_util.function__lambda()

    _vtvcs = {k: np.array(v) for k, v in vtvc_dict.items()}
    max_ndim = np.array([a.ndim for a in _vtvcs.values()]).flatten().max()

    if t2 is None and duration is not None:
        t2 = duration

    match max_ndim:
        case 0 | 1:
            rows1 = None
            rows2 = wt_input.rows_from_arguments(
                *[], time=t2, context=context, **vtvc_dict
            )

        case 2:
            _vtvc_1d = {k: v for k, v in _vtvcs.items() if v.ndim != 2}
            _vtvc_2d_0 = {k: v[0] for k, v in _vtvcs.items() if v.ndim == 2}
            _vtvc_2d_1 = {k: v[1] for k, v in _vtvcs.items() if v.ndim == 2}

            rows1 = wt_input.rows_from_arguments(
                *[], time=t, context=context, **_vtvc_2d_0
            )
            rows2 = wt_input.rows_from_arguments(
                *[], time=t2, context=context, **(_vtvc_1d | _vtvc_2d_1)
            )

        case _:
            raise ValueError(
                "Unsupported input to the `ramp` function. Only one or two tuples can be processed per variable."
            )

    # Prepare the starting points and then basically do two (shorcut-ed) `create`s. One depending on the previous timeline and one depending on the previous `create`.

    df_1 = wt_frame.new(rows1, columns=_SCHEMA.keys()).astype(_SCHEMA)
    df_2 = wt_frame.new(rows2, columns=_SCHEMA.keys()).astype(_SCHEMA)

    df__no_start_points = df_2[~df_2["variable"].isin(df_1["variable"])]
    if t is None:
        df__no_start_points.loc[:, ["time", "value"]] = 0.0
    else:
        df__no_start_points.loc[:, "time"] = t
        df__no_start_points.loc[:, "value"] = 0.0

    origin = wt_origin.auto(
        timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS__RAMP
    )

    # A value origin belongs only to a start point that had to be *inferred*. `df_1`
    # holds the ones the user stated explicitly, through the 2-D form that
    # `tab:rampExamples` describes as being for cases where the start cannot be inferred
    # from `origin` -- so adding the inferred value on top of them defeated the only
    # reason to use the form: a stated 1.0 came out as 8.0 (A8/#106). Those rows take
    # the time origin and nothing else.
    #
    # Nothing is lost by this. To start a ramp at the variable's current value but at a
    # stated time, the 2-D form was never needed: `ramp(v=target, t=..., duration=...)`
    # says it, and the default origin supplies the value.
    new1 = wt_frame.concat(
        [
            wt_origin.update(df_1, timeline, origin=[origin[0], None]),
            wt_origin.update(df__no_start_points, timeline, origin=origin),
        ]
    )
    new1["function"] = function
    inherit.context(new1, timeline, context=context)

    new2 = wt_origin.update(df_2, new1, origin=origin2)
    new2["function"] = function
    new2["context"] = new1["context"]

    # ===
    # TODO: It would be more efficient to do these checks earlier on (but more complicated).

    # `new1` and `new2` are assembled from different dictionaries and so do not hold
    # their variables in the same order: `new1` takes the explicitly started ones first
    # and the inferred ones after, `new2` the reverse. Subtracting them positionally
    # therefore compared one variable's boundary against another's whenever the two
    # input forms were mixed in a single call (B1/#108). Align on `variable` first --
    # each frame holds exactly one row per variable, `df_1` and `df__no_start_points`
    # being disjoint by construction.
    new2__aligned = wt_frame.align_to(new2, new1["variable"])

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
                    "Check `duration` (or `t2`) -- a duration computed as a difference"
                    " of two stage times is the usual way this comes out wrong. To"
                    " command a value at a single instant, use `update`.",
                ]
            )
        )

    # NOTE: Don't drop duplicates until after the expansion. Currently, this messes things up.
    return wt_frame.concat([timeline, new1, new2])


# def stack(firstArgument, *fs: list[Callable]) -> Callable | wt_frame.CLASS:
#     if isinstance(firstArgument, wt_frame.CLASS):
#         return funcy.compose(*fs[::-1])(firstArgument)
#     else:
#         return funcy.compose(*fs[::-1], firstArgument)


def _ensure_stackable(f):
    """
    A `stack` constituent must be a *deferred timeline function*, not merely callable.

    The distinction is invisible to Python: a deferred call, a composed `stack` and an
    uncalled user stage are all plain `function` objects with unhelpfully similar
    signatures. So the deferral machinery tags what it produces, and this checks the tag.

    The mistake it exists for is writing a stage's name where its call belongs --
    `stack(timeline, MOT)` for `stack(timeline, MOT(...))`. Without the tag that composes
    silently, binding the timeline to the stage's first parameter and returning a
    function where a timeline was expected. It was caught only when something followed it
    in the chain, so the tail of every composition went unguarded.
    """
    if wt_util.is_deferred(f) or isinstance(f, wt_frame.CLASS):
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
                    "A constituent must be a deferred timeline function -- what a core"
                    " function or a stage returns when called without a `timeline`:",
                    "",
                    "    stack(timeline, {}(...), update(...))".format(name),
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


def stack(
    timeline_or_f: wt_frame.CLASS | Callable, *fs: list[Callable], **kws
) -> Callable | wt_frame.CLASS:
    """
    For chaining modifications to the timeline in a composable way.

    If the first argument is a timeline, the result is also a timeline; otherwise, the result is a functional, which can later be applied on an existing timeline, /e.g./

    `stack(
        timeline,
        update(…),
        ramp(…)
    )`

    returns a timeline equivalent to

    `ramp(…, timeline=update(…, timeline=timeline))`.

    Constituents must **already have been called**: `stack` supplies only the timeline.
    `stack(timeline, MOT(duration=15))`, never `stack(timeline, MOT)` -- the latter
    raises. This is the opposite of `cascade`, which takes the stage functions themselves
    and calls them with the keywords routed to each.

    Also, all key-word arguments that are passed to `stack` are passed through to the subsidiary functions. This is particularly convenient for creating shared 'contexts', e.g.

    `stack(
        timeline,
        update(…),
        ramp(…),

        context='MOT'
    )`
    """

    for f in (timeline_or_f, *fs):
        _ensure_stackable(f)

    fs__wrapped = [lambda x, f=f: f(x, **kws) for f in fs]
    composed = funcy.compose(*reversed(fs__wrapped))

    if isinstance(timeline_or_f, wt_frame.CLASS):
        return composed(timeline_or_f)

    wrapped_first = lambda x: timeline_or_f(x, **kws)
    return wt_util.mark_deferred(funcy.compose(*reversed(fs__wrapped), wrapped_first))


def _route_keyword(key, names__by_length, stages__by_name):
    """
    Resolve one `cascade` keyword to a `(stage name, parameter name)` pair, or to
    `None` with the reason it could not be resolved.

    Matching is anchored to the start of the key and to a `_` boundary, so a parameter
    that merely *contains* a stage name is not captured by it. Candidates are tried
    longest first, because a shorter stage name can be a prefix of a longer one
    (`MOT_` also begins `MOT__detuned_growth_duration`).

    Longest-first alone is not enough to settle the genuine collision, though: if
    `MOT__detuned_growth` does not take the remainder but `MOT` does, the key belongs to
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


def cascade(*fs: list[Callable], **kws) -> Callable | wt_frame.CLASS:
    """
    Similarly to `stack`, a convenience that combines an arbitrary chain of functions with an arbitrary selection of associated keywords.

    `kws` are routed to the associated functions by prefixing, e.g. `cascade(MOT, molasses, MOT_duration=1.0)` creates a `stack` of `MOT` and `molasses`, with `duration=1.0` passed into the `MOT` function before evaluation.

    The motivation for this feature is that different experimental contexts should be built modularly, but, at final composition, the user often just wants a single point of contact to add/change nested variables.

    *How this differs from `stack`, which is easy to get wrong*

    `stack` takes stages that have **already been called**; `cascade` takes the stage
    functions **themselves** and calls them::

        stack(timeline, MOT(duration=15), molasses())     # called here
        cascade(MOT, molasses, MOT_duration=15)           # called by cascade

    In the first, `MOT(duration=15)` has had every argument but `timeline` supplied, and
    what it returns is a function of the timeline alone -- partial application, not
    currying, since the remaining argument is supplied in one call rather than one at a
    time. `stack` then threads the timeline through that chain.

    In the second, nothing has been called: `cascade` routes `MOT_duration=15` to `MOT`,
    calls it, and hands the results to `stack`. So a stage reaches `cascade` bare and
    reaches `stack` applied, and the two are not interchangeable -- writing
    `stack(timeline, MOT)` raises (see `_ensure_stackable`), and `cascade(MOT(...))`
    fails because the result takes no keywords to route.

    *What it returns*

    Whatever `stack` makes of the first stage's result: a timeline if that stage returns
    one -- `init` ends in `create`, so it does -- and a deferred function if it does not,
    as `MOT` ending in `update` does not. So `cascade` is itself stackable, and a
    `cascade` beginning mid-experiment composes like any other stage.

    Routing is **strict**: a keyword that names no stage, or that names one but is not a
    parameter of it, raises rather than being dropped. The alternative -- letting an
    unrouted keyword broadcast to every stage -- was considered and rejected, because
    every stage would turn it into rows, and into different *kinds* of row depending on
    whether the stage ends in an `update` or a `ramp`.

    Strictness is not configured but derived, from whether the target has `**kwargs`.
    That is only safe because the operation layer confines the open namespace to
    `default_state` and the two functions that wrap it; a stage that collects `**kwargs`
    is, correctly, still permissive here.

    WARNING: API is not settled; may get combined with `stack` in the next release.
    """
    # TODO:
    # - Consider alternative names: 'compose'?
    # - Consider nested dictionaries instead of prefixed keywords?
    #
    # NOTE: keyed by `__name__`, so a stage appearing twice receives the same keywords
    # both times. That is relied upon; see `KNOWN_ISSUES.md` §C.
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


def expand(timeline=None, num__bounds=2, **function_args) -> wt_frame.CLASS | Callable:
    """
    Converts the functions marked in the timeline into individual rows, i.e. applies the functions to the given data.

    This is generally a 'one-way' operation and so should only be carried out before the timeline is implemented on a device.

    `num__bounds` refers to the number of points (and so rows) needed to define the ramp function in the first place. Currently, this is implicitly assumed to be two, i.e. that `ramp`s are simply defined by the origin, terminus and expansion function.

    # NOTE: Not implemented for `num__bounds` != 2
    """
    timeline = wt_util.ensure_timeline(timeline, "expand", columns__required=_SCHEMA)

    if timeline is None:
        return wt_util.function__lambda(kwargs=["function_args"])

    if "function" not in timeline.columns:
        # TODO: Add test for this 'feature'
        return timeline

    _mask_fs = timeline["function"].notna()
    _dff = timeline[_mask_fs].sort_values(by=["variable", "time"])

    # Work out where the ramps start
    _indices_drop = _dff.index
    _inds__start = _dff.iloc[::num__bounds].index

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
        # - Only pass on the kwargs that the function accepts
        func = wt_util.function__filtered_kws(
            _group["function"].tolist()[0], **function_args
        )

        # The internal constructor, because this is the one caller that assembles rows
        # rather than being handed them: `create` takes keywords only.
        _dfs.append(
            _populate_timeline(
                [
                    _group["variable"].tolist()[0],
                    func(_pt_start, _pt_end),
                ],
            ).assign(**_group.iloc[0][_columns__keep].to_dict())
        )

    timeline.drop(index=_indices_drop, inplace=True)
    timeline.drop(columns=["function"], inplace=True)

    # Add the values back into the main timeline
    return wt_frame.insert_dataframes(timeline, _inds__start, _dfs)
