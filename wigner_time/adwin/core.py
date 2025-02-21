# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from copy import deepcopy

import funcy
import numpy as np

from wigner_time import timeline as tl
from wigner_time import conversion as conv
from wigner_time import device
from wigner_time import variable as wt_variable
from wigner_time.internal import dataframe as wt_frame
import wigner_time.adwin as wt_adwin
from wigner_time.adwin import connection
from wigner_time.adwin import validate as wt_validate


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


def add_cycle(
    timeline,
    specifications=SPECIFICATIONS__DEFAULT,
    special_contexts=wt_adwin.CONTEXTS__SPECIAL,
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
        special_contexts,
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
    time_end__cycles = cycles[
        ~np.isin(cycles, list(wt_adwin.CONTEXTS__SPECIAL.values()))
    ].max()

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


def modules__digital(specifications):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.
    """

    # TODO: Check for modules (from dict) that have some characteristic (no voltage range etc?).

    return [int(1)]


def add(timeline, adwin_connections, devices, specifications=SPECIFICATIONS__DEFAULT):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Digital: module 1
    Analogue otherwise
    """
    # TODO: parameterize the column names
    # TODO: Add vectorization to the python overview talk
    #       (this might actually be an overkill: as long as the device is linear, supplying unit_range is sufficient for the conversion, so the functor is necessary only for nonlinear devices)

    dff = wt_frame.join(timeline, adwin_connections)
    dff = wt_frame.join(dff, devices)
    dff = dff.sort_values(by=["time"], ignore_index=True)

    units = wt_variable.units(dff)
    for variable, group in dff.groupby("variable"):
        for u in units:
            conv.add_linear(dff, u)

    # TODO: ^ This 'feels' inefficient?

    mask__analogue = dff["module"] != 1
    # TODO: fix this hardcoding

    dff.loc[~mask__analogue, "value__digits"] = round(dff["value"])

    device.check_safety_range(dff)

    return wt_validate.all(add_cycle(dff, specifications))


def to_tuples(timeline, cols=["cycle", "module", "channel", "value__digits"]):
    """
    A raw extraction of ADwin-relevant values from a `timeline`.

    No validation is done here.
    """
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

    mods_digital = modules__digital(specifications)
    mods_analogue = [
        int(x) for x in timeline["module"].unique() if x not in mods_digital
    ]

    return [
        to_tuples(timeline.query("module in {}".format(mods_analogue))),
        to_tuples(
            timeline.query("module in {}".format(mods_digital)),
        ),
    ]


def to_data(
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
        lambda tline: connection.remove_unconnected_variables(tline, connections),
    )(timeline)
