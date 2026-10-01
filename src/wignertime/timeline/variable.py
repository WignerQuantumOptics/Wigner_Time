# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Outlines the conventions for variables  and provides some convenience functions for working with them.
"""

import re
from munch import Munch
from wignertime import config as wt_config
from wignertime.internal import tags as wt_tags


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
        elif wt_tags.LABEL__ANCHOR in d:
            unit = wt_tags.LABEL__ANCHOR
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


def __getattr__(name):
    """Say where a name that moved went."""
    if name == "units":
        raise AttributeError(
            "`variable.units` is now `timeline.query.units`: reading a timeline back is in"
            " `wignertime.timeline.query`."
        )
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
