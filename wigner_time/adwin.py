# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from copy import deepcopy

from wigner_time import timeline as tl
from wigner_time import conversion as conv


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


def add_cycles(
    df,
    specifications=specifications_default,
    special_contexts={"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31},
):
    """
    Inserts a new `cycle` column into the timeline, that is a conversion of the `time` column into 'number of cycles'.

    The `special_contexts` dictionary is used to overwrite the timing conversion, to allow the user to utilise ADwin's special features, e.g. to allow initialization and finalization to be carried out outside of the usual cycle progression.
    NOTE: The same convention has to be implemented on both the Python and ADwin side.

    ASSUMES: That the whole experimental run starts at t=0.

    """
    # TODO: Implement the special contexts more efficiently

    if "time" in df.columns:
        dff = deepcopy(df)
        dff["cycle"] = (
            df["time"].values / specifications["device_001"]["cycle_period__normal"]
        )

        for context in special_contexts:
            dff.loc[dff["context"] == context, "cycle"] = special_contexts[context]

        return dff.astype(
            {
                "cycle": int,
            },
            errors="raise",
        )
    else:
        raise Exception("No `time` column.")


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

    return tl.sanitize(add_cycles(dff, specifications))


def modules_digital(specifications):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.
    """

    # TODO: Check for modules (from dict) that have some characteristic (no voltage range etc?).

    return [1]


def to_tuples(df, cols=["cycle", "module", "channel", "value_digits"]):
    return [tuple([int(i) for i in x]) for x in df[cols].values]


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
