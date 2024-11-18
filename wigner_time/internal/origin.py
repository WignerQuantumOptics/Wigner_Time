"""
For manipulating column 'origins', particularly 'time' and 'value'.

This is important for inferring what the user means when they want to add rows to their dataframe and is especially important when it comes to chaining `ramp`s together.

The options are:
- "anchor"
- "variable"
- "time" (last time)
- "context" ?
- <float> (specific time)

In the future, there should be equivalent options for 'value'.
"""

from wigner_time.internal import dataframe as frame


def previous(
    timeline: frame.CLASS,
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
        return frame.row_from_max_column(tl__filtered)
    else:
        if not timeline[sort_by].is_monotonic_increasing:
            tl__filtered.sort_values(sort_by, inplace=True)
            return tl__filtered.iloc[index]
        else:
            return timeline.iloc[index]


def find(timeline: frame.CLASS, origin=None):
    """
    If origin is None, tries for anchor and then falls back to SOMETHING (TBC).
    """
    if origin is None:
        if (timeline["variable"] == "ANCHOR").any():
            origin = "anchor"
        else:
            origin = "time"
    match origin:
        case str() as text if "anchor" == text:
            row = previous(timeline, variable="ANCHOR")
        case str() as text if "variable" == text:
            # TODO: need extra argument or the decision has to be made further up the chain
            row = previous(timeline, variable="variable")
        case str() as text if "time" == text:
            row = previous(timeline)
        case str() as text:
            row = previous(timeline, variable=text)
        case float() as num:
            row = num
        case _:
            raise ValueError(
                "Unsupported option for 'origin' in `wigner_time.internal.origin.previous`."
            )
    return row
