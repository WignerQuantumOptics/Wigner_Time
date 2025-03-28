"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

"""

# TODO:
# - Rename this file (and relevant functions) to something to do with query/history?
# - dictionary option for origin (i.e. different origin for different variables?)

from copy import deepcopy
import numpy as np

from wigner_time import config as wt_config
from wigner_time.config import wtlog
from wigner_time import util as wt_util
from wigner_time import anchor as wt_anchor
from wigner_time.internal import dataframe as wt_frame
from wigner_time.internal import origin as wt_origin

###############################################################################
#                                  CONSTANTS                                   #
###############################################################################

# TODO: These could be moved to the `config` module
_ORIGINS = ["anchor", "last", "variable"]
"These origin labels are reserved for interpretation by the package. Other origin strings will be interpreted as`variable`s."


def error__unsupported_option(origin):
    return ValueError(
        f"{origin} is an unsupported option for 'origin' in `wigner_time.internal.origin.find`. Check the formatting and whether this makes sense for your current timeline. \n\n If you feel like this option should be supported then don't hesitate to get in touch with the maintainers."
    )


def error__timeline(origin):
    return ValueError(f"Timeline not specified, but necessary for origin={origin}.")


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

    Example origins:
    - [0.0,0.0]
    - 0.0
    - "anchor"
    - ["anchor", 0.0]
    - "last" (The row highest in time)
    - "AOM_shutter" (A variable name that is present in the dataframe)
    - "init" (A context name that is present in the dataframe)
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

    def _to_col_var(timeline, label):
        if label == "anchor" and wt_anchor.is_available(timeline):
            return ["variable", label__anchor]
        elif label == "last":
            return ["variable", None]
        elif _is_available__variable(label):
            return ["variable", label]
        elif _is_available__context(label):
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
                _previous_vt(*([timeline, "time"] + _to_col_var(timeline, s1))),
                n1,
            ]
        case [None | float() as n1, str(s1)]:
            tv = [
                n1,
                _previous_vt(
                    *([timeline, "value"] + _to_col_var(timeline, s1)),
                    time__max=n1 + time__max__relative,
                ),
            ]
        case [str(s1), str(s2)] if (s1 == s2):
            tv = _previous_vt(*([timeline, "both"] + _to_col_var(timeline, s1)))
        case [str(s1), str(s2)]:
            t = _previous_vt(*([timeline, "time"] + _to_col_var(timeline, s1)))
            tv = [
                t,
                _previous_vt(
                    *([timeline, "value"] + _to_col_var(timeline, s2)),
                    time__max=t + time__max__relative,
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

            _t0, _v0 = wt_origin.find(
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
        _t0, _v0 = wt_origin.find(origin=origin)

        _update_future(timeline__future, _t0, _v0, variable=None)

    return timeline__future
