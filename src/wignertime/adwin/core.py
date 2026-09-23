# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import funcy
import numpy as np
import importlib.util
from typing import NamedTuple

if not importlib.util.find_spec("ADwin"):
    raise ImportError("Wigner Time's adwin modules require `ADwin` to be installed.")

import ADwin

from wignertime import timeline as tl
import wignertime.adwin as wt_adwin
from wignertime.adwin import connection
from wignertime.adwin import internal as ad
from wignertime.adwin import validate as wt_validate


class Upload(NamedTuple):
    """
    The log of one `upload`: where the timeline went, at what period, and what was written.

    The first two fields are the machine and the process, in the order of the
    `(machine, process)` pair that routines starting the controller take -- the camera
    routines of `sec:parameter_scan` among them -- so an `Upload` can be passed wherever
    such a pair is expected.

    `cycle__last` is what `Par_1` was set to, the cycle of the last row outside the
    special contexts, and `time__last` is the same instant in seconds. `analogue` and
    `digital` are the arrays as written, `(cycle, module, channel, digits)` per row.
    """

    machine: ADwin.ADwin
    process: int
    processor: str
    processdelay: int
    cycle_period: float
    cycle__last: int
    analogue: list
    digital: list

    @property
    def time__last(self):
        return self.cycle__last * self.cycle_period

    def __repr__(self):
        # The arrays run to hundreds of thousands of rows, so they are counted, not shown.
        return (
            "Upload(process={}, processor={!r}, processdelay={}, cycle_period={!r},"
            " cycle__last={}, time__last={!r}, rows={} analogue + {} digital)".format(
                self.process,
                self.processor,
                self.processdelay,
                self.cycle_period,
                self.cycle__last,
                self.time__last,
                len(self.analogue),
                len(self.digital),
            )
        )


def _timing(machine, process):
    """`(processor, processdelay, cycle_period)` of `process`, as the machine reports them."""
    processor = machine.Processor_Type()
    if processor not in wt_adwin.PROCESSDELAY__RATE:
        raise ValueError(
            "The controller reports a {!r} processor, and how fast its Processdelay counts"
            " is not known here: `adwin.PROCESSDELAY__RATE` covers {}. Add it there once"
            " the rate is confirmed; guessing would rescale every time in the"
            " experiment.".format(processor, list(wt_adwin.PROCESSDELAY__RATE))
        )

    processdelay = machine.Get_Processdelay(process)
    if not processdelay > 0:
        raise ValueError(
            "Process {} reports a Processdelay of {!r}, so it has no cycle period. Is the"
            " backend loaded as process {}?".format(process, processdelay, process)
        )

    return (
        processor,
        processdelay,
        processdelay / wt_adwin.PROCESSDELAY__RATE[processor],
    )


def read_cycle_period(machine, process):
    """
    The cycle period of `process` on `machine`, in seconds: its `Processdelay`, read off the
    machine, divided by the rate at which the processor counts it.

    Read, never set. An ADbasic program can overwrite its own `Processdelay`, so a value
    written from here is not one the machine is bound to keep. For the same reason this
    shows the value before any the program sets for itself once started.
    """
    return _timing(machine, process)[2]


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


def upload(
    timeline,
    connections,
    devices,
    machine: ADwin.ADwin,
    process: int,
    machine_specifications=None,
    time_resolution=None,
) -> Upload:
    """
    Converts a timeline for `process` on `machine` and writes it into the machine's memory,
    ready for the process to be started. Returns the `Upload` log of what was written.

    The cycle period is read off the machine (`read_cycle_period`), never given: a wrong
    one rescales every time in the experiment, which reads as physics rather than as an
    error. That is why the machine and the process are both required. The process is the
    one whose `Processdelay` sets the period, so it must be the one started afterwards;
    the arrays themselves are shared by every process on the machine.

    `machine_specifications` and `time_resolution` are passed on to `convert`.

    NOTE: Stateful. It writes `Par_1..3` and the data arrays, and starts nothing.
    """
    # TODO:
    # - Should we prepare all of the possible variables or does this waste memory?

    processor, processdelay, cycle_period = _timing(machine, process)

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
    cycle__last = int(cycles__run.max())

    # `endCC`, `analogArrayDim` and `digitalArrayDim` in `WignerTimeADwin.bas`: the event
    # loop ends after the last cycle, and the counts say how far into each array to read.
    machine.Set_Par(1, cycle__last)
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

    return Upload(
        machine=machine,
        process=process,
        processor=processor,
        processdelay=processdelay,
        cycle_period=cycle_period,
        cycle__last=cycle__last,
        analogue=output[0],
        digital=output[1],
    )
