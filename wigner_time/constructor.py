# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

"""
Utilities for supplying default arguments to new functions in a flexible way, i.e. to provide constructors without objects.
"""

from munch import Munch

from wigner_time import timeline as tl
import pandas as pd


def arguments(variables, variables_default: Munch | None = None):
    """
    Adds/overrides the given variables to the given defaults.
    """
    return Munch(variables_default, **variables) if variables else variables_default


def time(time_start, timeline):
    """
    Convenience to set the time_start default in new functions.
    """
    if (time_start is None) and (timeline is not None):
        return tl.previous_time(timeline)

    if (time_start is None) and (timeline is None):
        return 0.0


def time_and_arguments(time_start, variables, variables_default, timeline):
    """
    A constructor-like function for 'normal' timeline generators.
    """
    return (
        time(time_start, timeline),
        arguments(variables, variables_default),
    )
