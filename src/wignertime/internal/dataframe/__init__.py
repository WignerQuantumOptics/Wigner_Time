# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Every operation the package performs on a timeline, behind one interface.

A timeline is a table. Which library holds it is chosen by the environment variable
`WIGNERTIME_BACKEND`, read once, when the package is first imported:

- `pandas`: a timeline is a `pandas.DataFrame`.
- `polars`: a timeline is a `polars.DataFrame`.
- `pandas-strict`: pandas, except that package code outside this namespace may not touch
  a timeline directly. Any attempt raises `BackendLeak`, naming the line. This is how the
  test suite proves that `INTERFACE` is the whole of what the package needs.

Unset, it is pandas if pandas is installed and polars otherwise. At least one of the two
must be: `pip install wigner-time[pandas]` or `wigner-time[polars]`.

One implementation serves both libraries (`_narwhals`). A frame of the other library is
converted to the active one where it enters (`own`), so a pandas table given to a polars
session works, and comes back as polars.

The interface speaks only in frames, column names, row *positions* and numpy arrays.
Masks are numpy boolean arrays, aligned with the frame by position. Nothing depends on a
row label, because polars has none.
"""

import importlib
import importlib.util
import os

INTERFACE = (
    "CLASS",
    # construction, types and combination
    "own",
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
    "copy",
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
)

# backend: (library, implementation module)
BACKENDS = {
    "pandas": ("pandas", "_narwhals"),
    "polars": ("polars", "_narwhals"),
    "pandas-strict": ("pandas", "_strict"),
}


def _installed(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


BACKEND = os.environ.get("WIGNERTIME_BACKEND") or (
    "pandas" if _installed("pandas") else "polars"
)
if BACKEND not in BACKENDS:
    raise ValueError(
        f"WIGNERTIME_BACKEND={BACKEND!r} is not a backend; choose one of {sorted(BACKENDS)}."
    )
LIBRARY, _module = BACKENDS[BACKEND]
if not _installed(LIBRARY):
    raise ImportError(
        "Wigner Time keeps its timelines in pandas or polars, and {} is not installed."
        " Install one of them: `pip install wigner-time[pandas]` or"
        " `pip install wigner-time[polars]`{}.".format(
            LIBRARY,
            (
                ""
                if os.environ.get("WIGNERTIME_BACKEND") is None
                else ", or unset WIGNERTIME_BACKEND={}".format(BACKEND)
            ),
        )
    )

importlib.import_module("._narwhals", __name__).use(LIBRARY)
_implementation = importlib.import_module("." + _module, __name__)

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
