# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np

CONTEXTS__SPECIAL = {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1}
"""Used for passing information to the ADwin controller"""

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
