# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import re
from typing import Sequence

from munch import Munch, DefaultMunch
import pandas as pd

# =====================================================================
# CLASSES
# =====================================================================
"""
The choice made here is to model our ADwin connections as little more than dictionaries of information. This allows for the least amount of coupling with other implementations. Rather than plain dictionaries, we use the 'munch' library for the nice attribute features e.g. 'd.module = 1'.

The reason for not simply using a dictionary (rather than an object) is to allow for the insertion of default values and easy instantiation of multiple objects of the same type.
TODO: I'm not sure about this anymore - consider it subject to review! Maybe we should avoid dictionaries entirely and just use DataFrame objects? This might be expensive memory-wise?

Once the connections have associated functions, then consider putting them within their own namespaces. Functions that manipulate the values should be as independent as possible however.

TODO:
reset the default values
"""


def connection(*vmcs, type="dataframe") -> pd.DataFrame | Sequence[dict] | dict | None:
    """
    Working principle is that variables have the form 'context_equipment__SIunit' or 'context_equipment'. In the latter case, the 'variable' is taken to be digital (unitless).

    returns either a DataFrame or a list of dicts based on type="dataframe" or "dict"

    Input:
    i.e.
    [[var001, 1, 1],[var002, 1, 2],...]

    WARN:
    variable output (Iterable or not)
    """
    # TODO: Check that the input is sensible (integers where expected etc.)
    # TODO: Update connections so that they always return a dataframe-like thing rather than a dictionary (don't be confusing!).

    if (len(vmcs) > 0) and (len(vmcs[0])) == 3 and type == "dataframe":
        return pd.DataFrame.from_records(
            [connection(vmc[0], vmc[1], vmc[2], type="dict") for vmc in vmcs]
        )
    elif (len(vmcs) > 0) and (len(vmcs[0])) == 3 and type == "dict":
        return [connection(vmc[0], vmc[1], vmc[2], type="dict") for vmc in vmcs]
    elif (
        (len(vmcs) == 3)
        and not all(map(lambda x: hasattr(x, "__iter__"), vmcs))
        and type == "dataframe"
    ):
        return pd.DataFrame([Munch(variable=vmcs[0], module=vmcs[1], channel=vmcs[2])])
    elif (
        (len(vmcs) == 3)
        and not all(map(lambda x: hasattr(x, "__iter__"), vmcs))
        and type == "dict"
    ):
        return Munch(variable=vmcs[0], module=vmcs[1], channel=vmcs[2])
    else:
        print("input to connection not well formatted")
        return None


def parse(variable: str) -> dict:
    ceu = re.split("_+", variable)
    if len(ceu) > 1:
        try:
            unit = ceu[2]
        except:
            unit = None
    else:
        raise ValueError("problem with variable name")

    return Munch(context=ceu[0], equipment=ceu[1], unit=unit if unit else None)


def is_valid(variable: str) -> bool:
    c, e, u = parse(variable)
    if c and e:
        return True
    else:
        return False
