# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Utility functions related to setting, finding and querying anchors in a timeline.
"""

from typing import Callable

from wignertime.internal import tags as wt_tags
from wignertime.internal import dataframe as wt_frame

LABEL__ANCHOR = wt_tags.LABEL__ANCHOR


def mask(timeline, context=None):
    """
    A collection that identifies whether or not each row in the dataframe represents an anchor.
    """
    msk = timeline["variable"].str.startswith(LABEL__ANCHOR)

    if context is not None:
        msk &= timeline["context"] == context
    return msk


def is_available(timeline, context=None) -> bool:
    if timeline is None:
        return False
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
