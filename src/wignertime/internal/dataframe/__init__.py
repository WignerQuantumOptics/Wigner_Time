# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Every operation the package performs on a timeline, behind one interface.

A timeline is a table. Which library holds it is chosen by the environment variable
`WIGNERTIME_BACKEND`, read once, when the package is first imported:

- `pandas` (the default): a timeline is a `pandas.DataFrame`.
- `pandas-strict`: the same, except that package code outside this namespace may not
  touch a timeline directly. Any attempt raises `BackendLeak`, naming the line. This is
  how the test suite proves that `INTERFACE` is the whole of what the package needs.
- `polars`: a timeline is a `polars.DataFrame`. Not implemented yet; every operation
  raises `NotImplementedError` naming itself, so a run of the suite lists what is left.

The interface speaks only in frames, column names, row *positions* and numpy arrays.
Masks are numpy boolean arrays, aligned with the frame by position. Nothing depends on a
row label, because polars has none.
"""

import importlib
import os

INTERFACE = (
    "CLASS",
    # construction, types and combination
    "new",
    "new_schema",
    "cast",
    "concat",
    "join",
    "is_frame",
    # shape and columns
    "columns",
    "has_columns",
    "n_rows",
    "is_empty",
    "column",
    "unique",
    "select",
    "drop_columns",
    "with_column",
    "rename_columns",
    # rows
    "filter",
    "take",
    "row",
    "rows",
    "group_by",
    "sort",
    "drop_duplicates",
    "duplicated",
    "insert_dataframes",
    "align_to",
    "row_from_max_column",
    "subframe",
    "increment_selected_rows",
    "replace_column__filtered",
    "mask__changed",
    # values
    "isnull",
    "not_numeric",
    "is_column_float",
    "normalise_nulls",
    # files
    "read_pickle",
    "read_csv",
    "read_json",
    "read_parquet",
    "read_feather",
    "write_pickle",
    "write_csv",
    "write_json",
    "write_parquet",
    "write_feather",
    # tests
    "assert_equal",
    "assert_series_equal",
)

BACKENDS = {"pandas": "_pandas", "pandas-strict": "_strict", "polars": "_polars"}

BACKEND = os.environ.get("WIGNERTIME_BACKEND", "pandas")
if BACKEND not in BACKENDS:
    raise ValueError(
        f"WIGNERTIME_BACKEND={BACKEND!r} is not a backend; choose one of {sorted(BACKENDS)}."
    )

_implementation = importlib.import_module("." + BACKENDS[BACKEND], __name__)

globals().update(
    {
        name: getattr(_implementation, name)
        for name in INTERFACE
        if hasattr(_implementation, name)
    }
)


def __getattr__(name):
    if name in INTERFACE:
        raise NotImplementedError(
            f"`wt_frame.{name}` has no implementation for the {BACKEND!r} backend yet."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
