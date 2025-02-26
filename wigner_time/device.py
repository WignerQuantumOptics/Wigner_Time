"""
A device is represented by a dataframe that contains a unit range and (optionally) a safety range.

The unit range is used for conversion and the saftey range is for sanity checking the output.
"""

import numpy as np
import pandas as pd

from wigner_time.internal import dataframe as wt_frame
from wigner_time import util as wt_util

from collections.abc import Callable


# ======================================================================
SCHEMA = {
    "variable": str,
    "to_V": object,
    # float | Callable,
    "value__min": float,
    "value__max": float,
}
SCHEMA__expanded = {
    "variable": str,
    "to_V": float,
    "value__min": float,
    "value__max": float,
}

# ======================================================================


def new(*variable_factor_min_max) -> wt_frame.CLASS:
    """
    Convenience for creating a table that specifies the conversion and range of device values ('variable', 'to_V', 'value__min' and 'value__max' columns). 'to_V' specifies the conversion and can either be a floating point factor or a function that takes the output from the givin units to a Voltage. The min-max limits outline the range that a user is allowed to specify (and will be validated before output). This allows for error-checking before passing values to real devices.

    `variable`s are used as the means by which `connection`s and `device`s can be later connected.

    If the 'value__min/max' columns are not specified, then they will be taken as +/- infinity.

    vfmm:
    e.g.
        "coil_compensationX__A", 3/10., -3.0, 3.0,
    or
        ["coil_compensationY__A", 0.333, -3.0],
        ["coil_MOTlower__A", <function>, -5, 5],
        ["coil_MOTupper__A", lambda x: x - 100,-5, 5],
    """
    # TODO:
    # - allow for automatic conversion for Voltages?

    def process_input(args):
        l = len(args)
        if l == 2:
            return np.concatenate([args, [-np.inf, np.inf]])
        elif l == 3:
            return np.concatenate([args, [np.inf]])
        elif l == 4:
            return args  # No changes
        else:
            raise ValueError(
                f"Invalid list of devices {args}: the number of arguments should be less than 5."
            )

    input4 = [
        process_input(args) for args in wt_util.ensure_2d(variable_factor_min_max)
    ]

    try:
        new = wt_frame.new_schema(input4, SCHEMA)

        # convert dtype to float if possible (i.e. no functions)
        if pd.to_numeric(new["to_V"], errors="coerce").notna().all():
            new["to_V"] = new["to_V"].astype(float)

    except:
        raise ValueError("=== Input to 'device' not well formatted ===")

    return new


def add(timeline, devices):
    """
    For connecting device information to a `timeline`.
    """
    return wt_frame.join(timeline, devices)


def check_safety_range(timeline):
    """
    Checks whether the `timeline` `value`s fall inside device safety ranges.
    """
    for variable, group in timeline.groupby("variable"):
        if group["value__max"].any():
            if max(group["value"].values) > group["value__max"].values[0]:
                raise ValueError(
                    "{} was given a value of {}, which is higher than its maximum safe limit. Please provide values only inside it's safety range.".format(
                        variable, max(group["value"].values)
                    )
                )
            elif min(group["value"].values) < group["value__min"].values[0]:
                raise ValueError(
                    "{} was given a value of {}, which is lower than its minimum safe limit. Please provide values only inside it's safety range.".format(
                        variable, min(group["value"].values)
                    )
                )
            else:
                pass
