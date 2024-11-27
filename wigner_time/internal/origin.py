"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

"""

# TODO:
# - "variable" flag (i.e. find the previous occurence of this particular variable)
# - Rename this file (and relevant functions) to something to do with query/history?
# - dictionary option for origin (i.e. different origin for different variables?)
# - "context" (Should we support this?)

from copy import deepcopy
from wigner_time import util as wt_util
from wigner_time.internal import dataframe as wt_frame
from wigner_time.internal import origin as wt_origin

_ORIGINS = ["anchor", "last", "variable"]
"These origin labels are reserved for interpretation by the package."
_LABEL__ANCHOR = "ANCHOR"


def previous(
    timeline: wt_frame.CLASS,
    variable=None,
    column="variable",
    sort_by=None,
    index=-1,
):
    """
    Returns a row from the previous timeline. By default, this is done by finding the highest value for time and returning that row. If `sort_by` is specified (e.g. 'time'), then the dataframe is sorted and then the row indexed by `index` is returned.

    Raises ValueError if the specified variable, or timeline, doesn't exist.
    """
    if variable is not None:
        tl__filtered = timeline[timeline[column] == variable]
        if tl__filtered.empty:
            raise ValueError("Previous {} not found".format(variable))
    else:
        tl__filtered = timeline

    if sort_by is None:
        return wt_frame.row_from_max_column(tl__filtered)
    else:
        if not timeline[sort_by].is_monotonic_increasing:
            tl__filtered.sort_values(sort_by, inplace=True)
            return tl__filtered.iloc[index]
        else:
            return timeline.iloc[index]


def find(
    timeline,
    origin=None,
    label__anchor=_LABEL__ANCHOR,
):
    """
    Returns a time-value pair, according to the choice of origin.

    Often, `None` will be returned for a value as it would be presumptuous to assume the same value origin for all devices.

    Example origins:
    - [0.0,0.0]
    - 0.0
    - "anchor"
    - ["anchor", 0.0]
    - "last" (The row highest in time)
    - "...AOM_shutter..." (A variable name that is present in the dataframe)
    """
    _is_available__anchor = (
        (timeline["variable"] == label__anchor).any() if timeline is not None else False
    )

    def _is_available__variable(var):
        return (timeline["variable"] == var).any() if (var is not None) else None

    """
    Falls back to last time entry if anchor is not available.
    TODO:
    - Is this a good idea?
    - More meaningful error if anchor is not available
    - Should anchor be 'hardcoded' or should we just use it as any other variable name?
    """
    if origin is None:
        if _is_available__anchor:
            origin = "anchor"
        else:
            origin = "last"

    o = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))

    error__unsupported_option = ValueError(
        "Unsupported option for 'origin' in `wigner_time.internal.origin.find`. Check the formatting and whether this makes sense for your current timeline. \n\n If you feel like this option should be supported then don't hesitate to get in touch with the maintainers."
    )
    error__timeline = ValueError(
        "Timeline not specified, but necessary for this type of origin."
    )

    if len(o) != 2:
        raise error__unsupported_option

    print('===')
    print(o[0], o[1])
    print(_is_available__variable(o[0]))
    print(_is_available__variable(o[1]))
    print('===')
    match o:
        case [float(), float()] | [float(), None] | [None, float()] as lst:
            tv = lst

        case [a, None | float() as b]:
            if timeline is None:
                raise error__timeline
            match a:
                case str(text) if (text == "anchor") and _is_available__anchor:
                    tv = [
                        previous(timeline, variable=label__anchor).at["time"],
                        b,
                    ]

                case str(text) if "last" == text:
                    tv = [previous(timeline).at["time"], b]

                case str(text) if _is_available__variable(text):
                    tv = [previous(timeline, variable=text).at["time"], b]
                case _:
                    raise error__unsupported_option

        case [str(t1), str(t2)] if (t1 == t2) and _is_available__variable(t1):
            tv = previous(timeline, variable=t1)[["time", "value"]].values

        case [str(t1), str(t2)] if (
            _is_available__variable(t1) and _is_available__variable(t1)
        ):
            tv = [
                previous(timeline, variable=t1).at["time"],
                previous(timeline, variable=t2).at["value"],
            ]

        case _:
            raise error__unsupported_option
    return tv


def update(
    timeline__present: wt_frame.CLASS,
    timeline__past: wt_frame.CLASS | None,
    origin=None,
) -> wt_frame.CLASS:
    # TODO:
    # - Move numerical origin checks here?
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

    if timeline__past is not None:
        match origin:
            case "variable" | ["variable"]:
                for var in timeline__future["variable"]:
                    _t0, _v0 = wt_origin.find(timeline__past, origin=var)
                    timeline__future = _update_future(
                        timeline__future, _t0, _v0, variable=var
                    )

            case ["variable", "variable"]:
                for var in timeline__future["variable"]:
                    _t0, _v0 = wt_origin.find(timeline__past, origin=[var, var])
                    timeline__future = _update_future(
                        timeline__future, _t0, _v0, variable=var
                    )
            case ['ANCHOR', 'variable' ]:
                for var in timeline__future["variable"]:
                    print(f'{var}: GOT HERE')
                    _t0, _v0 = wt_origin.find(timeline__past, origin=['ANCHOR', var])
                    print(f'found anchor!===')
                    timeline__future = _update_future(
                        timeline__future, _t0, _v0, variable=var
                    )

            case ['variable', 'ANCHOR']:
                # TODO: Can combine this with the above?
                for var in timeline__future["variable"]:
                    _t0, _v0 = wt_origin.find(timeline__past, origin=[var,'ANCHOR'])
                    timeline__future = _update_future(
                        timeline__future, _t0, _v0, variable=var
                    )

            case _:
                _t0, _v0 = wt_origin.find(timeline__past, origin=origin)

                if _t0 is not None:
                    timeline__future["time"] += _t0
                if _v0 is not None:
                    timeline__future["value"] += _v0

    else:
        if origin is not None:
            _t0, _v0 = wt_origin.find(None, origin=origin)
        else:
            _t0, _v0 = [None, None]

        if _t0 is not None:
            timeline__future["time"] += _t0
        if _v0 is not None:
            timeline__future["value"] += _v0

    return timeline__future
