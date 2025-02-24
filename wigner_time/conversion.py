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
    unit_min, unit_max = np.asarray(unit_range) / gain
    return np.round(
        ((unit - unit_min) / (unit_max - unit_min)) * (2**num_bits - 1)
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


def function_from_file(
    path,
    method="cubic",
    fill_value="extrapolate",
    indices__column=[0, 1],
    **read_csv__args
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
