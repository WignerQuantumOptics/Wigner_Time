# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import importlib.util

if importlib.util.find_spec("matplotlib"):
    __all__ = ["timeline", "adwin", "variable", "connection", "device", "display"]
else:
    __all__ = ["timeline", "adwin", "variable", "connection", "device"]
