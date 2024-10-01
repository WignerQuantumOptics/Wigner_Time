# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np
from copy import deepcopy
import pandas as pd

from wigner_time import adwin

# TODO: the devices layer should be a set of conversion functors from units like A, MHz, etc., and we should provide convenient factories for such functors
#       (this might actually be an overkill: as long as the device is linear, supplying unit_range is sufficient for the conversion, so the functor is necessary only for nonlinear devices)


#TODO: read out the corresponding bit, range and gain values from adwin.specifications!!!


def unit_to_digits(unit, unit_range, num_bits=16, gain=8):
    """
    Transforms any unit range linearly to ADC digits.
    TODO: implement gain
    """
    num_vals = 2 ** num_bits
    min_unit, max_unit = unit_range
    unit_range_interval = max_unit - min_unit
    return np.round(unit * (num_vals / unit_range_interval) + 2 ** (num_bits - 1)).astype(int)



# the 2 functions below are not needed, since with the unit_range in the devices data structure, we can always scale directly into the digits range

def voltage_to_digits(voltage, num_bits=16, voltage_range=20, gain=8, **kwargs):
    """
    Transforms volts to ADC digits.
    TODO: implement gain
    """
    num_vals = 2**num_bits

    return np.round((voltage * (num_vals / voltage_range)) + 2 ** (num_bits - 1)).astype(int)

def current_to_digits(current, num_bits=16, current_range=10, gain=8, **kwargs):
    """
    Transforms volts to ADC digits.
    TODO: implement gain
    """
    num_vals = 2**num_bits

    return np.round((current * (num_vals / current_range)) + 2 ** (num_bits - 1)).astype(int)
