# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np
from copy import deepcopy
import pandas as pd

from wigner_time import adwin

#TODO: read out the corresponding bit, range and gain values from adwin.specifications!!!

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

def unit_to_digits(unit, unit_range, num_bits=16, gain=8):
    num_vals = 2 ** num_bits
    min_unit, max_unit = unit_range
    unit_range_interval = max_unit - min_unit
    return np.round(unit * (num_vals / unit_range_interval) + 2 ** (num_bits - 1)).astype(int)