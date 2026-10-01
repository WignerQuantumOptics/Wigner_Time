# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Wigner Time, version 0.9 of the user API: one import for most work.

    import wignertime.api.v0_9 as wt

    initial = wt.update(shutter__MOT=0, coil__MOT__A=0.0, time=0.0, context="init")
    MOT = wt.stack(
        wt.anchor(1e-3, context="MOT"),
        wt.update(shutter__MOT=1),
        wt.ramp(coil__MOT__A=-1.0, duration=10e-3, function=wt.tanh),
    )
    timeline = wt.to_timeline(wt.stack(initial, MOT))

Building and placing (`update`, `ramp`, `anchor`, `stack`, `cascade`, `to_timeline`,
`expand`), reading a timeline back (`previous`,
`context_information`) and drawing it (`display`), the origin
tags (`INFER`, `ANCHOR`, `LAST`, `VARIABLE`), ramp shapes (`tanh`, `linear`, and
`with_points` for writing one), devices and their calibrations (`devices`,
`function_from_file`), and files (`save`, `load`) are all here. `config` is the module
of settings a user may change, such as `wt.config.VARIABLE__REGEX`; it is the module
itself, so a setting changed through it is the one the package reads.

What needs an optional package is in a namespace of its own, loaded on first use:

    wt.adwin            converting, uploading and running on ADwin     (extra `adwin`)
    wt.adwin.console    the manual console                            (extra `console`)
    wt.adwin.adc        recording with the ADC during a run            (extra `adwin`)

`wt.display(timeline)` draws a timeline and needs matplotlib (extra `display`); it is a
function here, and looks for matplotlib only when called, saying what to install if it
is missing.

Every name here is the package's own function, not a copy: `wt.update` is
`wignertime.timeline.build.update`. What `__all__` lists is the API of version 0.9.
"""

import importlib as _importlib

from wignertime import config
from wignertime.internal.tags import ANCHOR, INFER, LAST, VARIABLE
from wignertime.hardware.conversion import function_from_file
from wignertime.hardware.device import new as devices
from wignertime.io.display import quantities as display
from wignertime.io.file import load, save
from wignertime.timeline.ramp_function import linear, tanh, with_points
from wignertime.timeline.build import (
    anchor,
    cascade,
    expand,
    ramp,
    stack,
    to_timeline,
    update,
)
from wignertime.timeline.query import context_information, previous

__all__ = [
    # building and placing
    "update",
    "ramp",
    "anchor",
    "stack",
    "cascade",
    "to_timeline",
    "expand",
    # reading and drawing a timeline
    "previous",
    "context_information",
    "display",
    # origin tags
    "INFER",
    "ANCHOR",
    "LAST",
    "VARIABLE",
    # ramp shapes
    "tanh",
    "linear",
    "with_points",
    # devices and calibrations
    "devices",
    "function_from_file",
    # files
    "save",
    "load",
    # settings
    "config",
]

# The parts that need an optional package, imported when first used, so that importing
# this module never requires ADwin.
_OPTIONAL = ("adwin",)


def __getattr__(name):
    if name in _OPTIONAL:
        return _importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted([*__all__, *_OPTIONAL])
