# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Wigner Time. For most work, `import wignertime.api.v0_9 as wt`.

    api         the user API, by version
    config      the settings a user may change (`wt.config`)
    timeline    building (`build`) and reading back (`query`) timelines, the ramp
                functions and the variable naming convention
    hardware    the device layer: physical units to output values, and calibrations
    io          files (`save`, `load`) and drawing a timeline
    backend     the real-time systems: `adwin` (converting, uploading, running) and the
                `national_instruments` stub
    internal    what the whole package shares, and nothing a user calls
"""

__all__ = ["api", "config", "timeline", "hardware", "io", "backend"]

_MOVED = {
    "ramp_function": "wignertime.timeline.ramp_function",
    "variable": "wignertime.timeline.variable",
    "device": "wignertime.hardware.device",
    "conversion": "wignertime.hardware.conversion",
    "file": "wignertime.io.file",
    "display": "wignertime.io.display",
    "adwin": "wignertime.backend.adwin",
    "national_instruments": "wignertime.backend.national_instruments",
}


def __getattr__(name):
    """Say where a module that moved (#163) went, rather than only that it is missing."""
    if name in _MOVED:
        raise ModuleNotFoundError(
            "`wignertime.{}` moved to `{}` (#163). Users reach it through the user API,"
            " `import wignertime.api.v0_9 as wt`.".format(name, _MOVED[name]),
            name="wignertime." + name,
        )
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
