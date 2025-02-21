"""
Outlines the conventions for variables  and provides some convenience functions for working with them.
"""

import re
from munch import Munch
from wigner_time.internal import dataframe as wt_frame

REGEX = re.compile(r"^([^_]+)_([^_]+)(?:__([^_]+))?$")


def parse(variable: str) -> dict:
    """
    A dictionary of equipment, context and unit.

    The convention is that a variable is represented by `thing_deviceOfManyParts__unit` for a non-digital unit and `thing_deviceOfManyParts` otherwise.
    """

    match = re.match(REGEX, variable)

    if match is not None:
        e, c, u = match.groups()
        return Munch(equipment=e, context=c, unit=u if u else "digital")
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


def units(timeline: wt_frame.CLASS, do_digital=True):
    """
    Returns a set of different timeline units (strs).
    """
    us = set(map(unit, timeline["variable"].unique()))
    if do_digital:
        return us
    else:
        us.discard("digital")
        return us
