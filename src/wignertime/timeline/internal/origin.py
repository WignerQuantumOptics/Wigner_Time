# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

"""

from copy import deepcopy

import numpy as np

from wignertime.timeline import query as wt_query
from wignertime.internal import tags as wt_tags
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util as wt_util
from wignertime.timeline.internal import anchor as wt_anchor

###############################################################################
#                                  CONSTANTS                                   #
###############################################################################

ANCHOR, LAST, VARIABLE = wt_tags.ANCHOR, wt_tags.LAST, wt_tags.VARIABLE

_ORIGINS__TIME = [ANCHOR, LAST, VARIABLE]
"""
The tags admissible in the TIME slot (`config.Origin`). Every one of them names an instant.
"""

_ORIGINS__VALUE = [VARIABLE]
"""
The tags admissible in the VALUE slot.

Only `VARIABLE` survives the narrowing, because only it names a quantity of the right
physical kind: the value *this* variable held. `ANCHOR` and `LAST` are defined
temporally, so the value they yield belongs to whichever variable happens to hold the
relevant row -- a shutter's 0/1 added to a current in amps, silently. See KNOWN_ISSUES
A7.
"""

_ORIGINS = _ORIGINS__TIME
"""
The tags, all of them. Since #158 they are not strings, so a string in an origin is always
a name -- of a variable first, then of a context -- and nothing needs reserving.
"""

_WORDS = {tag.value: tag for tag in _ORIGINS}
"""The strings the tags were, until #158, for the message that says so."""

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
                "The value slot admits a number, VARIABLE, or the name of a variable.",
                "",
                "To take a value from a named instant, name the variable and let the"
                " instant bound it in time:",
                "",
                "    origin=[{!r}, VARIABLE]".format(label),
                "",
                "which reads the value this variable held there -- a time origin and a"
                " value origin, rather than one label asked to be both.",
            ]
        )
    )


#############################################################################
#   METHODS                                                                 #
#############################################################################


def instants(timeline):
    """
    The rows of `timeline` that sit at an instant: those at a finite time.

    A row at −∞ is before the run and one at +∞ after it (#154). Neither is an instant
    anything can be placed relative to, or inherit a context from. So the time slot of an
    origin, the default chain's `LAST`, and context inheritance all look here only. A
    value lookup does not: it is bounded by a finite instant, so it sees what was set
    before the run, and never what is set after it.
    """
    if timeline is None:
        return None
    return wt_frame.filter(
        timeline, np.isfinite(wt_frame.column(timeline, "time", dtype=float))
    )


def _refuse__no_instant(timeline, at_instants, column, name, label):
    """
    A time reference whose rows are all at ±∞ names no instant (#154), and says so rather
    than reporting an empty timeline or a name that is not there. Anchors need no check:
    one at ±∞ is refused where it is written.
    """

    def present(tline):
        if name is None:
            return not wt_frame.is_empty(tline)
        return bool((wt_frame.column(tline, column) == name).any())

    if (
        column == "variable"
        and name is not None
        and name.startswith(wt_tags.LABEL__ANCHOR)
    ):
        return
    if present(timeline) and not present(at_instants):
        raise ValueError(
            "\n".join(
                [
                    "`origin={!r}` names no instant: {} at ±∞, before or after the"
                    " run (#154), and neither is an instant to place anything relative"
                    " to.".format(
                        label,
                        (
                            "every row of this timeline is"
                            if name is None
                            else "every row of {!r} is".format(name)
                        ),
                    ),
                    "",
                    "Refer to a stage of the run, or give a number: on a timeline with"
                    " nothing at an instant yet, the first rows are placed in absolute"
                    " time by default.",
                ]
            )
        )


def _is_satisfiable__time(timeline, label):
    """Whether this time reference has anything to refer to in this timeline."""
    if label is ANCHOR:
        return wt_anchor.is_available(timeline)
    if label is LAST:
        return (timeline is not None) and (not wt_frame.is_empty(instants(timeline)))
    return True


def auto(timeline, origin, origin__defaults):
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
    taken. The chain is terminal -- if nothing is satisfiable the time origin is `0.0`.
    It can therefore no longer return `None` implicitly, which is A4: a `ramp` onto an
    anchorless timeline used to fall off the end of its own single-entry chain and land
    in absolute time, *before* the rows it was appended to.

    Nothing is satisfiable only on a timeline with no row at an instant (`instants`),
    since `LAST` is satisfiable on any other, and there absolute zero is the one answer:
    an empty timeline, or one holding only the state before the run, at −∞ (#154). That
    is what places the first timed stage, so it needs no `origin=0.0` of its own. It used
    to come with a warning. Since #85 every timeline starts from an empty one
    (`to_timeline`), so the warning would fire once per experiment and tell nobody
    anything (C7, item 3).

    The value default is taken from the same entry, so a caller states the pair it wants
    once: `[[ANCHOR, VARIABLE], [LAST, VARIABLE]]` for `ramp`, whose start value
    must be looked up; `[[ANCHOR, None], [LAST, None]]` for `update` and `anchor`,
    whose values are absolute.

    `origin__defaults` is **required**, and deliberately has no default of its own.
    Defaulting it to `wt_config.ORIGIN__DEFAULTS` bound that object at import time, so
    rebinding the config attribute -- which is how `config.VARIABLE__REGEX` is documented
    to work, and how the Lab2 regression fixture uses it -- would silently have had no
    effect here, while mutating it in place would have. Two config knobs that look alike
    should not behave oppositely. Every call site in `timeline.py` already reads the
    attribute at call time and passes it explicitly, so nothing is lost.

    Pass `None` to complete nothing and take the origin as given.

    `wt_tags.INFER`, the signature default of the public functions, is read as `None`
    wherever it appears -- as the whole origin or in one slot -- so that the marker is a
    visible name for the default and not a second meaning beside it (#142).

    NOTE: Assumes that origin__defaults is a list of pairs.
    """
    if origin is wt_tags.INFER:
        origin = None
    o = [
        None if slot is wt_tags.INFER else slot
        for slot in wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))
    ]

    if origin__defaults is None:
        return o

    entry = None
    for od in origin__defaults:
        candidate = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(od))
        if isinstance(
            candidate[0], (str, wt_tags.Origin)
        ) and not _is_satisfiable__time(timeline, candidate[0]):
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

    return [entry[i] if o[i] is None else o[i] for i in (0, 1)]


def sanitize_origin(timeline, orig):
    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(orig))
    if len(o) != 2:
        raise error__unsupported_option(orig)
    if any(isinstance(e, (str, wt_tags.Origin)) for e in o) and timeline is None:
        raise error__timeline(orig)
    return o


def find(
    timeline=None,
    origin=None,
    label__anchor=wt_tags.LABEL__ANCHOR,
    time__max__relative=None,
):
    """
    Returns a time-value pair, according to the choice of origin.

    Often, `None` will be returned for a value as it would be presumptuous to assume the same value origin for all devices.

    N.B. `VARIABLE` is **not** resolved here: it is a placeholder for whichever variable
    is being placed, and `origin.update` substitutes the actual name before calling this
    function. It is listed among the reserved words because that is where users meet it.

    N.B. `variable` strings take precedence over `context`s and `context`s are special. For convenience, using a `context` as an `origin` will default to picking out an `anchor`, if available. If not, then the 'last' value of the context will be used.

    `time__max` is the (non origin-corrected) maximum time that should be considered when trying to find previous values.

    The two slots admit different vocabularies
    ------------------------------------------

    ======  ======================================================================
    time    a number, ANCHOR, LAST, VARIABLE, a variable name, a context name
    value   a number, VARIABLE, a variable name
    ======  ======================================================================

    The time slot asks *when*, and each of its options names an instant. The value slot
    asks *how much, of what*, and only a variable names a quantity: `ANCHOR`, `LAST`
    and a context name all resolve to whichever variable happens to hold the row at that
    instant, so they answer in the wrong units without saying so. They therefore raise
    here rather than resolving (KNOWN_ISSUES A7, settled by the maintainer 2026-09-18).

    Nothing is lost by the narrowing, because the intended reading is already sayable as
    a pair: "the value `coil__A` held at the end of molasses" is `["molasses",
    VARIABLE]` -- the context bounds the lookup in time, the variable names what is
    looked up.

    Example origins:
    - [0.0,0.0]
    - 0.0
    - ANCHOR
    - [ANCHOR, 0.0]
    - LAST (The row highest in time)
    - "AOM_shutter" (A variable name that is present in the dataframe)
    - "init" (A context name that is present in the dataframe)
    - ["init", VARIABLE] (time from a context, value from each variable itself)
    """

    # Normalised once, here. `find` used to do this twice -- once for the early return
    # and again through `sanitize_origin` -- which left the "a string origin needs a
    # timeline" check unable to gate the early return, and a reader unable to tell which
    # normalisation was authoritative (D10/#124).
    o = sanitize_origin(timeline, origin)

    if o == [None, None]:
        return [None, None]

    def _is_available__variable(var):
        return (
            bool((wt_frame.column(timeline, "variable") == var).any())
            if (timeline is not None) and (var is not None)
            else None
        )

    def _is_available__context(var):
        return (
            bool((wt_frame.column(timeline, "context") == var).any())
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
                return wt_query.previous(
                    timeline, column=col__fil, variable=var, time__max=time__max
                )[get]
            case "both":
                row = wt_query.previous(
                    timeline, column=col__fil, variable=var, time__max=time__max
                )
                return np.array([row["time"], row["value"]])

    def _to_col_var(timeline, label, slot="time"):
        """
        Maps an origin label onto a `[column, value]` filter for `previous`.

        The two slots admit different vocabularies, because they ask different
        questions. The time slot asks *when*, and anything naming an instant answers it.
        The value slot asks *how much, of what*, and only a variable names a quantity:
        `ANCHOR`, `LAST` and context names each resolve to whichever variable
        happens to hold the row at that instant, so they answer in the wrong units
        without saying so.
        """
        if isinstance(label, wt_tags.Origin) and label not in _ORIGINS__BY_SLOT[slot]:
            raise error__slot__value(label, "it names an instant, not a quantity")

        if label is VARIABLE:
            # `VARIABLE` is a placeholder, not a reference: it means "each variable
            # relative to its own entry", which only has an answer once a variable has
            # been named. `origin.update`'s per-variable loop substitutes the actual
            # name before calling `find`, so `find` never sees it through the public
            # API -- but it is listed in `_ORIGINS` and in this function's own
            # docstring, so reaching here directly deserves better than
            # `unsupported option` (D8/#122).
            raise ValueError(
                "\n".join(
                    [
                        "`origin=VARIABLE` cannot be resolved by `origin.find`"
                        " alone: it stands for whichever variable is being placed, and"
                        " `find` resolves one origin for the frame as a whole.",
                        "",
                        "It is substituted per variable by `origin.update`, so it works"
                        " through `update`, `ramp` and `anchor`. To resolve one here,"
                        " name the variable.",
                    ]
                )
            )

        if label is ANCHOR:
            if not wt_anchor.is_available(timeline):
                raise ValueError(
                    "`origin=ANCHOR` was asked for, but this timeline holds no"
                    " anchor. Close the preceding stage with `anchor(duration)`, or"
                    " name what to be relative to -- `origin=LAST`, a context, a"
                    " variable, or a number."
                )
            return ["variable", label__anchor]
        elif label is LAST:
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
        elif label in _WORDS:
            # One of the words the tags were: a name now, and nothing here has it.
            raise ValueError(
                "\n".join(
                    [
                        "`{0!r}` is taken as a name, and nothing in this timeline is"
                        " called that.".format(label),
                        "",
                        "The reserved origin words are tags since #158, so that a"
                        " string is always a name:",
                        "",
                        "    origin=tl.{0}".format(_WORDS[label]),
                    ]
                )
            )
        elif slot == "value":
            # Reached most often through `ramp`'s `VARIABLE` default, once
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
                        "A ramp starts where its variable is (#142), so the variable has"
                        " to have been set: `update` it first --"
                        " `stack(update({0}=...), ramp({0}=..., duration=...))`.".format(
                            label
                        ),
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
    # branch used to build it from the *raw* time slot, so `[None, VARIABLE]` was
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
        case wt_tags.Origin() | str():
            # The time slot asks *when*, and only a row at an instant answers: one at
            # ±∞ is before or after the run (#154).
            column, name = _to_col_var(timeline, o[0], "time")
            at_instants = instants(timeline)
            _refuse__no_instant(timeline, at_instants, column, name, o[0])
            t = _previous_vt(at_instants, "time", column, name)
        case _:
            raise error__unsupported_option(o)

    match o[1]:
        case None:
            v = None
        case bool():
            raise error__unsupported_option(o)
        case float() | int():
            v = o[1]
        case wt_tags.Origin() | str():
            # The bound is inclusive (`previous` compares with `<=`), so a row sitting
            # exactly at the origin instant is already in effect there. It used to be
            # widened by `config.TIME_RESOLUTION`, which admitted rows up to 1 us
            # *after* the instant as though they preceded it, and tied a construction-
            # time lookup to a hardware period there is no machine to ask for. Setting
            # it to zero changed no result in the suite, the Lab2 checksums included.
            v = _previous_vt(
                *([timeline, "value"] + _to_col_var(timeline, o[1], "value")),
                time__max=(0.0 if t is None else t) + time__relative,
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
                tlfuture = wt_frame.increment_selected_rows(tlfuture, **{variable: t0})
            if v0 is not None:
                tlfuture = wt_frame.increment_selected_rows(
                    tlfuture, column__increment="value", **{variable: v0}
                )
        else:
            if t0 is not None:
                tlfuture = wt_frame.with_column(
                    tlfuture, "time", wt_frame.column(tlfuture, "time") + t0
                )
            if v0 is not None:
                tlfuture = wt_frame.with_column(
                    tlfuture, "value", wt_frame.column(tlfuture, "value") + v0
                )
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
        time__max__relative = wt_frame.column(timeline__future, "time").min()

        for var in wt_frame.unique(timeline__future, "variable"):

            _t0, _v0 = find(
                timeline__past,
                origin=[var if e is VARIABLE else e for e in input],
                time__max__relative=time__max__relative,
            )
            timeline__future = _update_future(
                timeline__future,
                _t0,
                _v0,
                variable=var,
            )
        return timeline__future

    if timeline__past is not None:
        timeline__future = find_every_origin(timeline__past, timeline__future, o)

    else:
        _t0, _v0 = find(origin=origin)

        timeline__future = _update_future(timeline__future, _t0, _v0, variable=None)

    return timeline__future
