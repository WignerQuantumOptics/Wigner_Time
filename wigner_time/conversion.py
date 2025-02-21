# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np
from copy import deepcopy

# TODO: This is ADwin-dependent in practice and so should be moved.
# TODO: Should deal with module by module conversion


def unit_to_digits(unit, unit_range, num_bits=16, gain=8):
    """
    Transforms any unit range linearly to ADC digits.
    """
    # TODO: implement gain
    # TODO: read out the corresponding bit, range and gain values from adwin.specifications!!!

    num_vals = 2**num_bits
    min_unit, max_unit = unit_range
    unit_range_interval = max_unit - min_unit
    return np.round(
        unit * (num_vals / unit_range_interval) + 2 ** (num_bits - 1)
    ).astype(int)


def add_linear(
    timeline,
    unit: str,
    separator: str = "__",
    column__new: str = "value__digits",
    is_inplace: bool = True,
):
    """
    Performs a linear conversion, according to the associated bounding values (`unit__min` and `unit__max`), and adds the resulting values as another column, `value__digits`.

    """
    # TODO: Should use the current `variable` regex consistently. Maybe available centrally?
    # - reconsider deepcopy

    if is_inplace:
        dff = timeline
    else:
        dff = deepcopy(timeline)

    mask = dff["variable"].str.contains(separator + unit + "$")

    if mask.any():
        unit_range = dff.loc[mask, ["unit__min", "unit__max"]].iloc[0]

        dff.loc[dff.index[mask], column__new] = unit_to_digits(
            dff.loc[mask, "value"], unit_range=unit_range
        )
    return dff
