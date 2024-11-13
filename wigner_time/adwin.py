# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from copy import deepcopy

import numpy as np

from wigner_time import timeline as tl
from wigner_time import conversion as conv
from wigner_time import variable as var
from wigner_time.internal import dataframe as frame


"""
Represents the key ADwin settings for the given machine.

These should be loaded by the ADwin system during initialization. The dictionary of settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.
"""
specifications_default = {
    "device_001": {
        "cycle_period__normal": 5e-6,
        "module_001": {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
        "module_002": {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
        "module_003": {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
        "module_004": {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
    },
}

special_contexts = {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31}


def remove_unconnected_variables(df, connections):
    """
    Purges the given timeline of any `variable`s that do not have a matching `connection`.

    NOTE: Assumes df and connections are both pd.DataFrame-like things
    """

    df = deepcopy(df)
    _disconnections = [
        v for v in df["variable"].unique() if v not in connections["variable"].unique()
    ]

    for v in _disconnections:
        df.drop(df[df.variable == v].index, inplace=True)

    return df


def add_cycle(
    df,
    specifications=specifications_default,
    special_contexts=special_contexts,
    device="device_001",
):
    """
    Inserts a new `cycle` column into the timeline as a conversion of the `time` column into 'number of cycles'.

    Parameters:
    - df: DataFrame containing the experimental data.
    - specifications: Dictionary with device-specific configuration, must contain cycle period.
    - special_contexts: Dictionary with context-specific overrides for cycle values.
    - device: Device name to use for cycle period in specifications.

    Raises:
    - ValueError if required columns are missing or if cycle period is not found for specified device.
    """
    # Check if `time` column is present
    if "time" not in df.columns:
        raise ValueError(
            f"`time` column not found. Columns present: {list(df.columns)}"
        )

    # Ensure device-specific cycle period is available
    try:
        cycle_period = specifications[device]["cycle_period__normal"]
    except KeyError:
        raise ValueError(
            f"`cycle_period__normal` not found in specifications for {device}."
        )

    # Calculate cycles and handle special contexts
    df["cycle"] = np.round(df["time"].values / cycle_period).astype(np.int64)

    # Apply special context cycles
    for context, cycle_value in special_contexts.items():
        if context in df["context"].values:
            df.loc[df["context"] == context, "cycle"] = cycle_value

    return df


def initialize_ADwin(m, output):
    """
    NOTE: Stateful.
    General setup of the *system*, rather than the specific experimental project.
    """
    # TODO: Should we prepare all of the possible variables or does this waste memory?

    time_end__cycles = max(
        max([t[0] for t in output[0]]), max([t[0] for t in output[1]])
    )
    print(
        "time_end: {}s".format(
            time_end__cycles
            * specifications_default["device_001"]["cycle_period__normal"]
        )
    )

    m.Set_Par(1, time_end__cycles)
    m.Set_Par(2, len(output[0]))
    m.Set_Par(3, len(output[1]))

    m.SetData_Long([a[0] for a in output[0]], 10, 1, len(output[0]))
    m.SetData_Long([a[1] for a in output[0]], 11, 1, len(output[0]))
    m.SetData_Long([a[2] for a in output[0]], 12, 1, len(output[0]))
    m.SetData_Long([a[3] for a in output[0]], 13, 1, len(output[0]))

    m.SetData_Long([d[0] for d in output[1]], 20, 1, len(output[1]))
    m.SetData_Long([d[1] for d in output[1]], 22, 1, len(output[1]))
    m.SetData_Long([d[2] for d in output[1]], 23, 1, len(output[1]))

    return m


def check_safety_range(df):
    """
    Checks whether the values sent to this device fall inside its safety range.
    """
    for variable, group in df.groupby("variable"):
        if group["safety_range"].any():
            # print(group)
            if max(group["value"].values) > max(group["safety_range"].values[0]):
                raise ValueError(
                    "{} was given a value of {}, which is higher than its maximum safe limit. Please provide values only inside it's safety range.".format(
                        variable, max(group["value"].values)
                    )
                )
            elif min(group["value"].values) < min(group["safety_range"].values[0]):
                raise ValueError(
                    "{} was given a value of {}, which is lower than its minimum safe limit. Please provide values only inside it's safety range.".format(
                        variable, min(group["value"].values)
                    )
                )
            else:
                pass


def add_linear_conversion(df, unit, separator="__", column__new="value__digits"):
    """
    Performs a linear conversion, according to the associated bounding values ('unit_range'), and adds the resulting values as another column, 'value__digits'.

    unit: string.
    """
    dff = deepcopy(df)
    mask = dff["variable"].str.contains(separator + unit + "$")

    if mask.any():
        unit_range = dff.loc[mask, "unit_range"].iloc[0]

        dff.loc[dff.index[mask], column__new] = conv.unit_to_digits(
            dff.loc[mask, "value"], unit_range=unit_range
        )
    return dff


def add(df, adwin_connections, devices, specifications=specifications_default):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Digital: module 1
    Analogue otherwise
    """
    # TODO: parameterize the column names
    # TODO: Add vectorization to the python overview talk
    # TODO: Anything that is not voltage should be converted using a functor from the devices layer, which should be a set of conversion functors from units like A, MHz
    #       (this might actually be an overkill: as long as the device is linear, supplying unit_range is sufficient for the conversion, so the functor is necessary only for nonlinear devices)

    dff = df.join(
        adwin_connections.set_index("variable"),
        on="variable",
    )

    dff = dff.join(
        devices.set_index("variable"),
        on="variable",
    )

    dff = dff.sort_values(by=["time"], ignore_index=True)

    for variable, group in dff.groupby("variable"):
        if (dff["variable"].str.contains("__A", regex=False)).any():
            mask_current = group["variable"].str.contains("__A", regex=False)

            # Check if the variable contains "__A" in its name
            if mask_current.any():
                # Get the unit_range from the rows with "__A" in their name
                unit_range = group.loc[mask_current, "unit_range"].iloc[0]

                dff.loc[group.index[mask_current], "value_digits"] = (
                    conv.unit_to_digits(
                        group.loc[mask_current, "value"], unit_range=unit_range
                    )
                )

        if (dff["variable"].str.contains("__V", regex=False)).any():
            mask_voltage = group["variable"].str.contains("__V", regex=False)

            # Check if the variable contains "__V" in its name
            if mask_voltage.any():
                # Get the unit_range from the rows with "__V" in their name
                unit_range = group.loc[mask_voltage, "unit_range"].iloc[0]

                dff.loc[group.index[mask_voltage], "value_digits"] = (
                    conv.unit_to_digits(
                        group.loc[mask_voltage, "value"], unit_range=unit_range
                    )
                )

        if (dff["variable"].str.contains("__MHz", regex=False)).any():
            mask_frequency = group["variable"].str.contains("__MHz", regex=False)

            # Check if the variable contains "__MHz" in its name
            if mask_frequency.any():
                # Get the unit_range from the rows with "__MHz" in their name
                unit_range = group.loc[mask_frequency, "unit_range"].iloc[0]

                dff.loc[group.index[mask_frequency], "value_digits"] = (
                    conv.unit_to_digits(
                        group.loc[mask_frequency, "value"], unit_range=unit_range
                    )
                )

    mask = dff["module"] != 1

    dff.loc[~mask, "value_digits"] = round(dff["value"])

    check_safety_range(dff)

    return tl.sanitize(add_cycle(dff, specifications))


def modules_digital(specifications):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.
    """

    # TODO: Check for modules (from dict) that have some characteristic (no voltage range etc?).

    return [1]


def to_tuples(df, cols=["cycle", "module", "channel", "value_digits"]):
    return [tuple([np.int64(i) for i in x]) for x in df[cols].values]


def output(df, specifications=specifications_default):
    """
    Takes a dataframe of the experimental run and converts the result to a PyADwin 'Output' class.


    return [[(cycle, module, channel, value), ...],
    [(cycle, channel, value), ...]]
    """
    # TODO: ensure digital outputs are integers
    # TODO: sort table by cycle before export
    # As defined in PyAdwin.py
    # TODO: use the same format for analogue and digital (requires change at the ADwin side)

    mods_digital = modules_digital(specifications)
    mods_analogue = [x for x in df["module"].unique() if x not in mods_digital]

    return [
        to_tuples(df.query("module in {}".format(mods_analogue))),
        to_tuples(
            df.query("module in {}".format(mods_digital)),
            cols=["cycle", "channel", "value_digits"],
        ),
    ]


def to_adwin(df, connections, devices, adwin_settings=specifications_default):
    """
    Convenience for converting a Wigner timeline (DataFrame) to an ADwin-compatible list of tuples.

    This takes an operation-layer timeline, adds the columns necessary for an ADwin conversion, based on the supplied or default specifications, and then converts the relevant columns according to `adwin.output`, i.e.  [[(cycle, module, channel, value), ...],
    [(cycle, channel, value), ...]].
    """

    return output(
        add(df, connections, devices, specifications=specifications_default),
        specifications=specifications_default,
    )


def sanitize_special_contexts(timeline, special_contexts=special_contexts):
    """
    that there isn't more than one entry for a given variable inside special contexts. This is necessary as there is no concept of 'time' inside the special contexts defined for ADwin.
    """
    df = timeline[timeline["context"].isin(special_contexts)]
    df_N = df.groupby(["variable", "context"])["value"].count()
    duplicates = df_N[df_N > 1].reset_index()
    duplicates.columns = ["variable", "context", "variable_occurences"]

    if duplicates.empty:
        return timeline
    else:
        raise ValueError(
            "The same variable has more than one value inside a special context. This will not work as expected on export to ADwin as these special contexts have no concept of time. For details,  see the duplicate information: "
            + str(duplicates)
        )


def sanitize_types(timeline):
    return timeline.astype(
        {
            "module": int,
            "channel": int,
            "cycle": np.int64,
            "value_digits": np.int64,
        }
    )


def sanitize(timeline):
    """
    Includes ADwin-specific methods ontop of the basic timeline sanitization for removing unnecessary points and raising errors on illogical input.

    """
    return sanitize_special_contexts(sanitize_types(tl.sanitize(timeline)))


# ======
# SCRIPT
# ======
if __name__ == "__main__":
    import pandas as pd

    import importlib
