# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
A device is represented by a dataframe that contains a variable (with a given unit) and a means, scalar or function, to convert this quantity to a voltage. It also specifies a minimum and maximum value for the variable, to be used in validation.

The unit range is used for conversion and the saftey range is for sanity checking the output.
"""

import numpy as np
import pandas as pd

from wignertime import variable as wt_variable
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util as wt_util

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


def new(*variable_toV_min_max) -> wt_frame.CLASS:
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

    # A purely digital apparatus has no devices at all, and that is a legitimate table
    # rather than a mistake -- `check_correspondence` expects exactly this where nothing
    # analogue is connected. Without the early return, `ensure_2d(())` yields one empty
    # row and the arity check rejects it.
    if not variable_toV_min_max:
        return wt_frame.new_schema([], SCHEMA)

    input4 = [process_input(args) for args in wt_util.ensure_2d(variable_toV_min_max)]

    # Narrowed from a bare `except:` that discarded the cause and reported only
    # "=== Input to 'device' not well formatted ===". It would also have swallowed the
    # name check below (A14). The same fault was fixed in `adwin/connection.py` on
    # 2026-09-11.
    try:
        new = wt_frame.new_schema(input4, SCHEMA)
    except (TypeError, ValueError, KeyError) as e:
        raise ValueError(
            "Input to `device.new` is not well formatted: {}. Each device is"
            " `[variable, to_V]`, `[variable, to_V, value__min]` or"
            " `[variable, to_V, value__min, value__max]`.".format(e)
        ) from e

    # Parity with `connection.new`, which has always refused a malformed name. Catches a
    # name that could not denote a variable at all; it cannot catch one that is well
    # formed but denotes nothing, which is what `check_correspondence` is for (A14).
    _ensure_valid_names(new)

    # convert dtype to float if possible (i.e. no functions)
    if pd.to_numeric(new["to_V"], errors="coerce").notna().all():
        new["to_V"] = new["to_V"].astype(float)

    return new


def _ensure_valid_names(devices):
    offenders = [v for v in devices["variable"] if not wt_variable.is_valid(v)]
    if offenders:
        raise ValueError(
            "Device name(s) {} do not follow the naming convention"
            " `<device>_<UID>(__<unit>)` set by `config.VARIABLE__REGEX`.".format(
                offenders
            )
        )
    return devices


def check_correspondence(connections, devices):
    """
    Checks that the `device` and `connection` tables describe the same apparatus.

    The two are deliberately separate — recalibrating a device and rewiring the apparatus
    are independent operations — but they are not independent *vocabularies*, and nothing
    used to notice when they drifted apart. A single transposed letter in a device name
    left the variable with no bounds at all, and `check_within_range` reads absent bounds
    as "a digital line" and skips it: 500 A passed on a coil declared +/-5 A (A14).

    Both directions raise, because each catches a different half of that:

    - an **analogue variable with a connection but no device** will be driven with neither
      a calibration nor limits;
    - a **device with no connection** is the other end of the same typo. It is harmless in
      itself, since nothing reads it, but tolerating it is what let the first case happen
      quietly.

    A digital line has no unit and needs no device, so it is not expected to have one.
    """
    names__connected = set(connections["variable"])
    names__calibrated = set(devices["variable"])

    analogue = {
        v for v in names__connected if wt_variable.unit(v) != "digital"
    } - names__calibrated
    orphaned = names__calibrated - names__connected

    if analogue or orphaned:
        raise ValueError(
            "\n".join(
                [
                    "The `device` and `connection` tables do not describe the same apparatus.",
                    "",
                    "  connected, analogue, but no device : {}".format(
                        sorted(analogue) or "none"
                    ),
                    "  a device, but nothing connected    : {}".format(
                        sorted(orphaned) or "none"
                    ),
                    "",
                    "An analogue channel without a device has neither a conversion nor"
                    " safety limits, and `check_within_range` cannot tell that from a"
                    " digital line. A device naming nothing connected is usually the"
                    " other end of the same misspelling.",
                ]
            )
        )
    return True


def add(timeline, devices):
    """
    For connecting device information to a `timeline`.
    """
    return wt_frame.join(timeline, devices)


def check_within_range(timeline, columns__bounds=["value__min", "value__max"]):
    """
    Considers whether the `timeline` `value`s fall inside device safety ranges (see SCHEMA). Raises an error if not, naming every variable that offends rather than only the first.

    A variable with no bounds at all is one that has no entry in `device`s – a digital line – and is skipped. A variable with only one bound is checked against that bound alone.

    "Typically" until 2026-09-21: an analogue variable could reach here unbounded through a mistyped device name, and this function could not tell that from a digital line, so it passed it. `check_correspondence`, called from `adwin.internal.add`, now rules that out on the path to hardware (A14).

    ASSUMES: That a `value` column is present, and that the timeline has already been joined to `device`s.
    """

    if not wt_frame.is_column_float(timeline["value"]):
        raise ValueError("Value column might not contain floats.")

    columns__missing = [c for c in columns__bounds if c not in timeline.columns]
    if columns__missing:
        raise ValueError(
            "Safety limits cannot be checked because the column(s) {} are absent. `device`s should be joined to the timeline before validation. Columns present: {}".format(
                columns__missing, list(timeline.columns)
            )
        )

    column__min, column__max = columns__bounds
    violations = []

    for variable, group in timeline.groupby("variable"):
        bound__min = group[column__min].iloc[0]
        bound__max = group[column__max].iloc[0]

        if wt_frame.isnull(bound__min) and wt_frame.isnull(bound__max):
            # No device entry for this variable, so there is nothing to check.
            continue

        if not wt_frame.isnull(bound__max):
            value__max = group["value"].max()
            if value__max > bound__max:
                violations.append((variable, value__max, "above", bound__max))

        if not wt_frame.isnull(bound__min):
            value__min = group["value"].min()
            if value__min < bound__min:
                violations.append((variable, value__min, "below", bound__min))

    if violations:
        raise ValueError(
            "The following variables were given values outside their device safety range. Please provide values only inside it:\n"
            + "\n".join("  {}: {} is {} the limit of {}".format(*v) for v in violations)
        )

    return True
