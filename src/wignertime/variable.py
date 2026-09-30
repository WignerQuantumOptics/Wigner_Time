# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Outlines the conventions for variables  and provides some convenience functions for working with them.
"""

import re
from munch import Munch
from wignertime.internal import dataframe as wt_frame
from wignertime import config as wt_config


def parse(variable: str) -> dict:
    """
    A dictionary of device, UID and unit.

    The convention is `<device>__<UID>__<unit>` for an analog variable and
    `<device>__<UID>` for a digital one, e.g. `coil__MOT_lower__A` and `shutter__MOT`.
    `<device>` and `<unit>` contain no `_`; the UID may contain single ones.

    The convention is spelled out by `config.VARIABLE__REGEX`, which is read here on every call so that a site applying a different one can rebind it.
    """

    match = re.match(wt_config.VARIABLE__REGEX, variable)

    if match is not None:
        d, uid, u = match.groups()
        if u:
            unit = u
        elif wt_config.LABEL__ANCHOR in d:
            unit = wt_config.LABEL__ANCHOR
        else:
            unit = "digital"

        return Munch(device=d, uid=uid, unit=unit)
    else:
        raise ValueError(
            f"Variable {variable} doesn't meet the current naming convention."
        )


def is_valid(variable: str) -> bool:
    try:
        parse(variable)
        return True
    except ValueError:
        return False


def unit(variable):
    return parse(variable)["unit"]


def without_unit(variable):
    """`coil__MOT_lower__A` without its unit, `coil__MOT_lower`; a digital name as it is."""
    p = parse(variable)
    return "{}__{}".format(p.device, p.uid)


def units(timeline: wt_frame.CLASS, do_digital: bool = True):
    """
    Returns a set of different timeline units (strs).
    """
    us = set(map(unit, wt_frame.unique(timeline, "variable")))
    if do_digital:
        return us
    else:
        us.discard("digital")
        return us
