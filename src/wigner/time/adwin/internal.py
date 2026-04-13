"""
For 'lower-level' manipulations of ADwin-specifc timeline informaton.

In general, the user shouldn't need to use these functions and there is no guarantee that the API will not change.

"""

import numpy as np

from wigner.time.config import wtlog as wtl
from wigner.time import timeline as tl
from wigner.time import conversion as conv
from wigner.time import device
from wigner.time import variable as wt_variable
from wigner.time.internal import dataframe as wt_frame
import wigner.time.adwin as wt_adwin
from wigner.time.adwin import connection
from wigner.time.adwin import validate as wt_validate

"""
Represents the key ADwin settings for the given machine.

These should be loaded by the ADwin system during initialization. The settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.

The specifications have the form of a list of 'ADwin device' dictionaries, with the modules represented as a list of dictionaries.
"""
SPECIFICATIONS__DEFAULT = {
    "cycle_period__normal__us": 5e-6,
    "modules": [
        {
            "bits": 1,
            "voltage_range": [0.0, 5.0],
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
        {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
    ],
}


def modules__digital(machine_specifications):
    """
    The list of modules that govern digital connections.

    Currently, this just returns a static list, based on a specific lab setup.

    NOTE: Modules are numbered from 1 (unlike Python lists).
    """

    return [
        i + 1
        for i, m in enumerate(machine_specifications["modules"])
        if m.get("bits", False) == True
    ]


def add_cycle(
    timeline,
    machine_specifications=SPECIFICATIONS__DEFAULT,
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
        cycle_period = machine_specifications["cycle_period__normal__us"]
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


def add(timeline, connections, devices, machine_specifications=SPECIFICATIONS__DEFAULT):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Digital: module 1
    Analogue otherwise
    """

    wtl.debug("Got to `adwin.core.add`")

    dff = wt_frame.join(timeline, connections)
    dff = wt_frame.join(dff, devices)
    dff = dff.sort_values(by=["time"], ignore_index=True)

    dff = conv.add(dff)
    # for variable, group in dff.groupby("variable"):
    # TODO: should dff below be group?
    # conv.add(dff)
    # TODO: ^ This 'feels' inefficient/wrong?

    print(dff.columns)
    mask__digital = dff["module"].isin(modules__digital(machine_specifications))

    dff.loc[mask__digital, "value__digits"] = round(dff["value"])
    # TODO: Shouldn't all of value__digits be rounded?

    device.check_within_range(dff)
    dcycle = add_cycle(dff, machine_specifications)

    return wt_validate.all(dcycle)


def to_tuples__raw(timeline, cols=["cycle", "module", "channel", "value__digits"]):
    """
    A raw extraction of ADwin-relevant values from a `timeline`, regardless of whether or not the module is digital or not.

    NOTE: No validation is done here.
    """
    return [tuple([np.int32(i) for i in x]) for x in timeline[cols].values]


def to_tuples(timeline, machine_specifications=SPECIFICATIONS__DEFAULT):
    """
    Takes a full, ADwin-compatible, dataframe of the experimental run and converts the result to an output format that can be processed by ADwin (tuples), separating analogue and digital values.

    return [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]]
    """
    wtl.debug("Got to `output`")

    if not timeline["cycle"].is_monotonic_increasing:
        timeline = timeline.sort_values(by=["cycle"], ignore_index=True)

    if not ("module" in timeline.columns):
        raise ValueError(
            "No `module` listed in timeline. Remember to add ADwin specifications before ADwin export."
        )

    mods_digital = modules__digital(machine_specifications)
    mods_analogue = [
        int(x) for x in timeline["module"].unique() if x not in mods_digital
    ]

    return [
        to_tuples__raw(timeline.query("module in {}".format(mods_analogue))),
        to_tuples__raw(
            timeline.query("module in {}".format(mods_digital)),
        ),
    ]
