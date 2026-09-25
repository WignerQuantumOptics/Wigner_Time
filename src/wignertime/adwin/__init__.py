# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np

CONTEXTS__SPECIAL = {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1}
"""Used for passing information to the ADwin controller"""

PROCESSDELAY__RATE = {"T12": 1e9}
"""
How fast `Processdelay` counts on each processor type, in units per second, keyed by what
`ADwin.ADwin.Processor_Type()` returns. A process's cycle period is its `Processdelay`
divided by this.

The one hardware constant the package keeps, and only for the processors it has run on:
both laboratories use the T12, at 1 ns per unit. Another type -- including `"T12.1"`,
which the driver reports separately -- is refused by name rather than guessed at, and
belongs here only once its rate is confirmed. Kept as a rate rather than a tick so that
`5000 / 1e9` gives exactly the float `5e-6`.
"""

PAR__PROCESSDELAY__EXPECTED = 9
"""`processdelayExpected` in the sequencer: the Processdelay `upload` built the arrays for."""

PAR__PROCESSDELAY__REPORTED = 14
"""
`processdelayReported` in the sequencer: the Processdelay its event loop runs at, written at
the end of `init:`. `upload` clears it, so a 0 after a run means that the loaded program does
not report it. That is a program older than the check, which is refused rather than trusted.
Where the two differ, the sequencer has refused to play the run (#128).
"""

ROWS__MAX = {
    "analogue": 10_000_000,
    "digital": 10_000,
    "analogue__finish": 256,
    "digital__finish": 256,
}
"""
How many rows each array of the sequencer holds: `analogMaxArrayDim`, `digitalMaxArrayDim`
and `finishMaxArrayDim` in both `.bas` programs, which must agree. `upload` refuses more
rather than letting the transfer fail partway, with some arrays written and others not.
"""

CYCLES__RUN = (0, 2**31 - 2)
"""
The first and last cycle at which a row outside the special contexts can be played.

The real-time program's `cyclecount` is a 32-bit `long` that starts at 0 and is
incremented once past the last row, so that row can be at most 2**31 - 2. Everything
outside the range belongs to the sentinels of `CONTEXTS__SPECIAL`, which share the
column with the time axis (D19). See `validate.cycles` for what each way out does.
"""


SCHEMA = {
    "time": float,
    "variable": str,
    "value": float,
    "context": str,
    "module": int,
    "channel": int,
    "cycle": np.int32,
    "value__digits": np.int32,
}
