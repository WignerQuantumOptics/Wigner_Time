# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np
from copy import deepcopy
import pandas as pd

from wigner_time import adwin

# TODO: the devices layer should be a set of conversion functors from units like A, MHz, etc., and we should provide convenient factories for such functors

# TODO: read out the corresponding bit, range and gain values from adwin.specifications!!!


def units(df, separator="__"):
    """
    Returns a set of different timline units (strs).
    """
    # TODO: Should probably be moved to `timeline`
    return set(
        [
            u
            for var in df["variable"].unique()
            if len(u := (var.split(separator)[-1])) == 1
        ]
    )


def unit_to_digits(unit, unit_range, num_bits=16, gain=8):
    """
    Transforms any unit range linearly to ADC digits.
    TODO: implement gain
    """
    num_vals = 2**num_bits
    min_unit, max_unit = unit_range
    unit_range_interval = max_unit - min_unit
    return np.round(
        unit * (num_vals / unit_range_interval) + 2 ** (num_bits - 1)
    ).astype(int)
