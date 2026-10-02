# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Utility functions related to setting, finding and querying anchors in a timeline.
"""

# TODO: Not sure if this should be a separate file or not.

from typing import Callable

import numpy as np

from wignertime import config as wt_config
from wignertime.internal import dataframe as wt_frame

LABEL__ANCHOR = wt_config.LABEL__ANCHOR


def mask(timeline, context=None):
    """
    A collection that identifies whether or not each row in the dataframe represents an anchor.
    """
    msk = np.array(
        [
            isinstance(v, str) and v.startswith(LABEL__ANCHOR)
            for v in wt_frame.column(timeline, "variable")
        ],
        dtype=bool,
    )

    if context is not None:
        msk &= wt_frame.column(timeline, "context") == context
    return msk


def is_available(timeline, context=None) -> bool:
    if timeline is None:
        return False
    return bool(mask(timeline, context=context).any())


def last(timeline, context=None):
    """
    The last anchor variable available, optionally filtered by context.
    """
    if timeline is None:
        return None

    df_filt = wt_frame.filter(timeline, mask(timeline, context))

    if not wt_frame.is_empty(df_filt):
        return wt_frame.row_from_max_column(df_filt)["variable"]
    else:
        return None
