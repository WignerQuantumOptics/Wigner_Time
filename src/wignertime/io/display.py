# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Plotting a timeline. Needs the `display` extra (matplotlib).

Importing this module needs nothing optional: matplotlib is looked for when a timeline is
drawn, so `import wignertime.api.v0_9 as wt` works without it and `wt.display(timeline)`
says what to install.
"""

import importlib
import importlib.util

INSTALL__DISPLAY = "\n".join(
    [
        "Drawing a timeline needs matplotlib, which is not installed. It comes with the"
        " `display` extra:",
        "",
        '    pip install "wigner-time[display] @ git+https://github.com/WignerQuantumOptics/Wigner_Time.git"',
        "",
        "or, in a clone of the repository, `poetry install --extras display`.",
    ]
)

OPTIONS__QUANTITIES = (
    "do_context",
    "do_show",
    "symbol_quantities",
    "cmap__context",
    "range__x",
)
"""The keywords `quantities` passes on; `test_display` keeps them matched to the drawing."""


def _drawing():
    """The module that draws, imported now rather than with this one."""
    if importlib.util.find_spec("matplotlib") is None:
        raise ModuleNotFoundError(INSTALL__DISPLAY, name="matplotlib")
    return importlib.import_module("wignertime.io.internal.drawing")


def quantities(timeline, variables=None, **options):
    """
    Draws `timeline`, one panel per physical quantity (by the variables' units) and one
    for the digital lines; `variables` restricts it to those named.

        wt.display(timeline)
        wt.display(timeline, ["coil__MOT__A", "shutter__MOT"], range__x=(0.0, 0.1))

    `options`:
    - `do_context` (True): shade each context;
    - `do_show` (True): show the figure, rather than only return it;
    - `symbol_quantities`: unit symbol to quantity name, e.g. `{"A": "Current"}`;
    - `cmap__context` ("magma"): the colour map for the contexts;
    - `range__x`: the time range drawn.

    Returns the figure and its axes. Needs matplotlib (the `display` extra), and says so
    when it is missing.
    """
    unknown = sorted(set(options) - set(OPTIONS__QUANTITIES))
    if unknown:
        raise TypeError(
            "`display` takes no option(s) {}; it takes {}.".format(
                unknown, list(OPTIONS__QUANTITIES)
            )
        )
    return _drawing().quantities(timeline, variables, **options)


def display(timeline, variables=None):
    """`quantities` with its defaults. Kept for code that calls `display.display`."""
    return quantities(timeline, variables)
