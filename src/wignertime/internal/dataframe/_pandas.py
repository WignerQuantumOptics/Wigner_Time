# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The pandas backend: every operation of `wt_frame.INTERFACE`, on a `pandas.DataFrame`.

Some of these carry one of the package's rules, which plain pandas would get subtly
wrong: `sort` is stable, because among rows that share an instant the one written last is
in effect (A18); `drop_duplicates` keeps that last row; `insert_dataframes` inserts by
position; `mask__changed`, `normalise_nulls` and `row_from_max_column` each settle a
question pandas leaves open. The rest are thin, so that no other module of the package
needs to know which library holds a timeline.

Conventions, which every backend keeps: a mask is a numpy boolean array aligned with the
frame by position; a column read out is a numpy array; a row is a `dict`; rows are
addressed by position, never by label; every function returns a new frame and leaves its
arguments alone, except where a name says `in_place`.
"""

from collections.abc import Callable, Iterable
from copy import deepcopy

import numpy as np
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


def is_frame(o) -> bool:
    return isinstance(o, CLASS)


# ============================================================
# SHAPE AND COLUMNS
# ============================================================
def columns(df) -> list[str]:
    return list(df.columns)


def has_columns(df, names: Iterable[str]) -> bool:
    return set(names).issubset(df.columns)


def n_rows(df) -> int:
    return len(df)


def is_empty(df) -> bool:
    """
    No rows (or no columns, as a frame with neither holds no data either).
    """
    return df.empty


def column(df, name: str, dtype=None) -> np.ndarray:
    """
    The column `name` as a numpy array, in row order.
    """
    return df[name].to_numpy(dtype=dtype)


def unique(df, name: str) -> list:
    """
    The distinct values of `name`, in the order they first appear.
    """
    return list(pd.unique(df[name].to_numpy()))


def select(df, names: Iterable[str]):
    return df[list(names)].copy()


def drop_columns(df, names: Iterable[str]):
    return df.drop(columns=list(names))


def rename_columns(df, mapping: dict):
    return df.rename(columns=mapping)


def with_column(df, name: str, values, where=None):
    """
    A copy of `df` with column `name` set to `values`: a scalar, or one value per row.

    With a mask `where`, only those rows are set, and `values` is a scalar or one value
    per selected row; the others keep what they held, or null in a new column.
    """
    dff = df.copy()
    if where is None:
        dff[name] = values
    else:
        dff.loc[np.asarray(where, dtype=bool), name] = values
    return dff


# ============================================================
# ROWS
# ============================================================
def filter(df, mask):
    """
    The rows where `mask` is True, in order.
    """
    return df[np.asarray(mask, dtype=bool)].reset_index(drop=True)


def take(df, positions: Iterable[int]):
    """
    The rows at `positions`, in that order.
    """
    return df.iloc[list(positions)].reset_index(drop=True)


def row(df, position: int) -> dict:
    """
    The row at `position`, as a `dict` from column name to value.
    """
    return df.iloc[position].to_dict()


def rows(df, names: Iterable[str] | None = None) -> list[tuple]:
    """
    Every row as a tuple of the values in `names` (all columns by default), in order.
    """
    dff = df if names is None else df[list(names)]
    return list(dff.itertuples(index=False, name=None))


def group_by(df, keys) -> list[tuple]:
    """
    `(key, rows)` for each distinct value of `keys`, in the order the values first appear.
    `rows` keeps the order of `df`. A null key forms a group of its own, rather than
    being dropped as pandas would by default.

    `keys` is a column name, giving a scalar key, or a list of them, giving a tuple.
    """
    return [
        (key, group.reset_index(drop=True))
        for key, group in df.groupby(keys, sort=False, dropna=False)
    ]


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


def not_numeric(values) -> np.ndarray:
    """
    A boolean mask of the entries of `values` (an array) that cannot be read as a number.
    """
    return pd.isna(pd.to_numeric(np.asarray(values, dtype=object), errors="coerce"))


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


def row_from_max_column(df, column="time") -> dict:
    """
    The row holding the maximum of `column`, as a `dict`. Among rows that tie, the last.
    """
    # The last of the ties, as among rows at one instant the one written last is in
    # effect. This avoids subtle bugs in choosing the previous context etc.
    values = df[column].to_numpy()
    return row(df, len(values) - 1 - int(np.argmax(values[::-1])))


def increment_selected_rows(
    df, column__increment="time", column__match="variable", **incs
):
    """
    A copy of `df` in which each row whose `column__match` is a keyword has that keyword's
    increment added to `column__increment`. Keywords are variable=<increment> pairs.
    """
    dff = deepcopy(df)
    for k, v in incs.items():
        dff.loc[dff[column__match] == k, column__increment] += v
    return dff


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


def duplicated(df, subset=["time", "variable"], keep="last") -> np.ndarray:
    return df.duplicated(subset=subset, keep=keep).to_numpy()


def mask__changed(
    df,
    subset: list,
    column__value: str,
    column__order: str,
    do_keep_edges: bool = True,
):
    """
    A boolean mask, aligned with `df` by position, that is True where `column__value` differs from the previous row of the same `subset` group, once that group is ordered by `column__order`.

    The first row of every group is always True, as it has no predecessor. When `do_keep_edges`, the last row of every group is True as well, so that the temporal extent of each group survives any filtering built on this mask.

    """
    if df.empty:
        return np.zeros(0, dtype=bool)

    df = df.reset_index(drop=True)
    ordered = df.sort_values(by=list(subset) + [column__order], kind="stable")
    grouped = ordered.groupby(list(subset), sort=False)[column__value]

    value__previous = grouped.shift()
    changed = ordered[column__value].ne(value__previous) | value__previous.isna()

    if do_keep_edges:
        changed = changed | grouped.shift(-1).isna()

    return changed.reindex(df.index, fill_value=False).to_numpy(dtype=bool)


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


def write_pickle(df, path):
    df.to_pickle(path)


def write_csv(df, path):
    df.to_csv(path, index=False)


def write_json(df, path):
    df.to_json(path, orient="records")


def write_parquet(df, path):
    df.to_parquet(path, index=False)


def write_feather(df, path):
    df.to_feather(path)


def read_pickle(path, unpickler=None):
    """
    The frame pickled at `path`. `unpickler`, a `pickle.Unpickler` subclass, is how the
    pickle is read when given: `io.file` uses one to find functions under modules that
    have since moved.
    """
    if unpickler is None:
        return pd.read_pickle(path)
    with open(path, "rb") as f:
        return unpickler(f).load()


def read_csv(path, **options):
    """`pandas.read_csv(path, **options)`: `options` are the library's own."""
    return pd.read_csv(path, **options)


def read_json(path):
    return pd.read_json(path)


def read_parquet(path):
    return pd.read_parquet(path)


def read_feather(path):
    return pd.read_feather(path)


# ============================================================
# PREDICATES
# ============================================================
def is_column_float(df, name: str) -> bool:
    return pd.api.types.is_float_dtype(df[name])


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)


def assert_series_equal(s1, s2):
    return pd.testing.assert_series_equal(s1, s2)
