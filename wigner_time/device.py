"""
A device is represented by a dataframe that contains a `unit_range` and (optionally) a `safety_range`.

The unit range is used for conversion and the saftey range is for sanity checking the output.
"""

import numpy as np
from wigner_time.internal import dataframe as wt_frame


# ======================================================================
_SCHEMA = {
    "variable": str,
    "unit__min": float,
    "unit__max": float,
    "safety__min": float,
    "safety__max": float,
}
# ======================================================================


def check_ranges(devices):
    """
    Takes a dataframe of devices (value ranges) and checks whether or not the safety range is 'inside' the value range. If so, return `devices` unchanged; if not, raise an error.
    """

    mask = np.logical_and(
        devices["unit__min"] <= devices["safety__min"],
        devices["safety__max"] <= devices["unit__max"],
    )

    if mask.all():
        return devices
    else:
        raise ValueError(f"Safety values out of range: {devices[~mask]}")


def new(*variable_unit_safety) -> wt_frame.CLASS:
    """
    Convenience for creating a table that specifies the ranges of devices ('variable', 'unit__min', 'unit__max', 'safety__min' and 'safety__max' columns). The 'unit' limits represent how the specified quantities will map onto the resultant controlling voltages. The 'safety' limits outline the range that a user should be allowed to specify in practice. This will allow for error-checking before passing values to real devices.

    `variable`s are used as the means by which `connection`s and `device`s can be later connected.

    If the 'safety...' columns are not specified, then they will be copied from the 'unit...' entries.

    vmcs:
    e.g.
        "coil_compensationX__A", -3, 3, -2.5, 2.5,
    or
        ["coil_compensationY__A", -3, 3, -2.5, 2.5],
        ["coil_MOTlower__A", -5, 5],
        ["coil_MOTupper__A", -5, 5],
    """

    input5 = [
        np.concatenate([sub, sub[-2:]]) if len(sub) == 3 else sub
        for sub in np.atleast_2d(variable_unit_safety)
    ]

    try:
        new = wt_frame.new_schema(input5, _SCHEMA)
    except:
        raise ValueError("=== Input to 'device' not well formatted ===")

    return check_ranges(new)


def add(timeline, devices):
    """
    For connecting device information to a `timeline`.
    """
    return wt_frame.join(timeline, devices)
