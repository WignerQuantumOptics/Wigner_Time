# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The manual console, version 1 of the user API. Needs the `console` extra.

    table = wt.adwin.console.panel(connections, devices, timeline__defaults)
    widgets = wt.adwin.console.create_UI(machine, table)

or, without widgets, `configure` the console with the panel and `set_value` and
`readback` through the `Console` it returns. `final_state`, `jumps` and `health` report
on the machine; `OutputsOwned` is raised when a run holds the outputs.
"""

from wignertime.adwin.console import (
    Console,
    Health,
    Jump,
    OutputsOwned,
    configure,
    create_UI,
    final_state,
    health,
    jumps,
    panel,
    readback,
    set_value,
)

__all__ = [
    "panel",
    "configure",
    "create_UI",
    "set_value",
    "readback",
    "final_state",
    "jumps",
    "health",
    "Console",
    "Jump",
    "Health",
    "OutputsOwned",
]
