# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Recording with the ADC variant of the sequencer, `resources/ADwin/WignerTimeADwinADC.bas`.

That program plays an upload exactly as `WignerTimeADwin.bas` does, and in addition records
one channel of an ADC card in burst mode, over a window of the run. The window is stated here
in seconds of the timeline, and written to the program in cycles of the run, at the period
`core.upload` read off the machine. The program therefore assumes no period of its own. It
used to convert seconds to cycles at a fixed 5 us, so at a period of 2 us, Lab2's, a window
asked for at 1 s would have opened at 0.4 s (#94, step 10).

A window is armed for **one** run: the program's `finish:` disarms it. A run nobody armed
records nothing, rather than a window left over from an earlier run, and `read` says so.

The contract with the program, whose `#Define`s must agree with the numbers below:

- `Par_42` and `Par_43`, written by `arm`: the cycle at which the burst starts, and the cycle
  by which it is over. The program starts the burst only if `0 <= Par_42 < Par_43 <= Par_1`,
  and its `finish:` resets `Par_43` to 0, which is what disarms.
- `FPar_61`, written by `arm`: the window's duration in seconds. The program turns it into a
  number of samples at its own sample period, and caps it at its buffer.
- `Par_41` and `Par_44`, reported by the program, and cleared by `arm`: how many samples it
  recorded, and their period in whole nanoseconds. `Par_41` is 0 unless the burst had its whole
  window. The period is a Par rather than an FPar because an FPar reaches Python in single
  precision, which over two million samples would shift the last one by some 30 ns.
- `Data_1`: the samples, as the card's digits.

`FPar_62`, the start in seconds, is no longer read.
"""

import math
from typing import NamedTuple

import numpy as np

from wignertime.adwin import core

PROCESS = 4
"""The process number in the header of `WignerTimeADwinADC.bas`."""

PAR__SAMPLES = 41
PAR__CYCLE__START = 42
PAR__CYCLE__END = 43
PAR__SAMPLE_PERIOD__NS = 44
FPAR__DURATION = 61
DATA__SAMPLES = 1


class Window(NamedTuple):
    """
    What `arm` wrote: a window of the run of `upload`, in cycles of that run.

    `cycle__start` is the start rounded to the nearest cycle, by the same rule as every row
    of the timeline, and `time__start` is that instant in seconds, which is when the first
    sample is taken. `cycle__end` is the first cycle by which the whole `duration` has
    passed.
    """

    upload: core.Upload
    cycle__start: int
    cycle__end: int
    duration: float

    @property
    def time__start(self):
        """The start of the window as armed, in seconds of the timeline."""
        return self.cycle__start * self.upload.cycle_period


class Samples(NamedTuple):
    """
    One recording: `time` in seconds of the timeline, one entry per sample, and `digits` as
    the card delivered them, with the `window` that was armed and the `run` that played it.
    """

    time: np.ndarray
    digits: np.ndarray
    window: Window
    run: core.Run


def arm(upload, t, duration):
    """
    Arms the next run of `upload` to record from `t` for `duration` seconds, and returns the
    `Window` as written.

    `upload` must be one made for the ADC variant, process 4. The window must lie within the
    run: the samples are read out in `finish:`, and a burst still under way there would give
    a partly stale buffer, so a window that ends after the run is refused here. If process 4
    is running, this waits for it first, since its `finish:` would disarm the new window.
    """
    if upload.process != PROCESS:
        raise ValueError(
            "The ADC records only in `WignerTimeADwinADC.bas`, process {}, but this upload"
            " was made for process {}.".format(PROCESS, upload.process)
        )
    if not duration > 0:
        raise ValueError(
            "The duration of a recording must be a positive number of seconds, not"
            " {!r}.".format(duration)
        )
    if t < 0:
        raise ValueError(
            "A recording cannot start before the run does, at {} s.".format(t)
        )

    period = upload.cycle_period
    cycle__start = int(np.round(t / period))
    # Rounded to a millionth of a cycle before the ceiling, so that float noise cannot add a
    # whole cycle: 10e-6 / 2e-6 is 5.000000000000001.
    cycle__end = cycle__start + math.ceil(round(duration / period, 6))
    if cycle__end > upload.cycle__last:
        raise ValueError(
            "The recording from {:g} s for {:g} s ends after the run, which ends at {:g} s:"
            " the burst would still be under way when `finish:` reads it out. Shorten the"
            " recording, or extend the timeline.".format(t, duration, upload.time__last)
        )

    machine = upload.machine
    core._wait_for_the_arrays(
        machine,
        PROCESS,
        "arming its recording, which its `finish:` would disarm",
        "arming the recording of process {process}",
    )
    machine.Set_Par(PAR__CYCLE__START, cycle__start)
    machine.Set_Par(PAR__CYCLE__END, cycle__end)
    machine.Set_FPar(FPAR__DURATION, duration)
    machine.Set_Par(PAR__SAMPLES, 0)
    machine.Set_Par(PAR__SAMPLE_PERIOD__NS, 0)

    return Window(upload, cycle__start, cycle__end, duration)


def read(window, run):
    """
    Reads out what the `run` recorded in the `window` armed for it, and returns the `Samples`.

    Refuses a run of another upload, and one not yet waited for. Raises if the program
    recorded nothing, which it does when the run was not armed or did not last until the
    window closed, and if it recorded less than the window, which it does when the window is
    longer than its buffer. A program that reports no sample period is older than this
    contract, and is refused, since it would have placed the window by its own assumed period.
    """
    if run.upload is not window.upload:
        raise ValueError(
            "This window was armed for another upload than the one this run played."
        )
    if run.duration is None:
        raise ValueError(
            "The run has not been waited for, so its recording may be incomplete. Read it"
            " after `core.wait`, or use `adc.run`."
        )

    machine = window.upload.machine
    sample_period = machine.Get_Par(PAR__SAMPLE_PERIOD__NS) * 1e-9
    if sample_period == 0:
        raise RuntimeError(
            "Process {} did not report its sample period, so the program loaded there is"
            " older than the one that takes its window in cycles, and it placed the window"
            " by an assumed period. Load the current `WignerTimeADwinADC.bas`.".format(
                PROCESS
            )
        )

    samples = machine.Get_Par(PAR__SAMPLES)
    if samples == 0:
        raise RuntimeError(
            "Process {} recorded nothing: either the run was not armed (a window is armed"
            " for one run only, so arm it again, or use `adc.run`), or the run ended before"
            " cycle {}, when the window closed.".format(PROCESS, window.cycle__end)
        )
    if samples * sample_period < window.duration - sample_period:
        raise RuntimeError(
            "Process {} recorded {} samples, {:g} s, of the {:g} s asked for: the window is"
            " longer than its buffer.".format(
                PROCESS, samples, samples * sample_period, window.duration
            )
        )

    # As the lab has always read it off the rig.
    digits = np.asarray(machine.GetData_Int64(DATA__SAMPLES, 1, samples))
    time = window.time__start + np.arange(samples) * sample_period
    return Samples(time, digits, window, run)


def run(upload, t, duration):
    """
    Records from `t` for `duration` seconds in one run of `upload`, and returns the
    `Samples`: `arm`, then `core.run`, then `read`. Arms afresh each time, so it can be
    called repeatedly on the same upload, to average over runs.
    """
    window = arm(upload, t, duration)
    return read(window, core.run(upload))
