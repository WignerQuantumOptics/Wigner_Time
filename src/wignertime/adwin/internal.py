# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For 'lower-level' manipulations of ADwin-specifc timeline informaton.

In general, the user shouldn't need to use these functions and there is no guarantee that the API will not change.

"""

import numpy as np

from wignertime.config import wtlog as wtl
from wignertime import timeline as tl
from wignertime import conversion as conv
from wignertime import device
from wignertime import variable as wt_variable
from wignertime.internal import dataframe as wt_frame
import wignertime.adwin as wt_adwin
from wignertime.adwin import connection
from wignertime.adwin import validate as wt_validate

"""
Represents the key ADwin settings for the given machine.

These should be loaded by the ADwin system during initialization. The settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.

The specifications have the form of a list of 'ADwin device' dictionaries, with the modules represented as a list of dictionaries.
"""
SPECIFICATIONS__DEFAULT = {
    # In seconds, like every other time in the package. This is the period of the
    # ADbasic event loop that emits the timeline, i.e. `Initial_Processdelay` divided
    # by the processor clock rate -- a relationship nothing currently checks (see
    # KNOWN_ISSUES D14).
    #
    # NOTE: this was `cycle_period__normal`, where `normal` contrasted with a
    # `cycle_period__burst` of 250 ns that has since been dropped. If ADC burst mode
    # (`P2_Burst_Init` in `WignerTimeADwinADC.bas`) is ever described here, it wants a
    # name of its own -- `sampling_period__ADC` or similar. It is a sampling period for
    # reading, on a different clock and for a different purpose, and calling the two
    # things flavours of one "cycle period" is what made the qualifier necessary.
    "cycle_period": 5e-6,
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
    The module numbers carrying digital connections, derived from the specifications.

    A digital line is one bit wide, so a module of one-bit channels is a digital module.
    This is a *derivation* rather than a declaration, deliberately: a `kind` field beside
    `bits` would be a second source of truth, and a module declared
    `{"kind": "digital", "bits": 16}` would have no right answer. The same reasoning
    keeps module and channel numbers out of the device conversions.

    Until 2026-09-22 the test read `m.get("bits", False) == True`, which picks out the
    digital module only because `1 == True` in Python (D12/#126). Note what that did and
    did not cost: `x == True` and `x == 1` agree for every number, so the answer was
    never wrong -- what was wrong was that "is one bit wide" was written as a comparison
    against a boolean, leaving the intent unrecoverable from the code.

    A module that declares no `bits` at all now raises rather than being taken for
    analogue, which is the one behaviour that changed. Silently reading an
    under-specified module as analogue is a guess about hardware, and it would put a
    16-bit conversion on a digital line.

    NOTE: Modules are numbered from 1 (unlike Python lists).

    NOTE: Nothing here restricts how many modules may be digital, and the real-time
    program cannot honour more than one -- both `p2_digprog` and `p2_digout` name module
    1 as a literal. See D18/#133, which is an open decision rather than an oversight.
    """
    modules = machine_specifications["modules"]

    modules__unspecified = [i + 1 for i, m in enumerate(modules) if "bits" not in m]
    if modules__unspecified:
        raise ValueError(
            "Module(s) {} declare no `bits`, so whether they are digital cannot be"
            " determined. Every entry of `machine_specifications['modules']` needs its"
            " width: 1 for a digital module, 16 for the usual analogue one.".format(
                modules__unspecified
            )
        )

    return [i + 1 for i, m in enumerate(modules) if m["bits"] == 1]


def add_cycle(
    timeline,
    machine_specifications=SPECIFICATIONS__DEFAULT,
    special_contexts=wt_adwin.CONTEXTS__SPECIAL,
):
    """
    Inserts a new `cycle` column into the timeline as a conversion of the `time` column into 'number of cycles'.

    Parameters:
    - timeline: DataFrame containing the experimental data.
    - machine_specifications: Dictionary describing the machine; must contain `cycle_period`, in seconds.
    - special_contexts: Dictionary with context-specific overrides for cycle values.

    Raises:
    - ValueError if required columns are missing, or if `cycle_period` is absent from the specifications.
    """
    # Check if `time` column is present

    if "time" not in timeline.columns:
        raise ValueError(
            f"`time` column not found. Columns present: {list(timeline.columns)}"
        )

    # Ensure the cycle period is available
    try:
        cycle_period = machine_specifications["cycle_period"]
    except KeyError:
        raise ValueError(
            "`cycle_period` not found in the machine specifications. Keys present: {}.".format(
                list(machine_specifications)
            )
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

    # Here because this is where the two tables meet, and because conversion is the one
    # point at which hardware enters. Neither `connection.new` nor `device.new` can do it
    # alone: each sees only its own vocabulary (A14).
    device.check_correspondence(connections, devices)

    dff = wt_frame.join(timeline, connections)
    dff = wt_frame.join(dff, devices)
    dff = dff.sort_values(by=["time"], ignore_index=True)

    dff = conv.add(dff)
    # TODO: ^ This 'feels' inefficient/wrong?

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
    mods_analogue = [x for x in timeline["module"].unique() if x not in mods_digital]

    # NOTE: filtered by value rather than by a formatted query string. `module` is an
    # int64 column, so `unique()` yields numpy scalars, and building a query out of them
    # produced `module in [np.int64(3), np.int64(4)]` -- which pandas parses and then
    # rejects with `UndefinedVariableError: name 'np' is not defined`, an error that
    # looks like it comes from inside pandas and says nothing about modules (#41). A
    # bare `int()` on each element used to hold that off; comparing values removes the
    # failure mode instead of guarding it.
    return [
        to_tuples__raw(wt_frame.subframe(timeline, "module", mods_analogue)),
        to_tuples__raw(wt_frame.subframe(timeline, "module", mods_digital)),
    ]
