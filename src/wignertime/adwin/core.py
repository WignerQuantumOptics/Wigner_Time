# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import funcy
import numpy as np
import contextlib
import dataclasses
import importlib.util
import time
from typing import NamedTuple

if not importlib.util.find_spec("ADwin"):
    raise ImportError("Wigner Time's adwin modules require `ADwin` to be installed.")

import ADwin

from wignertime import timeline as tl
from wignertime.config import wtlog as wtl
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
    `digital` are the rows played, `(cycle, module, channel, digits)`; `analogue__finish` and
    `digital__finish` are the final state, `(module, channel, digits)`, which the sequencer
    applies however the run ends.
    """

    machine: ADwin.ADwin
    process: int
    processor: str
    processdelay: int
    cycle_period: float
    cycle__last: int
    analogue: list
    digital: list
    analogue__finish: list
    digital__finish: list

    @property
    def time__last(self):
        return self.cycle__last * self.cycle_period

    def __repr__(self):
        # The arrays run to hundreds of thousands of rows, so they are counted, not shown.
        return (
            "Upload(process={}, processor={!r}, processdelay={}, cycle_period={!r},"
            " cycle__last={}, time__last={!r}, rows={} analogue + {} digital,"
            " finish={} analogue + {} digital)".format(
                self.process,
                self.processor,
                self.processdelay,
                self.cycle_period,
                self.cycle__last,
                self.time__last,
                len(self.analogue),
                len(self.digital),
                len(self.analogue__finish),
                len(self.digital__finish),
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


POLL__PERIOD = 0.1
"""How often a process is asked whether it has stopped, in seconds: the lab's own rate."""


def _wait_until_stopped(machine, process, reason=None):
    """
    Returns once `process` reports that it has stopped. With a `reason`, says once that it
    is waiting and why; without one it waits quietly, as at the end of a run, where
    waiting is the point.

    Waits while the status is anything but 0 (stopped), not merely while it is 1, so that a
    process that has not finished is never taken for stopped. A process still in its
    `finish:` section is believed to report -1; UNVERIFIED, and the loop does not depend
    on it.
    """
    if machine.Process_Status(process) == 0:
        return

    if reason is not None:
        wtl.warning(
            "Process {} is still running; waiting for it to stop before {}.".format(
                process, reason
            )
        )
    while machine.Process_Status(process) != 0:
        time.sleep(POLL__PERIOD)


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

    If the process is still running, `upload` converts first and then waits for it to stop
    before writing, saying so once. The machine accepts writes mid-run and the running
    sequence reads them, so writing at once would rewrite the arrays under a run that is
    still playing (A15/#151). A parameter scan that uploads shot N+1 while shot N plays its
    tail is the case in point. Only `process` is waited for. Another process playing the
    same arrays, such as the ADC variant, is not seen here.

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

    # The final state leaves the playback arrays for arrays of its own, which `finish:`
    # plays from the start however the run ended (B11). Its rows need no cycle.
    analogue, analogue__finish = _split_finish(output[0])
    digital, digital__finish = _split_finish(output[1])
    rows = {
        "analogue": analogue,
        "digital": digital,
        "analogue__finish": analogue__finish,
        "digital__finish": digital__finish,
    }
    too_many = {k: len(v) for k, v in rows.items() if len(v) > wt_adwin.ROWS__MAX[k]}
    if too_many:
        raise ValueError(
            "The timeline does not fit the sequencer's arrays: {} rows against room for"
            " {}. Nothing was written.".format(
                too_many, {k: wt_adwin.ROWS__MAX[k] for k in too_many}
            )
        )

    # Only now, so that the conversion overlaps whatever is left of the previous run.
    _wait_until_stopped(
        machine, process, "uploading, so as not to rewrite the arrays it is playing"
    )

    # `endCC`, `analogArrayDim` and `digitalArrayDim` in `WignerTimeADwin.bas`: the event
    # loop ends after the last cycle, and the counts say how far into each array to read.
    # `analogFinishDim` and `digitalFinishDim` do the same for the final state.
    machine.Set_Par(1, cycle__last)
    machine.Set_Par(2, len(analogue))
    machine.Set_Par(3, len(digital))
    machine.Set_Par(15, len(analogue__finish))
    machine.Set_Par(16, len(digital__finish))

    # The period check (#128): the sequencer compares its own Processdelay with this at the
    # end of `init:`, and plays nothing past the initial state if they differ. The report is
    # cleared so that a program which does not make one cannot pass off an old one.
    machine.Set_Par(wt_adwin.PAR__PROCESSDELAY__EXPECTED, processdelay)
    machine.Set_Par(wt_adwin.PAR__PROCESSDELAY__REPORTED, 0)

    # `cycle, module, channel, digits` go to data_10..13 for the analogue set and
    # data_20..23 for the digital one. The final state is `module, channel, digits` in
    # data_31..33 and `channel, value` in data_42..43: the same numbers plus 20, without the
    # cycle, and without the digital module, which the sequencer does not read (D18).
    #
    # An empty set is communicated by its count alone, set just above: there is nothing
    # to write, and a zero-length transfer is not meaningful. The count is what stops the
    # real-time program reading the array -- which matters, because the arrays are never
    # cleared, so a previous and longer run's contents are still sitting in them (#8).
    for data__first, columns, rows__set in (
        (10, range(4), analogue),
        (20, range(4), digital),
        (31, range(3), analogue__finish),
        (42, range(1, 3), digital__finish),
    ):
        if rows__set:
            for number, column in enumerate(columns, start=data__first):
                machine.SetData_Long(
                    [row[column] for row in rows__set], number, 1, len(rows__set)
                )

    return Upload(
        machine=machine,
        process=process,
        processor=processor,
        processdelay=processdelay,
        cycle_period=cycle_period,
        cycle__last=cycle__last,
        analogue=analogue,
        digital=digital,
        analogue__finish=analogue__finish,
        digital__finish=digital__finish,
    )


def _split_finish(rows):
    """`(played, final)`: the rows to play, and the final state's as `(module, channel, digits)`."""
    finish = wt_adwin.CONTEXTS__SPECIAL["ADwin_Finish"]
    return (
        [row for row in rows if row[0] != finish],
        [tuple(row[1:]) for row in rows if row[0] == finish],
    )


###############################################################################
#   Running what was uploaded
###############################################################################


class LostEvents(RuntimeError):
    """
    A run lost events: ADwin's term for event cycles that came due while the previous one
    was still executing.

    Nothing is skipped when that happens -- `cyclecount` advances once per *executed*
    event, so every row is still played, in order, at its cycle -- but the cycles
    themselves stretch, and the run takes longer than its timeline says by `run.slip`.
    The shot is not the experiment that was described, so it is refused rather than
    reported. `run` carries the record.
    """

    def __init__(self, run):
        self.run = run
        super().__init__(
            "Process {} lost {} events during the run, so its sequence ran {:.1f} us"
            " longer than described: some cycle had more rows to play than one cycle"
            " period allows.".format(
                run.upload.process, run.lost_events, run.slip * 1e6
            )
        )


class PeriodRefused(RuntimeError):
    """
    The sequencer refused to play a run, because the Processdelay its event loop runs at is not
    the one the arrays were built for (#128). It played the initial state and nothing after.

    `upload` reads the period off the machine, but before the start. A program may still set its
    own Processdelay once started, and a different process from the one the upload was made for
    may have been started. Either way, playing the arrays would rescale every time in them.
    """

    def __init__(self, run):
        self.run = run
        rate = wt_adwin.PROCESSDELAY__RATE[run.upload.processor]
        super().__init__(
            "Process {} refused to play the run: it runs at a Processdelay of {} ({:g} us),"
            " but the arrays were built for {} ({:g} us). Nothing after the initial state"
            " was played.".format(
                run.upload.process,
                run.processdelay__reported,
                run.processdelay__reported / rate * 1e6,
                run.upload.processdelay,
                run.upload.cycle_period * 1e6,
            )
        )


@dataclasses.dataclass
class Run:
    """
    The record of one run of an upload, filled in as it goes: `start` sets the first three
    fields and `wait` the rest.

    `time__start` is wall-clock time (`time.time()`), so the record can be filed with the
    data the shot produced; `duration` is how long the run took, as seen from here, in
    seconds; `lost_events` counts ADwin's lost events during it (see `LostEvents`);
    `processdelay__reported` is the Processdelay the sequencer reported running at (see
    `PeriodRefused`).
    """

    upload: Upload
    lost_events__start: int
    time__start: float
    lost_events: int | None = None
    duration: float | None = None
    processdelay__reported: int | None = None

    @property
    def slip(self):
        """How much longer the run took than described, in seconds."""
        return self.lost_events * self.upload.cycle_period


def start(upload):
    """
    Starts the process an `upload` was made for, and returns its `Run`.

    If the process is still running -- a replay of the same upload, which does not go
    through `upload` and its wait -- this waits for it first, saying so once. Everything
    that must be ready before the sequence begins, such as a camera waiting for its
    trigger, has to be armed before this is called.
    """
    machine, process = upload.machine, upload.process
    _wait_until_stopped(machine, process, "starting it again")

    run = Run(
        upload=upload,
        lost_events__start=machine.Get_Lost_Events(process),
        time__start=time.time(),
    )
    machine.Start_Process(process)
    return run


def wait(run):
    """
    Waits for a `Run` to end, fills in its record, and returns it.

    Raises `PeriodRefused` if the sequencer refused to play the run, and refuses a program that
    did not report its Processdelay at all: one older than the check, whose run nothing vouches
    for. Then raises `LostEvents` if the run lost any. The count is the difference of ADwin's
    counter across the run, which is right if the counter accumulates from the moment
    the program was loaded. UNVERIFIED: if it instead restarts with every start, a fall
    across the run is refused below as the tell, but a run that happened to lose exactly
    as many events as the previous one would pass. One run on the rig settles which.
    """
    machine, process = run.upload.machine, run.upload.process
    _wait_until_stopped(machine, process)

    run.duration = time.time() - run.time__start

    run.processdelay__reported = machine.Get_Par(wt_adwin.PAR__PROCESSDELAY__REPORTED)
    if run.processdelay__reported == 0:
        raise RuntimeError(
            "Process {} did not report the Processdelay it ran at, so the program loaded"
            " there is older than the period check (#128), and nothing confirms that the run"
            " kept the timeline's times. Load the current `WignerTimeADwin.bas`, or"
            " `WignerTimeADwinADC.bas` as process 4.".format(process)
        )
    if run.processdelay__reported != run.upload.processdelay:
        raise PeriodRefused(run)

    lost_events = machine.Get_Lost_Events(process)
    run.lost_events = lost_events - run.lost_events__start

    if run.lost_events < 0:
        raise RuntimeError(
            "ADwin's lost-events counter for process {} fell from {} to {} across the run,"
            " so it evidently restarts with every start, and `adwin.core.wait` has to read"
            " it differently.".format(process, run.lost_events__start, lost_events)
        )
    if run.lost_events:
        raise LostEvents(run)

    return run


@contextlib.contextmanager
def running(upload):
    """
    Brackets one run of an `upload`: starts it on entry, and on leaving waits for it to end
    and checks it (`wait`). The block is where whatever the run triggers is collected:

        camera.arm()                          # before the start
        with adwin.running(log) as run:
            frames = camera.capture(4)        # triggered by the timeline
        # here the run is over, and lost no events

    If the block raises, the run is still waited out before the error goes on, but not
    checked, and not stopped: until B11 is fixed, stopping a run leaves the apparatus in
    whatever state the timeline had reached.
    """
    run = start(upload)
    try:
        yield run
    except BaseException:
        _wait_until_stopped(upload.machine, upload.process)
        raise
    wait(run)


def run(upload):
    """
    Runs an `upload` with nothing to collect alongside, and returns its `Run`: the plain
    case, as for a sequence whose results are read off the machine afterwards.
    """
    with running(upload) as record:
        pass
    return record
