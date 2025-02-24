"""
A device is represented by a dataframe that contains a unit range and (optionally) a safety range.

The unit range is used for conversion and the saftey range is for sanity checking the output.
"""

import numpy as np
from wigner_time.internal import dataframe as wt_frame
from collections.abc import Callable


# ======================================================================
_SCHEMA = {
    "variable": str,
    "unit__min": float,
    "unit__max": float,
    "safety__min": float,
    "safety__max": float,
}

_SCHEMA2 = {
    "variable": str,
    "range__min": float,
    "range__max": float,
    "volts_per_unit": float | Callable,
}
# ======================================================================


def _check_ranges(devices):
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


def new2(*variable_factor_safety) -> wt_frame.CLASS:
    """
    NOTE: WIP!!!

    IDEA:
    - factor can replace unit range (i.e. Volts/Unit)?
    - factor can be a nonlinear function? (conversion branches on this)
    - possible for there to be no safety range (clipped at the ADwin-side)
    - will this interfere with `ramp`s? (probably not, if we use a separate column, i.e. 'conversion' or something)

    - all device conversions to voltages? The conversion from voltage to ADC digits can then be done on everything in batch (using the ADwin/backend layer)?
    """

    input5 = [
        np.concatenate([sub, sub[-2:]]) if len(sub) == 3 else sub
        for sub in np.atleast_2d(variable_factor_safety)
    ]

    try:
        new = wt_frame.new_schema(input5, _SCHEMA)
    except:
        raise ValueError("=== Input to 'device' not well formatted ===")

    return _check_ranges(new)


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

    return _check_ranges(new)


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
        if group["safety__max"].any():
            if max(group["value"].values) > group["safety__max"].values[0]:
                raise ValueError(
                    "{} was given a value of {}, which is higher than its maximum safe limit. Please provide values only inside it's safety range.".format(
                        variable, max(group["value"].values)
                    )
                )
            elif min(group["value"].values) < group["safety__min"].values[0]:
                raise ValueError(
                    "{} was given a value of {}, which is lower than its minimum safe limit. Please provide values only inside it's safety range.".format(
                        variable, min(group["value"].values)
                    )
                )
            else:
                pass
