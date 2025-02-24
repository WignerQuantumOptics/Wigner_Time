# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

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

These should be loaded by the ADwin system during initialization. The settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.

The specifications have the form of a list of 'ADwin device' dictionaries, with the modules represented as a list of dictionaries.

# TODO: is there an implicit way of reliably checking if a module is digital or not?
"""
SPECIFICATIONS__DEFAULT = [
    {
        "cycle_period__normal__us": 5e-6,
        "modules": [
            {
                "voltage_range": [0.0, 5.0],
                "gain": 1,
                "digital": True,
            },
            {
                "bits": 16,
                "voltage_range": [-10.0, 10.0],
                "gain": 1,
            },
            {
                "bits": 16,
                "voltage_range": [-10.0, 10.0],
                "gain": 1,
            },
            {
                "bits": 16,
                "voltage_range": [-10.0, 10.0],
                "gain": 1,
            },
        ],
    },
]


def add_cycle(
    timeline,
    adwin_device=SPECIFICATIONS__DEFAULT[0],
    special_contexts=wt_adwin.CONTEXTS__SPECIAL,
):
    """
    Inserts a new `cycle` column into the timeline as a conversion of the `time` column into 'number of cycles'.

    Parameters:
    - timeline: DataFrame containing the experimental data.
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
        cycle_period = adwin_device["cycle_period__normal__us"]
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


def initialize(
    machine__adwin, output, adwin_device=SPECIFICATIONS__DEFAULT[0]
) -> object:
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
            time_end__cycles * adwin_device["cycle_period__normal__us"]
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


def modules__digital(adwin_device):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.

    NOTE: Modules are numbered from 1 (unlike Python lists).
    """

    return [
        i + 1 for i, m in enumerate(adwin_device["modules"]) if m.get("digital", False)
    ]


def add(timeline, connections, devices, adwin_device=SPECIFICATIONS__DEFAULT[0]):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Digital: module 1
    Analogue otherwise
    """
    # TODO: deal with nonlinear conversions

    dff = wt_frame.join(timeline, connections)
    dff = wt_frame.join(dff, devices)
    dff = dff.sort_values(by=["time"], ignore_index=True)

    units = wt_variable.units(dff)
    for variable, group in dff.groupby("variable"):
        # TODO: should dff below be group?
        for u in units:
            conv.add_linear(dff, u)
    # TODO: ^ This 'feels' inefficient/wrong?

    mask__digital = dff["module"].isin(modules__digital(adwin_device))

    dff.loc[mask__digital, "value__digits"] = round(dff["value"])
    # TODO: Shouldn't all of value__digits be rounded?

    device.check_safety_range(dff)
    return wt_validate.all(add_cycle(dff, adwin_device))


def to_tuples(timeline, cols=["cycle", "module", "channel", "value__digits"]):
    """
    A raw extraction of ADwin-relevant values from a `timeline`, regardless of whether or not the module is digital or not.

    NOTE: No validation is done here.
    """
    return [tuple([np.int32(i) for i in x]) for x in timeline[cols].values]


def output(timeline, adwin_device=SPECIFICATIONS__DEFAULT):
    """
    Takes a dataframe of the experimental run and converts the result to an 'Output' format that can be processed by ADwin, separating analogue and digital outputs.

    return [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]]
    """
    if not timeline["cycle"].is_monotonic_increasing:
        timeline = timeline.sort_values(by=["cycle"], ignore_index=True)

    if not ("module" in timeline.columns):
        raise ValueError(
            "No `module` listed in timeline. Remember to add ADwin specifications before ADwin export."
        )

    mods_digital = modules__digital(adwin_device)
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
    adwin_device=SPECIFICATIONS__DEFAULT[0],
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
        resolution = adwin_device["cycle_period__normal__us"]

    return funcy.compose(
        lambda tline: output(
            tline,
            adwin_device=adwin_device,
        ),
        lambda tline: add(tline, connections, devices, adwin_device=adwin_device),
        lambda tline: tl.expand(
            tline,
            time_resolution=resolution,
        ),
        lambda tline: connection.remove_unconnected_variables(tline, connections),
    )(timeline)
