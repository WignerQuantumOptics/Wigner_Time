# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)
import pathlib as pl

import numpy as np
from scipy.interpolate import interp1d

import pandas as pd
from copy import deepcopy


def unit_to_digits(unit, unit_range=[-10.0, 10.0], num_bits: int = 16, gain: int = 1):
    """
    Transforms any unit range linearly to ADC digits.
    """
    # TODO: change to volts to digits
    unit_min, unit_max = np.asarray(unit_range) / gain
    return np.round(((unit - unit_min) / (unit_max - unit_min)) * (2**num_bits - 1))


def add_linear(
    timeline,
    unit: str,
    separator: str = "__",
    column__new: str = "value__digits",
    is_inplace: bool = True,
):
    """
    Performs a linear conversion, according to the associated conversion factor, and adds the resulting values as another column, `value__digits`.

    """
    # TODO: Should use the current `variable` regex consistently. Maybe available centrally?
    # - reconsider deepcopy
    # - link to ADwin specifications

    if is_inplace:
        dff = timeline
    else:
        dff = deepcopy(timeline)

    mask = dff["variable"].str.contains(separator + unit + "$")

    if mask.any():
        factor = dff.loc[mask, ["to_V"]].values[0][0]

        dff.loc[dff.index[mask], column__new] = unit_to_digits(
            dff.loc[mask, "value"] * factor
        )
    return dff


def function_from_file(
    path,
    method="cubic",
    fill_value="extrapolate",
    indices__column=[0, 1],
    **read_csv__args,
):
    """
    An interpolation function drawn from *two columns* of a CSV-like calibration file.

    NOTE: If you would like to invert the interpolation then just specify the columns backwards, e.g. indices__column=[1,0]

    e.g.
    function_from_file(
        "resources/calibration/aom_calibration.dat",
        names=["voltage", "transparency"],
        'sep=r"\s+"',
    ),
    """
    df = pd.read_csv(path, **read_csv__args).dropna()

    return interp1d(
        df.iloc[:, indices__column[0]],
        df.iloc[:, indices__column[1]],
        kind=method,
        fill_value=fill_value,
    )
