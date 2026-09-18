# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import funcy
import numpy as np
import importlib.util

if not importlib.util.find_spec("ADwin"):
    raise ImportError("Wigner Time's adwin modules require `ADwin` to be installed.")

import ADwin

from wignertime import timeline as tl
import wignertime.adwin as wt_adwin
from wignertime.adwin import connection
from wignertime.adwin import internal as ad


def link_device(DeviceNo=1, raiseExceptions=1, useNumpyArrays=0):
    """
    A Wrapper around ADwin.ADwin. Returns a new (stateful) ADwin machine object that is digitally connected to a physical ADwin machine.
    """
    return ADwin.ADwin(
        DeviceNo=DeviceNo,
        raiseExceptions=raiseExceptions,
        useNumpyArrays=useNumpyArrays,
    )


def convert(
    timeline,
    connections,
    devices,
    machine_specifications=ad.SPECIFICATIONS__DEFAULT,
    time_resolution=None,
) -> list[tuple]:
    """
    Convenience for converting a Wigner timeline (DataFrame) to an ADbasic-compatible list of tuples.

    This takes an operation-layer timeline, adds the columns necessary for an ADwin conversion, based on the supplied or default specifications, and then converts the relevant columns according to `adwin.to_tuples`, i.e.  [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]].
    """

    if time_resolution is not None:
        resolution = time_resolution
    else:
        resolution = machine_specifications["cycle_period"]

    return funcy.compose(
        lambda tline: ad.to_tuples(
            tline,
            machine_specifications=machine_specifications,
        ),
        lambda tline: ad.add(
            tline, connections, devices, machine_specifications=machine_specifications
        ),
        lambda tline: tl.expand(
            tline,
            time_resolution=resolution,
        ),
        lambda tline: connection.remove_unconnected_variables(tline, connections),
    )(timeline)


def create(
    timeline,
    connections,
    devices,
    machine: ADwin.ADwin | None = None,
    machine_specifications=ad.SPECIFICATIONS__DEFAULT,
    time_resolution=None,
) -> ADwin.ADwin:
    """
    For a given ADwin.ADwin machine object, combines the given timeline, connections and devices, converts the result to an ADwin-compatible format and initializes the machine for data collection.


    NOTE: Stateful.
    """
    # TODO:
    # - Should we prepare all of the possible variables or does this waste memory?

    if machine is None:
        machine = link_device()

    output = convert(timeline, connections, devices)

    # Either set may legitimately be empty -- a digital-only apparatus has no analogue
    # updates -- so the two are concatenated rather than stacked. Stacking them assumed
    # both were non-empty and raised `IndexError: too many indices` on an empty one,
    # before any `Set_Par` had run, leaving the machine holding the whole of the previous
    # experiment (#73).
    cycles = np.concatenate(
        [np.array(rows)[:, 0] for rows in output if len(rows)]
        or [np.array([], dtype=int)]
    )

    # Finds the maximum cycle value, discounting special contexts
    cycles__run = cycles[~np.isin(cycles, list(wt_adwin.CONTEXTS__SPECIAL.values()))]
    if not len(cycles__run):
        raise ValueError(
            "There is nothing to run: no update falls outside the special contexts "
            "{}, so the experiment has no duration. Every variable may have been "
            "dropped for want of a `connection`, or the timeline may describe only "
            "initial and final states.".format(list(wt_adwin.CONTEXTS__SPECIAL))
        )
    time_end__cycles = cycles__run.max()

    # TODO: make this a log instead of a print statement
    print(
        "=== time_end: {}s ===".format(
            time_end__cycles * machine_specifications["cycle_period"]
        )
    )

    # TODO: What's happening below should be explained here
    machine.Set_Par(1, int(time_end__cycles))
    machine.Set_Par(2, len(output[0]))
    machine.Set_Par(3, len(output[1]))

    # `cycle, module, channel, digits` go to data_10..13 for the analogue set and
    # data_20..23 for the digital one.
    #
    # An empty set is communicated by its count alone, set just above: there is nothing
    # to write, and a zero-length transfer is not meaningful. The count is what stops the
    # real-time program reading the array -- which matters, because the arrays are never
    # cleared, so a previous and longer run's contents are still sitting in them (#8).
    for data__first, rows in ((10, output[0]), (20, output[1])):
        for offset in range(4):
            if rows:
                machine.SetData_Long(
                    [row[offset] for row in rows], data__first + offset, 1, len(rows)
                )

    return machine
