# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The polars backend. Phase 2: only the frame class exists so far.

Every name of `INTERFACE` not defined here raises `NotImplementedError` when used (see
the package `__init__`), so `pytest --backend=polars` lists what remains.
"""

import polars as pl

CLASS = pl.DataFrame
