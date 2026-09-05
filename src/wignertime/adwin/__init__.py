# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np

CONTEXTS__SPECIAL = {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1}
"""Used for passing information to the ADwin controller"""


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
