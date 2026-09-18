# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

"""

from copy import deepcopy
import numpy as np

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
    else:
        if not tl__filtered[sort_by].is_monotonic_increasing:
            tl__filtered.sort_values(sort_by, inplace=True)
            return tl__filtered.iloc[index]
        else:
            return tl__filtered.iloc[index]


def auto(timeline, origin, origin__defaults=wt_config.ORIGIN__DEFAULTS):
    """
    For choosing an origin, based on user input and defaults.


    NOTE: Assumes that origin__defaults is a list of pairs.
    """
    # TODO: Rename to be clearer

    if (origin is None) and (origin__defaults is not None):
        for od in origin__defaults:
            if "anchor" in np.array(od).flatten():
                if wt_anchor.is_available(timeline):
                    return od
                else:
                    continue
            else:
                return od
    else:
        return origin


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

    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))

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

        if label == "anchor" and wt_anchor.is_available(timeline):
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
        else:
            raise error__unsupported_option(label)

    o = sanitize_origin(timeline, origin)
    match o:
        case [float(), float()] | [float(), None] | [None, float()] as lst:
            tv = lst

        case [str(s1), None | float() as n1]:
            tv = [
                _previous_vt(*([timeline, "time"] + _to_col_var(timeline, s1, "time"))),
                n1,
            ]
        case [None | float() as n1, str(s1)]:
            tv = [
                n1,
                _previous_vt(
                    *([timeline, "value"] + _to_col_var(timeline, s1, "value")),
                    time__max=n1 + time__max__relative,
                ),
            ]
        case [str(s1), str(s2)] if (s1 == s2):
            # One label serving both slots, so it must satisfy the stricter vocabulary.
            tv = _previous_vt(
                *([timeline, "both"] + _to_col_var(timeline, s1, "value"))
            )
        case [str(s1), str(s2)]:
            t = _previous_vt(*([timeline, "time"] + _to_col_var(timeline, s1, "time")))
            tv = [
                t,
                _previous_vt(
                    *([timeline, "value"] + _to_col_var(timeline, s2, "value")),
                    time__max=t + wt_config.TIME_RESOLUTION + time__max__relative,
                ),
            ]

        case _:
            raise error__unsupported_option(o)
    return tv


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

        for var in timeline__future["variable"].unique():

            _t0, _v0 = find(
                timeline__past,
                origin=[var if e == "variable" else e for e in input],
                time__max__relative=timeline__future["time"].min(),
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
