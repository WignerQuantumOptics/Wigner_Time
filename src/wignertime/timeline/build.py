# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Building a timeline: the stages a user writes (`update`, `anchor`, `ramp`), their
composition (`stack`, `cascade`), and the one way from a stage to a table
(`to_timeline`), which `expand` then samples.

Users reach these through the user API, `import wignertime.api.v0_9 as wt`. What these
functions need and share lives in `timeline.internal`.
"""

from typing import Callable

import numpy as np

from wignertime.timeline import ramp_function as wt_ramp_function
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import tags as wt_tags
from wignertime.internal import util as wt_util
from wignertime.timeline.internal import inherit
from wignertime.timeline.internal import checks as wt_checks
from wignertime.timeline.internal import compose as wt_compose
from wignertime.timeline.internal import stages as wt_stages


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


def update(
    *,
    time=0.0,
    context=wt_tags.CONTEXT__INFER,
    origin=wt_tags.ORIGIN__INFER,
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
    `origin` defaults to `wt_tags.INFER`: the anchor-then-last chain
    (`config.ORIGIN__DEFAULTS`) fills whichever slots are left unstated, so `time` is a
    duration from the end of the preceding stage. `None` means the same. For absolute
    time, write `origin=0.0`. On an empty timeline there is nothing to be relative to,
    and the origin is absolute zero.

    `time=-math.inf` is before the run and `time=math.inf` after it (#154): the initial
    and the final state, in the contexts a backend reserves for them (`ADwin_LowInit`,
    `ADwin_Finish`). Neither is an instant, so nothing is placed relative to them, and
    until something is written at an instant the origin is absolute zero.

    `context` defaults to `wt_tags.INFER` too: an unstated row inherits the latest
    context of the timeline it joins, from a row at an instant. `None` means the same.
    Every row has a context (#156): on an empty timeline, or one holding only the state
    before the run, there is nothing to inherit, so the rows must name theirs, and
    `context=""` is refused. A row added to a finished timeline inherits from the last
    stage of the run, not from the final state at +∞.
    """
    wt_checks.refuse_timeline("update", vtvc_dict)
    inherit.resolve(context)  # refused where it is written, not where it is applied

    return wt_util.stage(
        wt_stages.update,
        update,
        dict(time=time, context=context, origin=origin, **vtvc_dict),
    )


def anchor(
    time,
    *,
    context=wt_tags.CONTEXT__INFER,
    origin=wt_tags.ORIGIN__INFER,
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
        wt_stages.anchor, anchor, dict(time=time, context=context, origin=origin)
    )


def ramp(
    *,
    duration=None,
    time=None,
    time2=None,
    context=wt_tags.CONTEXT__INFER,
    origin=wt_tags.ORIGIN__INFER,
    origin2=[wt_tags.VARIABLE, 0.0],
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

    `origin` places the start in time. It defaults to `wt_tags.INFER`, the
    anchor-then-last chain, and `None` means the same; `origin=0.0` is absolute time, as
    for `update`.

    `context` defaults to `wt_tags.INFER`, and `None` means the same: an unstated row
    inherits the latest context of `timeline`. Every row has a context (#156), so
    `context=""` is refused.

    NOTE: `duration` is a human-readable convenience for normal API usage. This is because the temporal origin of the second point is almost always in reference to the first point. Where there is a conflict, `time2` will have supremacy. It is `time2` because `origin2` places the same point, the end.
    """
    wt_checks.refuse_timeline("ramp", vtvc_dict)
    inherit.resolve(context)  # refused where it is written, not where it is applied
    wt_checks.refuse_value_origin(origin)
    wt_checks.refuse_infinite_ends(time=time, time2=time2, duration=duration)

    return wt_util.stage(
        wt_stages.ramp,
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
    wt_checks.ensure_stackable(stage)

    onto = (
        wt_stages.empty()
        if onto is None
        else wt_util.ensure_timeline(
            onto,
            "to_timeline",
            name__argument="onto",
            columns__required=wt_stages.SCHEMA,
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
        wt_checks.ensure_stackable(f)

    constituents = list(stages)

    keywords__available = wt_compose.keywords_available(constituents)
    if keywords__available is not None:
        unplaced = sorted(k for k in kws if k not in keywords__available)
        if unplaced:
            raise TypeError(wt_compose.message__unplaced(unplaced, keywords__available))

    # Where no constituent says what it consumes, a keyword that none of them can even
    # accept would otherwise be dropped below without a word.
    unaccepted = sorted(
        k for k in kws if not any(wt_util.accepts_keyword(f, k) for f in constituents)
    )
    if unaccepted:
        raise TypeError(
            wt_compose.message__unplaced(unaccepted, keywords__available or set())
        )

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
    `stack(MOT)` raises (see `wt_checks.ensure_stackable`), and `cascade(MOT(...))` fails because
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

    WARNING: API is not settled; may get combined with `stack` in the next release.
    """
    # TODO:
    # - Consider alternative names: 'compose'?
    # - Consider nested dictionaries instead of prefixed keywords?
    #
    # NOTE: keyed by `__name__`, so a stage appearing twice receives the same keywords
    # both times. That is relied upon; see `KNOWN_ISSUES.md` §C.
    for f in fs:
        wt_checks.ensure_cascadable(f)

    stages__by_name = {f.__name__: f for f in fs}
    names__by_length = sorted(stages__by_name, key=len, reverse=True)

    args__dict = {}
    unroutable = {}
    for key, value in kws.items():
        routed, near_misses = wt_compose.route_keyword(
            key, names__by_length, stages__by_name
        )
        if routed is None:
            unroutable[key] = near_misses
        else:
            name, parameter = routed
            args__dict.setdefault(name, {})[parameter] = value

    if unroutable:
        raise TypeError(wt_compose.message__unroutable(unroutable, names__by_length))

    # Apply keywords to function stack
    return stack(*[f(**args__dict.get(f.__name__, {})) for f in fs])


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
    timeline = wt_stages.given(timeline, "expand")

    if "num__bounds" in function_args:
        raise TypeError(
            "`expand` no longer takes `num__bounds`: how many points a ramp is made of"
            " is a property of its interpolating function, and is read from it. Declare"
            " it with `ramp_function.with_points(n)` if you are writing one."
        )

    if not wt_frame.has_columns(timeline, ["function"]):
        # TODO: Add test for this 'feature'
        return timeline

    # Each ramp row carries the position it was written at, which is where the ramp's
    # rows are put back. A column, because a backend need not have row labels.
    _POSITION = "__position__expand"
    _mask_fs = ~wt_frame.isnull(wt_frame.column(timeline, "function"))
    _dff = wt_frame.sort(
        wt_frame.filter(
            wt_frame.with_column(
                timeline, _POSITION, np.arange(wt_frame.n_rows(timeline))
            ),
            _mask_fs,
        ),
        ["variable", "time"],
    )

    # For adding back in the value of other columns, based on the first row, like `context` etc. Written this way to allow for more, unknown columns to continue.
    _columns__keep = [
        c
        for c in wt_frame.columns(_dff)
        if c not in ("time", "value", "variable", "function", _POSITION)
    ]

    # Grouped per variable rather than by striding the whole frame. The old global stride
    # meant one variable with an odd number of rows silently misaligned the pairing of
    # *every* variable after it, and the failure surfaced as a bare
    # `ValueError: not enough values to unpack` from the tuple assignment, naming
    # nothing (B6). Per variable, the arithmetic is local and the offender has a name.
    _inds__start = []
    _dfs = []
    for variable, rows in wt_frame.group_by(_dff, "variable"):
        functions = wt_frame.column(rows, "function")
        times = wt_frame.column(rows, "time")
        values = wt_frame.column(rows, "value")
        positions = wt_frame.column(rows, _POSITION)
        points__required = wt_ramp_function.points(functions[0])

        if len(functions) % points__required:
            raise ValueError(
                "\n".join(
                    [
                        "{} has {} ramp row(s), which is not a whole number of ramps:"
                        " {} makes each one out of {}.".format(
                            variable,
                            len(functions),
                            getattr(functions[0], "__name__", repr(functions[0])),
                            points__required,
                        ),
                        "",
                        "A ramp row is one carrying a `function`. Rows written by hand"
                        " into that column, or a `function` left on a row that was"
                        " meant to be a plain entry, are the usual causes.",
                    ]
                )
            )

        for i in range(0, len(functions), points__required):
            group = slice(i, i + points__required)
            _inds__start.append(int(positions[i]))

            # A default, never an override: each keyword reaches only the functions that
            # leave it unstated, so a ramp keeps a resolution it binds (#65, C7 item 7).
            function = functions[i]
            if "time_resolution" not in function_args and (
                "time_resolution" in wt_util.parameters__unstated(function)
            ):
                raise ValueError(
                    "{}'s ramp at {} s binds no `time_resolution`, and `expand` was given"
                    " none. Give one, `expand(timeline, time_resolution=1e-4)`, or bind"
                    " one into the ramp: `function=functools.partial(tanh,"
                    " time_resolution=1e-4)`. `adwin.core.convert` gives the cycle"
                    " period.".format(variable, times[i])
                )
            func = wt_util.function__defaults(function, **function_args)

            # The internal constructor, because this is the one caller that assembles
            # rows rather than being handed them: `create` takes keywords only.
            first = wt_frame.row(rows, i)
            expanded = wt_stages.populate_timeline(
                [variable, func(*np.column_stack([times[group], values[group]]))],
                context=first["context"],
            )
            for c in _columns__keep:
                expanded = wt_frame.with_column(expanded, c, first[c])
            _dfs.append(expanded)

    # Dropped into a new frame rather than in place. Every other function here returns a
    # new timeline and leaves its argument alone, and the "description is data" story
    # depends on a frame not changing under whoever is holding it -- `expand` was the one
    # exception, and it took both the ramp rows and the `function` column with it (B5).
    #
    # `adwin.core.convert` was unharmed only by accident of pipeline order:
    # `remove_unconnected_variables` runs first and hands `expand` a fresh frame.
    positions__kept = np.flatnonzero(~_mask_fs)
    timeline = wt_frame.drop_columns(wt_frame.filter(timeline, ~_mask_fs), ["function"])

    # Each ramp's rows go back where the ramp was written: before the first row kept from
    # after its start, in the order the ramps were written. Among a variable's rows at
    # one instant the last written is in effect, so this is not cosmetic. The ramps used
    # to land after rows written after them, and a ramp's end then superseded the
    # `update` written to supersede it (A18).
    ramps = sorted(zip(_inds__start, _dfs), key=lambda ramp: ramp[0])
    return wt_frame.insert_dataframes(
        timeline,
        [int(p) for p in np.searchsorted(positions__kept, [s for s, _ in ramps])],
        [rows for _, rows in ramps],
    )
