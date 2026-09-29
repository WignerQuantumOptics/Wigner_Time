# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

from collections.abc import Callable

# In the medium term, this should have a polars counterpart namespace so that we can switch between the two easily.
from copy import deepcopy

import pandas as pd
from numpy import nan

CLASS = pd.DataFrame


def new(data, columns: list | None = None):
    return pd.DataFrame(data, columns=columns)


def cast(df, col_type: dict):
    """
    Coerces column types according to the given schema (`col_type`).

    First, restricts the schema to match what is relevant to the dataframe.
    """

    return df.astype({k: col_type[k] for k in set(df.columns) if k in col_type.keys()})


def new_schema(data, schema: dict):
    """
    Makes another dataframe using `new`, but where the schema parameter provides some convenience.
    """
    return cast(
        new(
            data,
            list(schema.keys()),
        ),
        schema,
    )


def join(df1, df2, label="variable"):
    return df1.join(
        df2.set_index(label),
        on=label,
    )


def concat(dfs, ignore_index=True):
    return pd.concat(dfs, ignore_index=ignore_index)


def isnull(o):
    """
    Detect missing values for an array-like object.
    """
    return pd.isnull(o)


def not_numeric(column):
    """
    A boolean mask of the entries that cannot be read as a number.
    """
    return pd.to_numeric(column, errors="coerce").isna()


def normalise_nulls(df: CLASS) -> CLASS:
    """
    Give every missing value in an object column the same representation, `nan`.

    A timeline built in memory carries `nan` wherever a column does not apply -- that is
    what `concat` leaves behind when a frame without a `function` column is joined to one
    that has it. Round-tripping through parquet, JSON or feather brings those back as
    `None` instead, while CSV and pickle keep `nan`, so a loaded timeline was not equal to
    the one saved and the difference depended on the format chosen.

    `pandas.testing.assert_frame_equal` currently warns that it will stop treating the two
    as matching, so this would have become an error rather than a warning. The distinction
    carries no meaning here -- both say "no value" -- so `file.load` settles on one.
    """
    dff = df.copy()
    for column in dff.columns:
        if dff[column].dtype == object:
            dff[column] = dff[column].where(dff[column].notna(), nan)
    return dff


def fill_null(df, column: str, value):
    """
    Replace nulls in `column` with `value`, returning a new frame.
    """
    dff = df.copy()
    dff[column] = dff[column].fillna(value)
    return dff


def subframe(df: CLASS, column: str, values: list, func: Callable | None = None):
    """
    Returns a filtered df, where func(`column`) has values in `values`.
    """
    if func:
        return df[df[column].map(func).isin(values)].reset_index(drop=True)

    return df[df[column].isin(values)].reset_index(drop=True)


def align_to(df, order, column="variable"):
    """
    Returns `df`, one row per entry of `order`, in that order.

    For comparing two frames that hold the same keys in different orders. `order` must
    contain no repeats, and every one of its entries must appear in `df`.
    """
    return df.set_index(column).loc[list(order)].reset_index()


def row_from_max_column(df, column="time"):
    """
    Finds the maximum value of the column and returns the corresponding row.
    """
    # The reversal is necessary to ensure that the highest index maximum is returned. This avoids subtle bugs in choosing the previous context etc.
    return df.loc[df[column][::-1].idxmax()]


def increment_selected_rows(
    df, column__increment="time", column__match="variable", in_place=True, **incs
):
    """
    Keywords are variable=<increment> pairs. If none are provided then the original df is returned.
    """
    if incs is not None:
        dff = df if in_place else deepcopy(df)
        for k, v in incs.items():
            dff.loc[dff[column__match] == k, column__increment] += v
        return dff
    else:
        return df


def sort(df: CLASS, by, ignore_index=True) -> CLASS:
    """
    `df` sorted by `by`, as a new frame, and **stably**: rows that tie keep the order
    they were written in.

    Among a variable's rows at one instant the one written last is in effect, so order
    among ties carries meaning. pandas sorts a single column by quicksort unless told
    otherwise, which does not keep it. Before conversion, that put a ramp's end after
    the `update` written at the same instant to supersede it, and `drop_duplicates`,
    which keeps the last row of each cycle, sent the ramp's end to the hardware (A18,
    #153). (A sort on several columns is stable in pandas regardless.)
    """
    return df.sort_values(by=by, kind="stable", ignore_index=ignore_index)


def drop_duplicates(df, subset=None, keep="last"):
    return df.drop_duplicates(subset=subset, keep=keep, ignore_index=True).copy()


def insert_dataframes(df: CLASS, indices: list[int], dfs: list[CLASS]) -> CLASS:
    """
    Inserts each of `dfs` into `df` before the row at the matching *position* in
    `indices` (not a label; `len(df)` appends). Frames given the same position keep the
    order they are given in.

    The positions are in `df` as given. They used to be shifted by the number of rows
    inserted so far, as though `df` grew, while the slices were still cut from the
    original, so every insertion after the first landed that many rows too late: after
    rows written after it (A18).
    """
    if len(indices) != len(dfs):
        raise ValueError("`indices` and `dfs` are different lengths.")
    # `sorted` is stable, so frames sharing a position keep their order.
    insertions = sorted(zip(indices, dfs), key=lambda x: x[0])

    result_parts = []
    current_start = 0

    for index, new_df in insertions:
        result_parts.append(df.iloc[current_start:index])
        result_parts.append(new_df)
        current_start = index

    # Add the remainder of the original DataFrame
    result_parts.append(df.iloc[current_start:])

    # Concatenate all parts into a single DataFrame
    return pd.concat(result_parts, ignore_index=True).reset_index(drop=True)


def duplicated(df, subset=["time", "variable"], keep="last"):
    return df.duplicated(subset=subset, keep=keep)


def mask__changed(
    df,
    subset: list,
    column__value: str,
    column__order: str,
    do_keep_edges: bool = True,
):
    """
    A boolean mask, index-aligned with `df`, that is True where `column__value` differs from the previous row of the same `subset` group, once that group is ordered by `column__order`.

    The first row of every group is always True, as it has no predecessor. When `do_keep_edges`, the last row of every group is True as well, so that the temporal extent of each group survives any filtering built on this mask.

    NOTE: Requires a unique index, which is the case for every frame produced by the ADwin conversion chain.
    """
    if df.empty:
        return pd.Series(dtype=bool, index=df.index)

    ordered = df.sort_values(by=list(subset) + [column__order], kind="stable")
    grouped = ordered.groupby(list(subset), sort=False)[column__value]

    value__previous = grouped.shift()
    changed = ordered[column__value].ne(value__previous) | value__previous.isna()

    if do_keep_edges:
        changed = changed | grouped.shift(-1).isna()

    return changed.reindex(df.index, fill_value=False).astype(bool)


def replace_column__filtered(
    df,
    dict__replacement,
    column__change="time",
    column__filter="context",
    is_in_place=False,
):
    """
    Replaces all values of `column__change` with the corresponding dictionary values, for which the rows match the keys of column__filter.

    e.g. Replaces the `time` values with the numbers in {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1} according to which `context`s the rows are specified for.
    """
    if not is_in_place:
        dff = deepcopy(df)
    else:
        dff = df

    dff[column__change] = (
        dff[column__filter]
        .map(dict__replacement)
        .fillna(dff[column__change])
        .astype(df[column__change].dtype)
    )

    return dff


def for_input(df):
    """
    For printing frames in a format that can be pasted as an input.
    """
    rows = df.values.tolist()
    col_names = df.columns.tolist()

    source = "pd.DataFrame([\n"
    for row in rows:
        source += f"    {row},\n"
    source += "], columns={})".format(col_names)
    return source


def read_pickle(path):
    return pd.read_pickle(path)


def read_csv(path):
    return pd.read_csv(path)


def read_json(path):
    return pd.read_json(path)


def read_parquet(path):
    return pd.read_parquet(path)


def read_feather(path):
    return pd.read_feather(path)


# ============================================================
# PREDICATES
# ============================================================
def is_column_string(col):
    """
    Does the selected column only contain strings?
    """
    return col.dtype == "string" or bool(col.map(lambda x: isinstance(x, str)).all())


def is_column_float(col):
    return pd.api.types.is_float_dtype(col)


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)


def assert_series_equal(s1, s2):
    return pd.testing.assert_series_equal(s1, s2)
