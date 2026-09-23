# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

"""

from copy import deepcopy

from wignertime import config as wt_config
from wignertime.config import wtlog
from wignertime.internal import util as wt_util
from wignertime.internal.timeline import anchor as wt_anchor
from wignertime.internal import dataframe as wt_frame

###############################################################################
#                                  CONSTANTS                                   #
###############################################################################

_ORIGINS__TIME = ["anchor", "last", "variable"]
"""
Reserved origin labels admissible in the TIME slot. Every one of them names an instant.
"""

_ORIGINS__VALUE = ["variable"]
"""
Reserved origin labels admissible in the VALUE slot.

Only `"variable"` survives the narrowing, because only it names a quantity of the right
physical kind: the value *this* variable held. `"anchor"` and `"last"` are defined
temporally, so the value they yield belongs to whichever variable happens to hold the
relevant row -- a shutter's 0/1 added to a current in amps, silently. See KNOWN_ISSUES
A7.
"""

_ORIGINS = _ORIGINS__TIME
"""
These origin labels are reserved for interpretation by the package. Other origin strings
are interpreted as `variable`s, then as `context`s -- so a `variable` or `context` named
after one of these would be unreachable as an origin, and the name is therefore refused
where it is written (`timeline._populate_timeline`).
"""

_ORIGINS__BY_SLOT = {"time": _ORIGINS__TIME, "value": _ORIGINS__VALUE}
"""The vocabulary admitted by each slot of an `origin` pair. `find` dispatches on this."""


def error__unsupported_option(origin):
    return ValueError(
        f"{origin} is an unsupported option for 'origin' in `wignertime.internal.origin.find`. Check the formatting and whether this makes sense for your current timeline. \n\n If you feel like this option should be supported then don't hesitate to get in touch with the maintainers."
    )


def error__timeline(origin):
    return ValueError(f"Timeline not specified, but necessary for origin={origin}.")


def error__slot__value(label, reason):
    """
    Refusal of a label that resolves perfectly well, but not to a *value*.

    Raised rather than warned: unlike the time slot there is no sensible quantity to
    fall back on, and the wrong one is indistinguishable from the right one once it has
    been added to a current.
    """
    return ValueError(
        "\n".join(
            [
                "{!r} cannot serve as a VALUE origin: {}.".format(label, reason),
                "",
                'The value slot admits a number, "variable", or the name of a variable.',
                "",
                "To take a value from a named instant, name the variable and let the"
                " instant bound it in time:",
                "",
                '    origin=[{!r}, "variable"]'.format(label),
                "",
                "which reads the value this variable held there -- a time origin and a"
                " value origin, rather than one label asked to be both.",
            ]
        )
    )


#############################################################################
#   METHODS                                                                 #
#############################################################################


def previous(
    timeline: wt_frame.CLASS,
    variable=None,
    column="variable",
    time__max=None,
    sort_by=None,
    index=-1,
):
    """
    Returns a row from the timeline. By default, this is done by finding the highest value for time and returning that row. If `sort_by` is specified (e.g. 'time'), then the dataframe is sorted and then the row indexed by `index` is returned.

    Anchors are a special case, where an exact match on the symbol is not required.

    Raises ValueError if the specified variable, or timeline, doesn't exist.
    """
    if timeline is None or timeline.empty:
        raise ValueError(
            "\n".join(
                [
                    "Nothing to resolve {}against: the timeline is empty.".format(
                        "`{}` ".format(variable) if variable is not None else ""
                    ),
                    "",
                    "An origin is a reference to something already written. On an empty"
                    " timeline there is nothing to refer to, so give a number instead"
                    " -- `origin=0.0` places the rows in absolute time.",
                ]
            )
        )

    if time__max is not None:
        tline = timeline[timeline["time"] <= time__max]
    else:
        tline = timeline

    if variable is not None:
        tl__filtered = tline[tline[column] == variable]
        if tl__filtered.empty and (variable == wt_config.LABEL__ANCHOR):
            tl__filtered = tline[tline[column].str.startswith(variable)]
        if tl__filtered.empty:
            raise ValueError("Previous {} not found".format(variable))
    else:
        tl__filtered = tline

    if sort_by is None:
        return wt_frame.row_from_max_column(tl__filtered)

    # Rebound rather than sorted in place: `tl__filtered` is a boolean-mask slice, and
    # `inplace=True` on one is undefined -- pandas 2 answers correctly but raises
    # `SettingWithCopyWarning`, and pandas 3 makes copy-on-write unconditional (B3, #88).
    # The two branches this replaces returned the same expression anyway.
    if not tl__filtered[sort_by].is_monotonic_increasing:
        tl__filtered = tl__filtered.sort_values(sort_by)
    return tl__filtered.iloc[index]


def _is_satisfiable__time(timeline, label):
    """Whether this time reference has anything to refer to in this timeline."""
    if label == "anchor":
        return wt_anchor.is_available(timeline)
    if label == "last":
        return (timeline is not None) and (not timeline.empty)
    return True


def auto(timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS):
    """
    Completes a partial `origin` from the caller's defaults, **slot by slot**.

    `None` in a slot means *defer to the default for this slot*. `0.0` means *absolute
    -- no shift*. Keeping those two apart is the whole of A6: a bare string pads to
    `[s, None]` (`util.ensure_pair`), and while `None` meant "absolute" that silently
    cancelled `ramp`'s value default, so the documented interweaving idiom
    `ramp(..., origin="stage1")` started the ramp from zero. Completing per slot makes it
    mean what it reads as -- time from `stage1`, value from the variable itself.

    The time default is a **chain owned by the caller**, not a single constant: each
    entry's time slot is tried in turn and the first one this timeline can satisfy is
    taken. The chain is terminal -- if nothing is satisfiable the time origin is `0.0`,
    with a warning. It can therefore no longer return `None` implicitly, which is A4: a
    `ramp` onto an anchorless timeline used to fall off the end of its own single-entry
    chain and land in absolute time, *before* the rows it was appended to.

    The value default is taken from the same entry, so a caller states the pair it wants
    once: `[["anchor", "variable"], ["last", "variable"]]` for `ramp`, whose start value
    must be looked up; `[["anchor", None], ["last", None]]` for `update` and `anchor`,
    whose values are absolute.

    NOTE: Assumes that origin__defaults is a list of pairs.
    """
    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))

    if origin__defaults is None:
        return o

    entry = None
    for od in origin__defaults:
        candidate = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(od))
        if isinstance(candidate[0], str) and not _is_satisfiable__time(
            timeline, candidate[0]
        ):
            continue
        entry = candidate
        break

    if entry is None:
        entry = [
            0.0,
            (
                wt_util.ensure_pair(
                    wt_util.ensure_iterable_with_None(origin__defaults[-1])
                )[1]
                if origin__defaults
                else None
            ),
        ]
        if o[0] is None:
            wtlog.warning(
                "No time origin could be resolved from %s, so the new rows are placed "
                "in absolute time. This timeline has neither an anchor nor any entry to "
                "be relative to; state `origin=0.0` to say so deliberately.",
                origin__defaults,
            )

    return [entry[i] if o[i] is None else o[i] for i in (0, 1)]


def auto_or_off(timeline, origin, origin__defaults):
    """
    The wrapper `update`, `anchor` and `ramp` call in place of `auto` itself, so that
    their own `origin` parameter can carry a distinction `auto` was never asked to make.

    Their signature default is `wt_config.ORIGIN__INFER`, not `None` (A8, 2026-09-23):
    a caller who writes nothing gets this sentinel, translated below into the bare
    `None` that `auto` has always read as "run the default chase" -- so nothing about
    that path changes. A caller who writes `origin=None` *explicitly* is asking for the
    opposite, and can only mean it explicitly, since it is no longer reachable any other
    way: no origin resolution at all. `origin__defaults` is not even consulted; the pair
    stays `[None, None]`, which `update` (below) already treats as a complete no-op --
    the stated coordinates come back exactly as given, in whichever slots the caller
    filled in themselves.

    `auto` itself is untouched by any of this and keeps its own long-standing contract:
    called directly, a bare `None` still means "run the defaults", exactly as its own
    tests pin. This wrapper exists because the three public entry points needed a
    distinct spelling for "off" that `auto` was never asked to provide -- not because
    `auto`'s own meaning needed to change.
    """
    if origin is None:
        return [None, None]

    if isinstance(origin, str) and origin == wt_config.ORIGIN__INFER:
        origin = None

    return auto(timeline, origin, origin__defaults=origin__defaults)


def sanitize_origin(timeline, orig):
    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(orig))
    if len(o) != 2:
        raise error__unsupported_option(orig)
    if any(isinstance(e, str) for e in o) and timeline is None:
        raise error__timeline(orig)
    return o


def find(
    timeline=None,
    origin=None,
    label__anchor=wt_config.LABEL__ANCHOR,
    time__max__relative=None,
):
    """
    Returns a time-value pair, according to the choice of origin.

    Often, `None` will be returned for a value as it would be presumptuous to assume the same value origin for all devices.

    N.B. `"variable"` is **not** resolved here: it is a placeholder for whichever variable
    is being placed, and `origin.update` substitutes the actual name before calling this
    function. It is listed among the reserved words because that is where users meet it.

    N.B. `variable` strings take precedence over `context`s and `context`s are special. For convenience, using a `context` as an `origin` will default to picking out an `anchor`, if available. If not, then the 'last' value of the context will be used.

    `time__max` is the (non origin-corrected) maximum time that should be considered when trying to find previous values.

    The two slots admit different vocabularies
    ------------------------------------------

    ======  ======================================================================
    time    a number, "anchor", "last", "variable", a variable name, a context name
    value   a number, "variable", a variable name
    ======  ======================================================================

    The time slot asks *when*, and each of its options names an instant. The value slot
    asks *how much, of what*, and only a variable names a quantity: `"anchor"`, `"last"`
    and a context name all resolve to whichever variable happens to hold the row at that
    instant, so they answer in the wrong units without saying so. They therefore raise
    here rather than resolving (KNOWN_ISSUES A7, settled by the maintainer 2026-09-18).

    Nothing is lost by the narrowing, because the intended reading is already sayable as
    a pair: "the value `coil__A` held at the end of molasses" is `["molasses",
    "variable"]` -- the context bounds the lookup in time, the variable names what is
    looked up.

    Example origins:
    - [0.0,0.0]
    - 0.0
    - "anchor"
    - ["anchor", 0.0]
    - "last" (The row highest in time)
    - "AOM_shutter" (A variable name that is present in the dataframe)
    - "init" (A context name that is present in the dataframe)
    - ["init", "variable"] (time from a context, value from each variable itself)
    """

    # TODO:
    # - More meaningful error if anchor is not available

    # Normalised once, here. `find` used to do this twice -- once for the early return
    # and again through `sanitize_origin` -- which left the "a string origin needs a
    # timeline" check unable to gate the early return, and a reader unable to tell which
    # normalisation was authoritative (D10/#124).
    o = sanitize_origin(timeline, origin)

    if o == [None, None]:
        return [None, None]

    def _is_available__variable(var):
        return (
            (timeline["variable"] == var).any()
            if (timeline is not None) and (var is not None)
            else None
        )

    def _is_available__context(var):
        return (
            (timeline["context"] == var).any()
            if (timeline is not None) and (var is not None)
            else None
        )

    def _previous_vt(
        timeline, get="time", col__fil="variable", var=None, time__max=None
    ):
        """
        `get` is one of ['time', 'value', 'BOTH']
        """
        match get:
            case "time" | "value":
                return previous(
                    timeline, column=col__fil, variable=var, time__max=time__max
                ).at[get]
            case "both":
                return previous(
                    timeline, column=col__fil, variable=var, time__max=time__max
                )[["time", "value"]].values

    def _to_col_var(timeline, label, slot="time"):
        """
        Maps an origin label onto a `[column, value]` filter for `previous`.

        The two slots admit different vocabularies, because they ask different
        questions. The time slot asks *when*, and anything naming an instant answers it.
        The value slot asks *how much, of what*, and only a variable names a quantity:
        `"anchor"`, `"last"` and context names each resolve to whichever variable
        happens to hold the row at that instant, so they answer in the wrong units
        without saying so.
        """
        if (label in _ORIGINS) and (label not in _ORIGINS__BY_SLOT[slot]):
            raise error__slot__value(label, "it names an instant, not a quantity")

        if label == "variable":
            # `"variable"` is a placeholder, not a reference: it means "each variable
            # relative to its own entry", which only has an answer once a variable has
            # been named. `origin.update`'s per-variable loop substitutes the actual
            # name before calling `find`, so `find` never sees it through the public
            # API -- but it is listed in `_ORIGINS` and in this function's own
            # docstring, so reaching here directly deserves better than
            # `unsupported option` (D8/#122).
            raise ValueError(
                "\n".join(
                    [
                        '`origin="variable"` cannot be resolved by `origin.find`'
                        " alone: it stands for whichever variable is being placed, and"
                        " `find` resolves one origin for the frame as a whole.",
                        "",
                        "It is substituted per variable by `origin.update`, so it works"
                        " through `update`, `ramp` and `anchor`. To resolve one here,"
                        " name the variable.",
                    ]
                )
            )

        if label == "anchor":
            if not wt_anchor.is_available(timeline):
                raise ValueError(
                    "`origin='anchor'` was asked for, but this timeline holds no"
                    " anchor. Close the preceding stage with `anchor(duration)`, or"
                    " name what to be relative to -- `origin='last'`, a context, a"
                    " variable, or a number."
                )
            return ["variable", label__anchor]
        elif label == "last":
            return ["variable", None]
        elif _is_available__variable(label):
            return ["variable", label]
        elif _is_available__context(label):
            if slot == "value":
                raise error__slot__value(
                    label,
                    "it is a context, and a context's last row may belong to any"
                    " variable in it",
                )
            anchor = wt_anchor.last(timeline, context=label)
            return ["variable", anchor] if (anchor is not None) else ["context", label]
        elif slot == "value":
            # Reached most often through `ramp`'s `"variable"` default, once
            # `find_every_origin` has substituted the actual name: the variable is being
            # ramped but has no history to start from. `error__unsupported_option` reads
            # as though the name were malformed, which sends the reader to the wrong
            # place entirely.
            raise ValueError(
                "\n".join(
                    [
                        "No previous value of {!r} to start from: it does not appear in"
                        " this timeline.".format(label),
                        "",
                        "A ramp runs from where the variable currently sits, so it needs"
                        " one. Either set the variable before ramping it, or state both"
                        " ends -- `{}=[[t_start, value_start], [t_end, value_end]]`"
                        " -- and give an absolute value origin,"
                        " `origin=[<time>, 0.0]`.".format(label),
                    ]
                )
            )
        else:
            raise error__unsupported_option(label)

    # The slots are resolved in order, because the value lookup is bounded by the time
    # origin: the value taken is the one *in effect at the instant the new rows will
    # occupy*, not the variable's last value in the timeline as a whole. That is what
    # lets an operation be interwoven and still see the state that physically precedes
    # it (`sec:origin_full`).
    #
    # There is now one definition of that bound instead of two (B7/#114). The numeric
    # branch used to build it from the *raw* time slot, so `[None, "variable"]` was
    # `None + float` -- a `TypeError` that made a value-only origin unusable through the
    # public API -- and the two branches disagreed about what "in effect" meant.
    time__relative = 0.0 if time__max__relative is None else time__max__relative

    match o[0]:
        case None:
            t = None
        case bool():
            raise error__unsupported_option(o)
        case float() | int():
            t = o[0]
        case str(s):
            t = _previous_vt(*([timeline, "time"] + _to_col_var(timeline, s, "time")))
        case _:
            raise error__unsupported_option(o)

    match o[1]:
        case None:
            v = None
        case bool():
            raise error__unsupported_option(o)
        case float() | int():
            v = o[1]
        case str(s):
            v = _previous_vt(
                *([timeline, "value"] + _to_col_var(timeline, s, "value")),
                # `TIME_RESOLUTION` makes the bound inclusive of a row sitting exactly
                # at the origin instant, against floating-point drift.
                time__max=(0.0 if t is None else t)
                + time__relative
                + wt_config.TIME_RESOLUTION,
            )
        case _:
            raise error__unsupported_option(o)

    return [t, v]


def update(
    timeline__present: wt_frame.CLASS,
    timeline__past: wt_frame.CLASS | None,
    origin=None,
) -> wt_frame.CLASS:
    """
    Returns a new timeline, changed according to the 'new' starting time and value.
    """

    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))
    if o == [None, None]:
        return timeline__present

    timeline__future = deepcopy(timeline__present)

    def _update_future(tlfuture, t0, v0, variable=None):
        if variable is not None:
            if t0 is not None:
                wt_frame.increment_selected_rows(tlfuture, **{variable: t0})
            if v0 is not None:
                wt_frame.increment_selected_rows(
                    tlfuture, column__increment="value", **{variable: v0}
                )
        else:
            if t0 is not None:
                tlfuture["time"] += t0
            if v0 is not None:
                tlfuture["value"] += v0
        return tlfuture

    def find_every_origin(timeline__past, timeline__future, input):
        """
        input is an origin, but where `variable` is a general placeholder: can be [var, None], [None, var], [var, var], [a,var], [var,a], [num,var], [var, num], where `var` is a specific variable reference.

        Now allows for `timeline__future` to deal with values 'inside' `timeline__past`.
        """

        # Computed **once**, before the loop. `_update_future` mutates the very times
        # this is measured from, so recomputing it per variable made the answer depend
        # on what else was being resolved, and in what order: adding an unrelated
        # variable to a `ramp` call moved another variable's start value (B2/#109).
        time__max__relative = timeline__future["time"].min()

        for var in timeline__future["variable"].unique():

            _t0, _v0 = find(
                timeline__past,
                origin=[var if e == "variable" else e for e in input],
                time__max__relative=time__max__relative,
            )
            timeline__future = _update_future(
                timeline__future,
                _t0,
                _v0,
                variable=var,
            )

    if timeline__past is not None:
        find_every_origin(timeline__past, timeline__future, o)

    else:
        _t0, _v0 = find(origin=origin)

        _update_future(timeline__future, _t0, _v0, variable=None)

    return timeline__future
