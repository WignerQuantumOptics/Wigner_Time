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
