# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)
from copy import deepcopy

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from wigner_time.internal import dataframe as wt_frame

SPECIFICATIONS__DEFAULT = {"voltage_range": [-10.0, 10.0], "num_bits": 16, "gain": 1}


def to_digits(voltage, voltage_range=[-10.0, 10.0], num_bits: int = 16, gain: int = 1):
    """
    Transforms any voltage range linearly to analogue-digital-converter(ADC) digits.
    """
    v_min, v_max = np.asarray(voltage_range) / gain
    return int(np.round(((voltage - v_min) / (v_max - v_min)) * (2**num_bits - 1)))


def _add_linear(
    timeline,
    column__conversion="to_V",
    column__new: str = "value__digits",
    is_inplace=False,
    specifications=SPECIFICATIONS__DEFAULT,
):
    """
    Performs a linear conversion, according to the associated conversion factor, adds the resulting values as another column, `value__digits`, and returns the result.
    """
    mask = pd.to_numeric(timeline[column__conversion], errors="coerce").notna()
    if mask.any():
        if is_inplace:
            dff = timeline
        else:
            dff = deepcopy(timeline)

        dff.loc[mask, column__new] = to_digits(
            dff.loc[mask, "value"] * dff.loc[mask, column__conversion], **specifications
        )

        return dff
    else:
        return timeline


def _add_function(
    timeline,
    column__conversion="to_V",
    column__new: str = "value__digits",
    is_inplace=False,
    specifications=SPECIFICATIONS__DEFAULT,
):
    """
    Performs a conversion, according to the associated function, adds the resulting values as another column, `value__digits`, and returns the result.
    """
    mask = timeline[column__conversion].apply(callable)
    if mask.any():
        if is_inplace:
            dff = timeline
        else:
            dff = deepcopy(timeline)

        dff.loc[mask, column__new] = to_digits(
            dff.loc[mask].apply(
                lambda row: row[column__conversion](row["value"]), axis=1
            ),
            **specifications,
        )

        return dff
    else:
        return timeline


def add(
    timeline: wt_frame.CLASS,
    specifications=SPECIFICATIONS__DEFAULT,
    column__conversion: str = "to_V",
    column__new: str = "value__digits",
) -> wt_frame.CLASS:
    if column__conversion in timeline.columns:
        dff = _add_linear(
            timeline,
            column__conversion=column__conversion,
            column__new=column__new,
            specifications=specifications,
        )
        return _add_function(
            dff,
            specifications=specifications,
            column__conversion=column__conversion,
            column__new=column__new,
        )

    else:
        raise ValueError(
            f"Cannot convert values because {column__conversion} column does not exist. "
        )


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
    # TODO: Include default 'sep' etc.
    df = pd.read_csv(path, **read_csv__args).dropna()

    # Deal with possible x-duplicates
    columns = df.columns
    df_avg = df.groupby(columns[indices__column[0]], as_index=False).mean()

    return interp1d(
        df_avg.iloc[:, 0],
        df_avg.iloc[:, indices__column[1]],
        kind=method,
        fill_value=fill_value,
    )
