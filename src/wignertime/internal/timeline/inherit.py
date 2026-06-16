from copy import deepcopy
import pandas as pd

from wignertime.internal import origin as wt_origin

# TODO: Fix dependance on pandas


def _mask__no_context(timeline):
    if "context" in timeline.columns:
        mask = timeline["context"] == ""
    else:
        mask = pd.Series(True, index=timeline.index)

    return mask


def context(
    timeline, timeline__previous, context=None, is_inPlace=True, time__max=None
):
    """
    Updates the context, taken from previous values where unspecified.

    Allows for situations where the new timelines are inserted at earlier times.
    """
    if is_inPlace:
        df = timeline
    else:
        df = deepcopy(timeline)

    if (timeline__previous is not None) and (context is None):
        if time__max == "min":
            time__max = timeline["time"].min()

        df.loc[_mask__no_context(timeline), "context"] = wt_origin.previous(
            timeline__previous, time__max=time__max
        )["context"]
        return df

    elif (timeline__previous is None) and (context is not None):
        df.loc[_mask__no_context(timeline), "context"] = context

    else:
        return timeline
