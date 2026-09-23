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
    A dictionary of equipment, context and unit.

    The convention is that a variable is represented by `thing_deviceOfManyParts__unit` for a non-digital unit and `thing_deviceOfManyParts` otherwise. The `deviceOfManyParts` part may itself contain single underscores, e.g. `coil_MOT_lower__A`.

    The convention is spelled out by `config.VARIABLE__REGEX`, which is read here on every call so that a site applying a different one can rebind it.
    """

    match = re.match(wt_config.VARIABLE__REGEX, variable)

    if match is not None:
        e, c, u = match.groups()
        if u:
            unit = u
        elif wt_config.LABEL__ANCHOR in e:
            unit = wt_config.LABEL__ANCHOR
        else:
            unit = "digital"

        return Munch(equipment=e, context=c, unit=unit)
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


def units(timeline: wt_frame.CLASS, do_digital: bool = True):
    """
    Returns a set of different timeline units (strs).
    """
    us = set(map(unit, timeline["variable"].unique()))
    if do_digital:
        return us
    else:
        us.discard("digital")
        return us
