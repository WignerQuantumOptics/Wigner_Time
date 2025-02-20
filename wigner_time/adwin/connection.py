# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)


"""
The choice made here is to model our ADwin connections as little more than tables of data (DataFrames). This allows for the least amount of coupling with other implementations an convenience of interaction with timelines etc.

What follows are simply convenience functions to make the creation easier.
"""
import re
from munch import Munch
import pandas as pd
import numpy as np

from wigner_time.internal import dataframe as wt_frame

# TODO: check connection names are valid on creation

# ======================================================================
_SCHEMA = {"variable": str, "module": int, "channel": int}
# ======================================================================


def parse(variable: str) -> dict | None:
    match = re.match(r"^([^_]+)_([^_]+)(?:__([^_]))?$", variable)

    if match is not None:
        e, c, u = match.groups()
        return Munch(context=e, equipment=c, unit=u if u else None)
    else:
        return None


def is_valid(variable: str) -> bool:
    ecu = parse(variable)
    if ecu is not None:
        return True
    else:
        return False


def new(*variable_module_channel) -> pd.DataFrame:
    """
    Convenience for creating a table with 'variable', 'module' and 'channel' columns.

    'variable's have the form 'context_equipment__unit' or 'context_equipment'. In the latter case, the 'variable' is taken to be digital (unitless).

    vmcs:
    e.g.
        "AOM_MOT__V", 1, 1
    or
        ["shutter_MOT", 1, 11],
        ["shutter_repump", 1, 12],
        ["shutter_imaging", 1, 13],
    """

    try:
        return wt_frame.new_schema(np.atleast_2d(variable_module_channel), _SCHEMA)
    except:
        raise ValueError("=== Input to 'connection' not well formatted ===")
