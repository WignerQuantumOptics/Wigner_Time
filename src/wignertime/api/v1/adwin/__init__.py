# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Running a timeline on ADwin, version 1 of the user API. Needs the `adwin` extra.

    import wignertime.api.v1 as wt

    connections = wt.adwin.connections(["shutter__MOT", 1, 11], ["coil__A", 3, 1])
    machine = wt.adwin.link_device()
    upload = wt.adwin.upload(timeline, connections, devices, machine, process=1)
    run = wt.adwin.run(upload)  # returns once the run has ended

`connections` says which module and channel each variable is wired to. `convert` gives
the arrays the machine would play, without a machine; `upload` writes them into it.
`run`, or `start` and `wait`, or `with running(upload):` play them. `LostEvents` and
`PeriodRefused` are the errors a run can end in.

The manual console is `wt.adwin.console`, and recording with the ADC `wt.adwin.adc`.
"""

import importlib as _importlib

from wignertime.adwin.connection import new as connections
from wignertime.adwin.core import (
    LostEvents,
    PeriodRefused,
    Run,
    Upload,
    convert,
    link_device,
    read_cycle_period,
    run,
    running,
    start,
    upload,
    wait,
)

__all__ = [
    "connections",
    "link_device",
    "read_cycle_period",
    "convert",
    "upload",
    "run",
    "start",
    "wait",
    "running",
    "Upload",
    "Run",
    "LostEvents",
    "PeriodRefused",
]

_OPTIONAL = ("console", "adc")


def __getattr__(name):
    if name in _OPTIONAL:
        return _importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted([*__all__, *_OPTIONAL])
