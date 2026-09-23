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
from wignertime.adwin import validate as wt_validate

CYCLE_PERIOD__ASSUMED = 5e-6
"""
The cycle period `create` assumes when it is not given one, in seconds: that of the
committed `WignerTimeADwin.bas`, whose `Initial_Processdelay = 5000` is 5 us at the
T12's 1 ns tick.

Transitional. The period belongs to the program loaded on the machine, and `create`,
which holds the machine, is to read it from there on every call (#94). `convert` may run
without a machine, so it has no default at all.
"""


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
    cycle_period,
    machine_specifications=None,
    time_resolution=None,
) -> list[list[tuple]]:
    """
    Convenience for converting a Wigner timeline (DataFrame) to an ADbasic-compatible list of tuples.

    This takes an operation-layer timeline, adds the columns necessary for an ADwin conversion, based on the supplied or default specifications, and then converts the relevant columns according to `adwin.to_tuples`, i.e.  [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]].

    `cycle_period` is the period of the controller's event loop, in seconds, and has no
    default: it belongs to the program loaded on the machine, not to the package, and
    the two laboratories this was written for run at 5 us and 2 us. A wrong value is a
    uniform rescaling of every time in the experiment, which reads as physics rather
    than as an error, so it is asked for rather than assumed.

    `time_resolution` is the step at which ramps are sampled, the cycle period when not
    given -- the finest step the hardware can act on. A coarser one thins the ramps
    without moving anything in time, since cycles are computed from the times
    themselves.

    `machine_specifications` describes the installed modules, and is
    `internal.SPECIFICATIONS__DEFAULT` when not given, read at call time.
    """
    if time_resolution is None:
        time_resolution = cycle_period

    machine_specifications = ad.specifications(machine_specifications)

    return funcy.compose(
        wt_validate.ascending,
        lambda tline: ad.to_tuples(
            tline,
            machine_specifications=machine_specifications,
        ),
        lambda tline: ad.add(
            tline,
            connections,
            devices,
            cycle_period,
            machine_specifications=machine_specifications,
        ),
        lambda tline: tl.expand(
            tline,
            time_resolution=time_resolution,
        ),
        lambda tline: connection.remove_unconnected_variables(tline, connections),
    )(timeline)


def create(
    timeline,
    connections,
    devices,
    machine: ADwin.ADwin | None = None,
    machine_specifications=None,
    cycle_period=None,
    time_resolution=None,
) -> ADwin.ADwin:
    """
    For a given ADwin.ADwin machine object, combines the given timeline, connections and devices, converts the result to an ADwin-compatible format and initializes the machine for data collection.

    `machine_specifications`, `cycle_period` and `time_resolution` are passed on to
    `convert`, and the same period gives the run length printed here, so the number
    reported and the data uploaded cannot disagree. They used to: neither argument
    reached `convert`, while the specification still set the printed length (D15/#129).
    Without a `cycle_period`, `CYCLE_PERIOD__ASSUMED` is used.

    NOTE: Stateful.
    """
    # TODO:
    # - Should we prepare all of the possible variables or does this waste memory?

    if machine is None:
        machine = link_device()

    if cycle_period is None:
        cycle_period = CYCLE_PERIOD__ASSUMED

    output = convert(
        timeline,
        connections,
        devices,
        cycle_period,
        machine_specifications=machine_specifications,
        time_resolution=time_resolution,
    )

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
    print("=== time_end: {}s ===".format(time_end__cycles * cycle_period))

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
