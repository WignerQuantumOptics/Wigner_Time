# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from copy import deepcopy

import funcy
import numpy as np

from wigner_time import timeline as tl
from wigner_time import conversion as conv
from wigner_time.internal import dataframe as wt_frame


"""
Represents the key ADwin settings for the given machine.

These should be loaded by the ADwin system during initialization. The dictionary of settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.
"""
SPECIFICATIONS__DEFAULT = {
    "device_001": {
        "cycle_period__normal__us": 5e-6,
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
# TODO: Rather than naming the above with numbers, this could be a list of dicts.

CONTEXTS__SPECIAL = {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1}
"""Used for passing information to the ADwin controller"""


SCHEMA = {
    "time": float,
    "variable": str,
    "value": float,
    "context": str,
    "module": int,
    "channel": int,
    "cycle": np.int32,
    "value_digits": np.int32,
}


def remove_unconnected_variables(timeline, connections):
    """
    Purges the given timeline of any `variable`s that do not have a matching `connection`.

    NOTE: Assumes timeline and connections are both pd.DataFrame-like things
    """
    # TODO: Shouldn't be here!!! More general

    timeline = deepcopy(timeline)
    _disconnections = [
        v
        for v in timeline["variable"].unique()
        if v not in connections["variable"].unique()
    ]

    for v in _disconnections:
        timeline.drop(timeline[timeline.variable == v].index, inplace=True)

    return timeline


def add_cycle(
    timeline,
    specifications=SPECIFICATIONS__DEFAULT,
    special_contexts=CONTEXTS__SPECIAL,
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
    if "time" not in timeline.columns:
        raise ValueError(
            f"`time` column not found. Columns present: {list(timeline.columns)}"
        )

    # Ensure device-specific cycle period is available
    try:
        cycle_period = specifications[device]["cycle_period__normal__us"]
    except KeyError:
        raise ValueError(
            f"`cycle_period__normal` not found in specifications for {device}."
        )

    # Calculate cycles and handle special contexts
    timeline["cycle"] = np.round(timeline["time"].values / cycle_period).astype(
        np.int32
    )

    # Apply special context cycles
    timeline = wt_frame.replace_column__filtered(
        timeline,
        CONTEXTS__SPECIAL,
        column__change="cycle",
    )

    return timeline


def initialize_ADwin(machine__adwin, output, specifications=SPECIFICATIONS__DEFAULT):
    """
    General setup of the *system*, rather than the specific experimental project.

    NOTE: Stateful.
    """
    # TODO:
    # - This would probably be easier if it accepted a dataframe
    # - Should we prepare all of the possible variables or does this waste memory?

    cycles = np.array([np.array(output[i])[:, 0] for i in range(2)]).flatten()
    # Finds the maximum cycle value, discounting special contexts
    time_end__cycles = cycles[~np.isin(cycles, list(CONTEXTS__SPECIAL.values()))].max()

    print(
        "=== time_end: {}s ===".format(
            time_end__cycles * specifications["device_001"]["cycle_period__normal__us"]
        )
    )

    # TODO: What's happening below should be explained here
    machine__adwin.Set_Par(1, int(time_end__cycles))
    machine__adwin.Set_Par(2, len(output[0]))
    machine__adwin.Set_Par(3, len(output[1]))

    machine__adwin.SetData_Long([a[0] for a in output[0]], 10, 1, len(output[0]))
    machine__adwin.SetData_Long([a[1] for a in output[0]], 11, 1, len(output[0]))
    machine__adwin.SetData_Long([a[2] for a in output[0]], 12, 1, len(output[0]))
    machine__adwin.SetData_Long([a[3] for a in output[0]], 13, 1, len(output[0]))

    machine__adwin.SetData_Long([d[0] for d in output[1]], 20, 1, len(output[1]))
    machine__adwin.SetData_Long([d[1] for d in output[1]], 22, 1, len(output[1]))
    machine__adwin.SetData_Long([d[2] for d in output[1]], 23, 1, len(output[1]))

    return machine__adwin


def check_safety_range(timeline):
    """
    Checks whether the values sent to this device fall inside its safety range.
    """
    for variable, group in timeline.groupby("variable"):
        if group["safety_range"].any():
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


def sanitize_special_contexts(timeline, special_contexts=CONTEXTS__SPECIAL):
    """
    Ensures that there isn't more than one entry for a given variable inside special contexts. This is necessary as there is no concept of 'time' inside the special contexts defined for ADwin.

    Similarly, the time values are adjusted to avoid automatic removal later on.
    """
    df = timeline[timeline["context"].isin(special_contexts)]
    df_N = df.groupby(["variable", "context"])["value"].count()
    duplicates = df_N[df_N > 1].reset_index()
    duplicates.columns = ["variable", "context", "variable_occurences"]

    # Replace time values with those specified in CONTEXTS__SPECIAL
    timeline = wt_frame.replace_column__filtered(timeline, CONTEXTS__SPECIAL)

    if duplicates.empty:
        return timeline
    else:
        raise ValueError(
            "The same variable has more than one value inside a special context. This will not work as expected on export to ADwin as these special contexts have no concept of time. For details,  see the duplicate information: "
            + str(duplicates)
        )


def sanitize_types(timeline, schema=SCHEMA):
    return timeline.astype(schema)


def sanitize__drop_duplicates(
    timeline,
    subset=["variable", "cycle"],
    unless_context=list(CONTEXTS__SPECIAL.keys()),
):
    """
    An alternative to that in timeline, to deal with ADwin-specific cases.

    Drop rows where the columns specified in `subset` are both duplicated, except for in the specific `context`s listed.
    """
    mask__duplicates = wt_frame.duplicated(timeline, subset=subset)

    return timeline[~mask__duplicates | (timeline["context"].isin(unless_context))]


def sanitize(timeline):
    """
    Includes ADwin-specific methods ontop of the basic timeline sanitization for removing unnecessary points and raising errors on illogical input.
    """
    return funcy.compose(
        sanitize__drop_duplicates,
        sanitize_special_contexts,
        sanitize_types,
    )(timeline)


def add_linear_conversion(timeline, unit, separator="__", column__new="value__digits"):
    """
    Performs a linear conversion, according to the associated bounding values ('unit_range'), and adds the resulting values as another column, 'value__digits'.

    unit: string.
    """
    dff = deepcopy(timeline)
    mask = dff["variable"].str.contains(separator + unit + "$")

    if mask.any():
        unit_range = dff.loc[mask, "unit_range"].iloc[0]

        dff.loc[dff.index[mask], column__new] = conv.unit_to_digits(
            dff.loc[mask, "value"], unit_range=unit_range
        )
    return dff


def add(timeline, adwin_connections, devices, specifications=SPECIFICATIONS__DEFAULT):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Digital: module 1
    Analogue otherwise
    """
    # TODO: parameterize the column names
    # TODO: Add vectorization to the python overview talk
    # TODO: Anything that is not voltage should be converted using a functor from the devices layer, which should be a set of conversion functors from units like A, MHz
    #       (this might actually be an overkill: as long as the device is linear, supplying unit_range is sufficient for the conversion, so the functor is necessary only for nonlinear devices)

    dff = timeline.join(
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

    return sanitize(add_cycle(dff, specifications))


def modules_digital(specifications):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.
    """

    # TODO: Check for modules (from dict) that have some characteristic (no voltage range etc?).

    return [int(1)]


def to_tuples(timeline, cols=["cycle", "module", "channel", "value_digits"]):
    return [tuple([np.int32(i) for i in x]) for x in timeline[cols].values]


def output(timeline, specifications=SPECIFICATIONS__DEFAULT):
    """
    Takes a dataframe of the experimental run and converts the result to an 'Output' format that can be processed by ADwin.


    return [[(cycle, module, channel, value), ...],
    [(cycle, channel, value), ...]]
    """
    # TODO: ensure digital outputs are integers
    # TODO: sort table by cycle before export
    # TODO: use the same format for analogue and digital (requires change at the ADwin side)

    if not ("module" in timeline.columns):
        raise ValueError(
            "No `module` listed in timeline. Remember to add ADwin specifications before ADwin export."
        )

    mods_digital = modules_digital(specifications)
    mods_analogue = [
        int(x) for x in timeline["module"].unique() if x not in mods_digital
    ]

    return [
        to_tuples(timeline.query("module in {}".format(mods_analogue))),
        to_tuples(
            timeline.query("module in {}".format(mods_digital)),
        ),
    ]


def to_adbasic(
    timeline,
    connections,
    devices,
    adwin_settings=SPECIFICATIONS__DEFAULT,
    time_resolution=None,
):
    """
    Convenience for converting a Wigner timeline (DataFrame) to an ADbasic-compatible list of tuples.

    This takes an operation-layer timeline, adds the columns necessary for an ADwin conversion, based on the supplied or default specifications, and then converts the relevant columns according to `adwin.output`, i.e.  [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]].
    """

    if time_resolution is not None:
        resolution = time_resolution
    else:
        resolution = adwin_settings["device_001"]["cycle_period__normal__us"]

    return funcy.compose(
        lambda tline: output(
            tline,
            specifications=adwin_settings,
        ),
        lambda tline: add(tline, connections, devices, specifications=adwin_settings),
        lambda tline: tl.expand(
            tline,
            time_resolution=resolution,
        ),
        lambda tline: remove_unconnected_variables(tline, connections),
    )(timeline)
