# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import funcy
import numpy as np
import importlib.util

if not importlib.util.find_spec("ADwin"):
    raise ImportError("Wigner Time's adwin modules require `ADwin` to be installed.")

import ADwin

from wigner.time import timeline as tl
import wigner.time.adwin as wt_adwin
from wigner.time.adwin import connection
from wigner.time.adwin import internal as ad


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
        resolution = machine_specifications["cycle_period__normal__us"]

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

    cycles = np.array([np.array(output[i])[:, 0] for i in range(2)]).flatten()
    # Finds the maximum cycle value, discounting special contexts
    time_end__cycles = cycles[
        ~np.isin(cycles, list(wt_adwin.CONTEXTS__SPECIAL.values()))
    ].max()

    # TODO: make this a log instead of a print statement
    print(
        "=== time_end: {}s ===".format(
            time_end__cycles * machine_specifications["cycle_period__normal__us"]
        )
    )

    # TODO: What's happening below should be explained here
    machine.Set_Par(1, int(time_end__cycles))
    machine.Set_Par(2, len(output[0]))
    machine.Set_Par(3, len(output[1]))

    machine.SetData_Long([a[0] for a in output[0]], 10, 1, len(output[0]))
    machine.SetData_Long([a[1] for a in output[0]], 11, 1, len(output[0]))
    machine.SetData_Long([a[2] for a in output[0]], 12, 1, len(output[0]))
    machine.SetData_Long([a[3] for a in output[0]], 13, 1, len(output[0]))

    machine.SetData_Long([d[0] for d in output[1]], 20, 1, len(output[1]))
    machine.SetData_Long([d[1] for d in output[1]], 21, 1, len(output[1]))
    machine.SetData_Long([d[2] for d in output[1]], 22, 1, len(output[1]))
    machine.SetData_Long([d[3] for d in output[1]], 23, 1, len(output[1]))

    return machine
