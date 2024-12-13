"""
Utility functions related to setting, finding and querying anchors in a timeline.
"""

# TODO: Not sure if this should be a separate file or not.

from typing import Callable

from wigner_time import config as wt_config
from wigner_time.internal import dataframe as wt_frame

LABEL__ANCHOR = wt_config.LABEL__ANCHOR


def mask(timeline, context=None):
    """
    A collection that identifies whether or not each row in the dataframe represents an anchor.
    """
    msk = timeline["variable"].str.startswith(LABEL__ANCHOR)

    if context is not None:
        msk &= timeline["context"] == context
    return msk


def is_available(timeline, context=None) -> bool:
    return (mask(timeline, context=context)).any()


def last(timeline, context=None):
    """
    The last anchor variable available, optionally filtered by context.
    """
    if timeline is None:
        return None

    df_filt = timeline[mask(timeline, context)]

    if not df_filt.empty:
        return df_filt.loc[df_filt["time"][::-1].idxmax(), "variable"]
    else:
        return None
