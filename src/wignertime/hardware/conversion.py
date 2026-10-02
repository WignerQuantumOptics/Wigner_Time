# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np
from scipy.interpolate import interp1d

from wignertime.internal import dataframe as wt_frame

SPECIFICATIONS__DEFAULT = {"voltage_range": [-10.0, 10.0], "num_bits": 16, "gain": 1}


def to_digits(voltage, voltage_range=[-10.0, 10.0], num_bits: int = 16, gain: int = 1):
    """
    Transforms any voltage linearly to analogue-digital-converter(ADC) digits.
    """

    v = np.asarray(voltage, dtype=float)
    v_min, v_max = np.asarray(voltage_range) / gain

    result = np.round(((v - v_min) / (v_max - v_min)) * (2**num_bits - 1)).astype(int)
    return result.item() if result.ndim == 0 else result


def _add_linear(
    timeline,
    column__conversion="to_V",
    column__new: str = "value__digits",
    specifications=SPECIFICATIONS__DEFAULT,
):
    """
    Performs a linear conversion, according to the associated conversion factor, adds the resulting values as another column, `value__digits`, and returns the result.
    """
    factors = wt_frame.column(timeline, column__conversion)
    mask = ~wt_frame.not_numeric(factors)
    if mask.any():
        values = wt_frame.column(timeline, "value")
        return wt_frame.with_column(
            timeline,
            column__new,
            to_digits(
                np.asarray(values[mask] * factors[mask], dtype=float), **specifications
            ),
            where=mask,
        )
    else:
        return timeline


def _add_function(
    timeline,
    column__conversion="to_V",
    column__new: str = "value__digits",
    specifications=SPECIFICATIONS__DEFAULT,
):
    """
    Performs a conversion, according to the associated function, adds the resulting values as another column, `value__digits`, and returns the result.
    """
    functions = wt_frame.column(timeline, column__conversion)
    mask = np.array([callable(f) for f in functions], dtype=bool)
    if mask.any():
        values = wt_frame.column(timeline, "value")
        return wt_frame.with_column(
            timeline,
            column__new,
            to_digits(
                np.array(
                    [f(v) for f, v in zip(functions[mask], values[mask])], dtype=float
                ),
                **specifications,
            ),
            where=mask,
        )
    else:
        return timeline


def add(
    timeline: wt_frame.CLASS,
    specifications=SPECIFICATIONS__DEFAULT,
    column__conversion: str = "to_V",
    column__new: str = "value__digits",
) -> wt_frame.CLASS:
    """
    Performs a conversion, according to the associated factor or function, adds the resulting values as another column, `value__digits`, and returns the result.
    """
    if wt_frame.has_columns(timeline, [column__conversion]):
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


def _read_calibration(path, read_csv__args):
    """
    The columns of a calibration file, as `(names, rows)`: a list of column names and a
    2-D float array, rows with a missing entry dropped. Read through `wt_frame`, so the
    keyword arguments are those of the backend's CSV reader (`pandas.read_csv`).
    """
    df = wt_frame.read_csv(path, **read_csv__args)
    names = list(wt_frame.columns(df))
    rows = np.column_stack([wt_frame.column(df, n, dtype=float) for n in names])
    return names, rows[~np.isnan(rows).any(axis=1)]


def function_from_file(
    path,
    method="cubic",
    fill_value="extrapolate",
    indices__column=[0, 1],
    **read_csv__args,
):
    """
    An interpolation function drawn from *two columns* of a CSV-like calibration file.

    `indices__column` says which: `[x, y]`, the function taking the first to the second.
    To invert the calibration, give them the other way round, `indices__column=[1, 0]`.
    Where the `x` column repeats a value, the `y` values are averaged.

    The keyword arguments are those of the CSV reader (`pandas.read_csv`).

    e.g.
    function_from_file(
        "resources/calibration/aom_calibration.dat",
        names=["voltage", "transparency"],
        sep=r"\s+",
    ),
    """
    _, rows = _read_calibration(path, read_csv__args)
    i__x, i__y = indices__column

    # Deal with possible x-duplicates: the mean `y` of each distinct `x`, in ascending `x`.
    x, inverse = np.unique(rows[:, i__x], return_inverse=True)
    y = np.bincount(inverse, weights=rows[:, i__y]) / np.bincount(inverse)

    # The columns are named by `indices__column` in the file's own order. They used to be
    # taken by position from the averaged frame, in which the grouped column had moved to
    # the front, so `[1, 0]` gave `x` twice and the "inverse" was the identity function.
    return interp1d(x, y, kind=method, fill_value=fill_value)
