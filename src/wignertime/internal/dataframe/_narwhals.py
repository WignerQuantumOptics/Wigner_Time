# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Every operation of `wt_frame.INTERFACE`, once, for pandas and polars alike.

The generic work -- selecting, joining, slicing, reading columns out, converting between
the libraries -- goes through narwhals. The package's own rules do not, because neither
library keeps them by default and narwhals does not add them:

- `sort` is stable. pandas sorts one column by quicksort, polars does not keep the order
  of ties either, and narwhals passes both through. Among a variable's rows at one
  instant the one written last is in effect (A18), so ties are broken here on the
  position a row was written at.
- `group_by` gives its groups in the order their keys first appear, and a null key is a
  group of its own.
- `drop_duplicates` and `duplicated` keep the *last* row of each key, and treat nulls as
  equal, as pandas does.

What cannot be written generically is in a small adapter per library (`_Pandas`,
`_Polars`): building a frame from Python data, casting to a schema, stacking frames whose
columns differ, the file formats, and comparing two frames in tests. The pandas adapter is
what the package did before, so the pandas backend behaves as it always has.

Conventions, which every function keeps: a mask is a numpy boolean array aligned with the
frame by position; a column read out is a numpy array; a row is a `dict`; rows are
addressed by position, never by label; every function returns a new frame and leaves its
arguments alone.

A frame of the other library is converted to the active one wherever it enters (`own`),
so a pandas table handed to a polars session, or the reverse, works and comes back in the
active library. The conversion is by column, through numpy, and keeps Python objects
(ramp functions, calibration functions) as they are.
"""

from collections.abc import Callable, Iterable
import math
import pickle

import narwhals as nw
import numpy as np

_POSITION = "__position__wt_frame"
_PICKLE_MARKER = "__wignertime_frame__"

_adapter = None  # set by `use`
CLASS = None


# ============================================================
# MISSING VALUES AND NUMBERS, WITHOUT EITHER LIBRARY
# ============================================================
def _isnull_scalar(o) -> bool:
    if o is None:
        return True
    if isinstance(o, (float, np.floating)):
        return math.isnan(o)
    # pandas' own missing markers, should one arrive from a pandas frame.
    return type(o).__name__ in ("NAType", "NaTType")


def isnull(o):
    """
    Whether `o` is missing -- `None`, NaN, or pandas' `NA`/`NaT` -- elementwise for an
    array or list, as a numpy boolean array, and as a `bool` for a scalar.
    """
    if isinstance(o, (np.ndarray, list, tuple)):
        array = (
            np.asarray(o) if isinstance(o, np.ndarray) else np.asarray(o, dtype=object)
        )
        if array.dtype.kind in "fc":
            return np.isnan(array)
        if array.dtype.kind in "iub":
            return np.zeros(array.shape, dtype=bool)
        return np.array([_isnull_scalar(x) for x in array.ravel()], dtype=bool).reshape(
            array.shape
        )
    return _isnull_scalar(o)


def _as_number(x):
    """`x` as a float, or None if it is not a number (or a missing one)."""
    if isinstance(x, (str, bytes)):
        try:
            x = float(x)
        except ValueError:
            return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def not_numeric(values) -> np.ndarray:
    """
    A boolean mask of the entries of `values` (an array) that cannot be read as a number.
    A missing value is not a number.
    """
    array = (
        np.asarray(values)
        if isinstance(values, np.ndarray)
        else np.asarray(values, dtype=object)
    )
    if array.dtype.kind in "iub":
        return np.zeros(array.shape, dtype=bool)
    if array.dtype.kind == "f":
        return np.isnan(array)
    return np.array([_as_number(x) is None for x in array.ravel()], dtype=bool).reshape(
        array.shape
    )


def _key(x):
    """A value made usable as a dictionary key, with every missing value the same key."""
    return None if _isnull_scalar(x) else x


def _infer(values: np.ndarray):
    """
    The kind of column an object array holds: 'bool', 'int', 'float', 'str' or 'object',
    as pandas would read it. Ints and floats together are 'float', and so is an int column
    with a missing value. Missing values do not otherwise decide it; a column of nothing
    but missing values is 'float'.
    """
    kinds = set()
    missing = False
    for x in values:
        if _isnull_scalar(x):
            missing = True
            continue
        if isinstance(x, (bool, np.bool_)):
            kinds.add("bool")
        elif isinstance(x, (int, np.integer)):
            kinds.add("int")
        elif isinstance(x, (float, np.floating)):
            kinds.add("float")
        elif isinstance(x, str):
            kinds.add("str")
        else:
            return "object"
    if kinds <= {"int", "float"}:
        return "int" if kinds == {"int"} and not missing else "float"
    return kinds.pop() if len(kinds) == 1 else "object"


# ============================================================
# ADAPTERS
# ============================================================
class _Pandas:
    name = "pandas"

    def __init__(self):
        import pandas as pd

        self.pd = pd
        self.CLASS = pd.DataFrame

    def owns(self, df):
        return isinstance(df, self.pd.DataFrame)

    def new(self, data, columns=None):
        return self.pd.DataFrame(data, columns=columns)

    def from_columns(self, columns: dict):
        """A frame from numpy arrays, one per column, kept as they are."""
        return self.pd.DataFrame(
            {name: self.pd.Series(values) for name, values in columns.items()}
        )

    def series(self, values: np.ndarray):
        if values.dtype == object:
            # As pandas itself would read the same Python values.
            return self.pd.Series(list(values), dtype=None).infer_objects()
        return self.pd.Series(values)

    def with_column(self, df, name, values, where=None):
        dff = df.copy()
        if where is None:
            dff[name] = values
        else:
            dff.loc[np.asarray(where, dtype=bool), name] = values
        return dff

    def filter(self, df, mask):
        return df[np.asarray(mask, dtype=bool)].reset_index(drop=True)

    def cast(self, df, schema):
        return df.astype(schema)

    def concat(self, dfs):
        return self.pd.concat(dfs, ignore_index=True)

    def normalise_nulls(self, df):
        dff = df.copy()
        for column in dff.columns:
            if dff[column].dtype == object:
                dff[column] = dff[column].where(dff[column].notna(), np.nan)
        return dff

    def write_pickle(self, df, path):
        df.to_pickle(path)

    def read_pickle(self, path):
        return self.pd.read_pickle(path)

    def write_csv(self, df, path):
        df.to_csv(path, index=False)

    def read_csv(self, path):
        return self.pd.read_csv(path)

    def write_json(self, df, path):
        df.to_json(path, orient="records")

    def read_json(self, path):
        return self.pd.read_json(path)

    def write_parquet(self, df, path):
        df.to_parquet(path, index=False)

    def read_parquet(self, path):
        return self.pd.read_parquet(path)

    def write_feather(self, df, path):
        df.to_feather(path)

    def read_feather(self, path):
        return self.pd.read_feather(path)

    def assert_equal(
        self, df1, df2, check_dtype=True, check_exact=None, rtol=None, atol=None
    ):
        kwargs = {"check_dtype": check_dtype}
        for name, value in (
            ("check_exact", check_exact),
            ("rtol", rtol),
            ("atol", atol),
        ):
            if value is not None:
                kwargs[name] = value
        return self.pd.testing.assert_frame_equal(df1, df2, **kwargs)


class _Polars:
    name = "polars"

    def __init__(self):
        import polars as pl

        self.pl = pl
        self.CLASS = pl.DataFrame
        self.DTYPES = {
            float: pl.Float64,
            int: pl.Int64,
            str: pl.String,
            bool: pl.Boolean,
            np.float64: pl.Float64,
            np.float32: pl.Float32,
            np.int64: pl.Int64,
            np.int32: pl.Int32,
            np.int16: pl.Int16,
            np.int8: pl.Int8,
            object: pl.Object,
        }

    def owns(self, df):
        return isinstance(df, self.pl.DataFrame)

    def series(self, values, name=""):
        """
        A Series of `values`, typed as pandas would read them: numbers (ints and floats
        together) as floats, strings as strings, anything else -- a function, a mixture --
        as Python objects. Missing values are nulls.
        """
        pl = self.pl
        values = (
            np.asarray(values)
            if isinstance(values, np.ndarray)
            else np.asarray(values, dtype=object)
        )
        if values.dtype.kind in "iufb":
            return pl.Series(name, values)
        if values.dtype.kind == "U":
            return pl.Series(name, values.astype(object), dtype=pl.String)
        match _infer(values):
            case "int":
                return pl.Series(name, [int(x) for x in values], dtype=pl.Int64)
            case "float":
                return pl.Series(
                    name,
                    [None if _isnull_scalar(x) else float(x) for x in values],
                    dtype=pl.Float64,
                )
            case "str":
                return pl.Series(
                    name,
                    [None if _isnull_scalar(x) else x for x in values],
                    dtype=pl.String,
                )
            case "bool":
                return pl.Series(
                    name,
                    [None if _isnull_scalar(x) else bool(x) for x in values],
                    dtype=pl.Boolean,
                )
            case _:
                return pl.Series(
                    name,
                    [None if _isnull_scalar(x) else x for x in values],
                    dtype=pl.Object,
                )

    def from_columns(self, columns: dict):
        return self.pl.DataFrame([self.series(v, name) for name, v in columns.items()])

    def new(self, data, columns=None):
        if isinstance(data, dict):
            names = list(data.keys()) if columns is None else list(columns)
            return self.from_columns({n: list(data[n]) for n in names})
        rows = list(data) if not isinstance(data, np.ndarray) else list(data)
        if rows and isinstance(rows[0], dict):
            names = list(rows[0].keys()) if columns is None else list(columns)
            return self.from_columns({n: [r.get(n) for r in rows] for n in names})
        names = (
            list(columns)
            if columns is not None
            else [str(i) for i in range(len(rows[0]) if rows else 0)]
        )
        if not rows:
            return self.pl.DataFrame(
                {n: self.pl.Series(n, [], dtype=self.pl.Null) for n in names}
            )
        for r in rows:
            if len(r) != len(names):
                raise ValueError(
                    "{} columns passed, a row has {}: {!r}".format(
                        len(names), len(r), r
                    )
                )
        return self.from_columns({n: [r[i] for r in rows] for i, n in enumerate(names)})

    def with_column(self, df, name, values, where=None):
        n = df.height
        if where is None:
            if np.ndim(values) == 0 or callable(values):
                if (
                    isinstance(values, (int, float, str, bool, np.generic))
                    or values is None
                ):
                    full = np.asarray([values] * n, dtype=object)
                else:
                    full = np.empty(n, dtype=object)
                    full[:] = [values] * n
            else:
                full = (
                    np.asarray(values)
                    if isinstance(values, np.ndarray)
                    else np.asarray(list(values), dtype=object)
                )
        else:
            mask = np.asarray(where, dtype=bool)
            if name in df.columns:
                full = df[name].to_numpy().astype(object).copy()
            else:
                full = np.full(n, None, dtype=object)
            if np.ndim(values) == 0 or callable(values):
                selected = np.empty(int(mask.sum()), dtype=object)
                selected[:] = [values] * int(mask.sum())
            else:
                selected = np.asarray(list(values), dtype=object)
            full[mask] = selected
        return df.with_columns(self.series(full, name))

    def filter(self, df, mask):
        return df.filter(self.pl.Series(np.asarray(mask, dtype=bool)))

    def cast(self, df, schema):
        pl = self.pl
        out = df
        for name, kind in schema.items():
            dtype = self.DTYPES.get(kind, kind)
            if dtype is pl.Object or out.schema[name] == dtype:
                continue
            try:
                out = out.with_columns(out[name].cast(dtype, strict=True))
            except Exception:
                # From Python objects: read each one as the type asks, as `astype` does.
                convert = {pl.String: str, pl.Boolean: bool}.get(
                    dtype, float if dtype in (pl.Float64, pl.Float32) else int
                )
                values = [
                    None if _isnull_scalar(x) else convert(x)
                    for x in out[name].to_list()
                ]
                out = out.with_columns(pl.Series(name, values, dtype=dtype))
        return out

    def concat(self, dfs):
        pl = self.pl
        dfs = list(dfs)
        # A column holding Python objects in one frame and nothing but nulls in another
        # is still one column of objects.
        objects = {n for df in dfs for n, t in df.schema.items() if t == pl.Object}
        if objects:
            dfs = [
                df.with_columns(
                    [
                        pl.Series(n, df[n].to_list(), dtype=pl.Object)
                        for n in objects
                        if n in df.columns and df.schema[n] != pl.Object
                    ]
                )
                for df in dfs
            ]
        return pl.concat(dfs, how="diagonal_relaxed")

    def normalise_nulls(self, df):
        pl = self.pl
        objects = [n for n, t in df.schema.items() if t == pl.Object]
        if not objects:
            return df
        return df.with_columns(
            [
                pl.Series(
                    n,
                    [None if _isnull_scalar(x) else x for x in df[n].to_list()],
                    dtype=pl.Object,
                )
                for n in objects
            ]
        )

    def write_pickle(self, df, path):
        # polars cannot pickle a column of Python objects, which a timeline's `function`
        # column is, so the columns are pickled as lists and the frame rebuilt on reading.
        with open(path, "wb") as f:
            pickle.dump(
                {
                    _PICKLE_MARKER: 1,
                    "columns": {n: df[n].to_list() for n in df.columns},
                    "schema": {n: str(t) for n, t in df.schema.items()},
                },
                f,
            )

    def read_pickle(self, path):
        with open(path, "rb") as f:
            return pickle.load(f)

    def _strings_for_text(self, df):
        """Python-object columns written as text, which neither CSV nor JSON can hold."""
        pl = self.pl
        objects = [n for n, t in df.schema.items() if t == pl.Object]
        return df.with_columns(
            [
                pl.Series(
                    n,
                    [None if _isnull_scalar(x) else str(x) for x in df[n].to_list()],
                    dtype=pl.String,
                )
                for n in objects
            ]
        )

    def write_csv(self, df, path):
        self._strings_for_text(df).write_csv(path)

    def read_csv(self, path):
        return self.pl.read_csv(path)

    def write_json(self, df, path):
        self._strings_for_text(df).write_json(path)

    def read_json(self, path):
        return self.pl.read_json(path)

    def write_parquet(self, df, path):
        df.write_parquet(path)

    def read_parquet(self, path):
        return self.pl.read_parquet(path)

    def write_feather(self, df, path):
        df.write_ipc(path)

    def read_feather(self, path):
        return self.pl.read_ipc(path)

    def assert_equal(
        self, df1, df2, check_dtype=True, check_exact=None, rtol=None, atol=None
    ):
        _assert_equal__generic(
            df1,
            df2,
            check_dtype=check_dtype,
            check_exact=check_exact,
            rtol=rtol,
            atol=atol,
        )


_ADAPTERS = {"pandas": _Pandas, "polars": _Polars}


def use(library: str):
    """Make `library` ('pandas' or 'polars') the one every frame is built in."""
    global _adapter, CLASS
    _adapter = _ADAPTERS[library]()
    CLASS = _adapter.CLASS


def library() -> str:
    return _adapter.name


# ============================================================
# CONVERSION
# ============================================================
def is_frame(o) -> bool:
    """A pandas or a polars frame, whichever library is active."""
    return isinstance(
        nw.from_native(o, eager_only=True, pass_through=True), nw.DataFrame
    )


def own(df):
    """
    `df` in the active library: unchanged if it is already, converted by column if it is
    a frame of the other one. Anything else is refused, naming what arrived.
    """
    if _adapter.owns(df):
        return df
    if not is_frame(df):
        raise TypeError(
            "Expected a dataframe ({}), got {}.".format(
                _adapter.name, type(df).__name__
            )
        )
    frame = nw.from_native(df, eager_only=True)
    return _adapter.from_columns({n: frame[n].to_numpy() for n in frame.columns})


def _nw(df):
    return nw.from_native(own(df), eager_only=True)


# ============================================================
# CONSTRUCTION, TYPES AND COMBINATION
# ============================================================
def new(data, columns: list | None = None):
    if columns is not None:
        columns = list(columns)
    return _adapter.new(data, columns=columns)


def cast(df, col_type: dict):
    """
    Coerces column types according to the given schema (`col_type`).

    First, restricts the schema to match what is relevant to the dataframe.
    """
    df = own(df)
    present = set(columns(df))
    return _adapter.cast(df, {k: v for k, v in col_type.items() if k in present})


def new_schema(data, schema: dict):
    """
    Makes another dataframe using `new`, but where the schema parameter provides some convenience.
    """
    return cast(new(data, list(schema.keys())), schema)


def concat(dfs, ignore_index=True):
    """
    The frames one after another. A column missing from one of them is null there.
    """
    return _adapter.concat([own(df) for df in dfs])


def join(df1, df2, label="variable"):
    """
    `df1` with the columns of `df2` added, matched on `label`, in the order of `df1`. A
    row of `df1` with no match gets nulls. A column other than `label` present in both is
    refused rather than suffixed, as pandas' `join` refused it.
    """
    left, right = _nw(df1), _nw(df2)
    overlap = (set(left.columns) & set(right.columns)) - {label}
    if overlap:
        raise ValueError(
            "columns overlap but no suffix specified: {}".format(sorted(overlap))
        )
    joined = (
        left.with_row_index(_POSITION)
        .join(right, on=label, how="left")
        .sort(_POSITION)
        .drop(_POSITION)
    )
    return nw.to_native(joined)


# ============================================================
# SHAPE AND COLUMNS
# ============================================================
def columns(df) -> list[str]:
    return list(_nw(df).columns)


def has_columns(df, names: Iterable[str]) -> bool:
    return set(names).issubset(columns(df))


def n_rows(df) -> int:
    return len(_nw(df))


def is_empty(df) -> bool:
    """
    No rows (or no columns, as a frame with neither holds no data either).
    """
    frame = _nw(df)
    return len(frame) == 0 or len(frame.columns) == 0


def column(df, name: str, dtype=None) -> np.ndarray:
    """
    The column `name` as a numpy array, in row order. Missing numbers are NaN; missing
    strings and objects are None or NaN, which `isnull` treats alike.
    """
    values = _nw(df)[name].to_numpy()
    if values.dtype.kind == "U":
        # Python strings, as pandas gives them, not numpy's.
        values = values.astype(object)
    return values if dtype is None else values.astype(dtype)


_column = column  # for the functions below whose parameter is called `column`


def unique(df, name: str) -> list:
    """
    The distinct values of `name`, in the order they first appear.
    """
    seen = {}
    for x in column(df, name):
        seen.setdefault(_key(x), x)
    return list(seen.values())


def copy(df):
    """
    A new frame with the same content. Nothing in the package needs one, since nothing
    writes into a frame; a test that checks a frame was left alone does.
    """
    return take(df, range(n_rows(df)))


def select(df, names: Iterable[str]):
    return nw.to_native(_nw(df).select(list(names)))


def drop_columns(df, names: Iterable[str]):
    return nw.to_native(_nw(df).drop(list(names)))


def rename_columns(df, mapping: dict):
    return nw.to_native(_nw(df).rename(mapping))


def with_column(df, name: str, values, where=None):
    """
    A copy of `df` with column `name` set to `values`: a scalar, or one value per row.

    With a mask `where`, only those rows are set, and `values` is a scalar or one value
    per selected row; the others keep what they held, or null in a new column.
    """
    return _adapter.with_column(own(df), name, values, where=where)


# ============================================================
# ROWS
# ============================================================
def filter(df, mask):
    """
    The rows where `mask` is True, in order.
    """
    return _adapter.filter(own(df), mask)


def take(df, positions: Iterable[int]):
    """
    The rows at `positions`, in that order.
    """
    positions = [int(p) for p in positions]
    frame = _nw(df)
    if not positions:
        return nw.to_native(frame[0:0])
    return _reset(nw.to_native(frame[positions]))


def _reset(native):
    # pandas keeps the labels of the rows taken; positions are what count here.
    if hasattr(native, "reset_index"):
        return native.reset_index(drop=True)
    return native


def _slice(df, start, stop):
    return _reset(nw.to_native(_nw(df)[start:stop]))


def row(df, position: int) -> dict:
    """
    The row at `position`, as a `dict` from column name to value.
    """
    frame = _nw(df)
    return dict(zip(frame.columns, frame.row(position)))


def rows(df, names: Iterable[str] | None = None) -> list[tuple]:
    """
    Every row as a tuple of the values in `names` (all columns by default), in order.
    """
    frame = _nw(df)
    if names is not None:
        frame = frame.select(list(names))
    return frame.rows()


def _positions_by_key(df, keys) -> dict:
    """{key: [positions]}, keys in first-appearance order, positions ascending."""
    names = [keys] if isinstance(keys, str) else list(keys)
    groups: dict = {}
    for position, values in enumerate(rows(df, names)):
        key = (
            _key(values[0]) if isinstance(keys, str) else tuple(_key(v) for v in values)
        )
        groups.setdefault(key, []).append(position)
    return groups


def group_by(df, keys) -> list[tuple]:
    """
    `(key, rows)` for each distinct value of `keys`, in the order the values first appear.
    `rows` keeps the order of `df`. A null key forms a group of its own.

    `keys` is a column name, giving a scalar key, or a list of them, giving a tuple.
    """
    df = own(df)
    return [
        (key, take(df, positions))
        for key, positions in _positions_by_key(df, keys).items()
    ]


def sort(df, by, ignore_index=True):
    """
    `df` sorted by `by`, as a new frame, and **stably**: rows that tie keep the order
    they were written in. Nulls go last.

    Among a variable's rows at one instant the one written last is in effect, so order
    among ties carries meaning. Neither library keeps it by default, so the position each
    row was written at breaks every tie. Without this, a ramp's end could come after the
    `update` written at the same instant to supersede it, and `drop_duplicates`, which
    keeps the last row of each cycle, would send the ramp's end to the hardware (A18,
    #153).
    """
    by = [by] if isinstance(by, str) else list(by)
    frame = _nw(df).with_row_index(_POSITION)
    return _reset(
        nw.to_native(frame.sort([*by, _POSITION], nulls_last=True).drop(_POSITION))
    )


def _mask__kept(df, subset, keep="last") -> np.ndarray:
    names = (
        columns(df)
        if subset is None
        else ([subset] if isinstance(subset, str) else list(subset))
    )
    keys = [tuple(_key(v) for v in values) for values in rows(df, names)]
    kept = np.zeros(len(keys), dtype=bool)
    seen = set()
    order = range(len(keys) - 1, -1, -1) if keep == "last" else range(len(keys))
    for i in order:
        if keys[i] not in seen:
            seen.add(keys[i])
            kept[i] = True
    return kept


def drop_duplicates(df, subset=None, keep="last"):
    """
    `df` with one row per value of `subset` (all columns by default): the last written,
    or the first with `keep="first"`. Nulls are equal to each other.
    """
    return filter(df, _mask__kept(df, subset, keep=keep))


def duplicated(df, subset=["time", "variable"], keep="last") -> np.ndarray:
    """
    A mask of the rows `drop_duplicates` would drop.
    """
    return ~_mask__kept(df, subset, keep=keep)


def insert_dataframes(df, indices: list[int], dfs: list):
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
    df = own(df)
    # `sorted` is stable, so frames sharing a position keep their order.
    insertions = sorted(zip(indices, dfs), key=lambda x: x[0])

    parts = []
    current = 0
    for index, new_df in insertions:
        parts.append(_slice(df, current, index))
        parts.append(own(new_df))
        current = index
    parts.append(_slice(df, current, n_rows(df)))
    return concat(parts)


def align_to(df, order, column="variable"):
    """
    Returns `df`, one row per entry of `order`, in that order.

    For comparing two frames that hold the same keys in different orders. `order` must
    contain no repeats, and every one of its entries must appear in `df`.
    """
    positions = {}
    for position, key in enumerate(_column(df, column)):
        positions.setdefault(_key(key), position)
    missing = [k for k in order if _key(k) not in positions]
    if missing:
        raise KeyError("{} not in `{}`".format(missing, column))
    return take(df, [positions[_key(k)] for k in order])


def row_from_max_column(df, column="time") -> dict:
    """
    The row holding the maximum of `column`, as a `dict`. Among rows that tie, the last.
    """
    # The last of the ties, as among rows at one instant the one written last is in
    # effect. This avoids subtle bugs in choosing the previous context etc.
    values = _column(df, column)
    return row(df, len(values) - 1 - int(np.argmax(values[::-1])))


def subframe(df, column: str, values: list, func: Callable | None = None):
    """
    Returns a filtered df, where func(`column`) has values in `values`.
    """
    entries = _column(df, column)
    if func:
        entries = [func(x) for x in entries]
    wanted = set(values)
    return filter(df, [x in wanted for x in entries])


def increment_selected_rows(
    df, column__increment="time", column__match="variable", **incs
):
    """
    A copy of `df` in which each row whose `column__match` is a keyword has that keyword's
    increment added to `column__increment`. Keywords are variable=<increment> pairs.
    """
    matches = column(df, column__match)
    values = column(df, column__increment)
    for k, v in incs.items():
        values = np.where(matches == k, values + v, values)
    return with_column(df, column__increment, values)


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

    The column keeps its type. `is_in_place` is accepted and ignored: nothing here writes
    into its argument.
    """
    current = column(df, column__change)
    replaced = np.array(
        [
            (
                dict__replacement[f]
                if f in dict__replacement and not isnull(dict__replacement[f])
                else c
            )
            for f, c in zip(column(df, column__filter), current)
        ],
        dtype=current.dtype,
    )
    return with_column(df, column__change, replaced)


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
    n = n_rows(df)
    changed = np.zeros(n, dtype=bool)
    if n == 0:
        return changed

    values = column(df, column__value)
    order = column(df, column__order)
    for positions in _positions_by_key(df, list(subset)).values():
        positions = sorted(positions, key=lambda p: order[p])  # stable
        changed[positions[0]] = True
        for previous, current in zip(positions, positions[1:]):
            if (
                isnull(values[previous])
                or isnull(values[current])
                or values[current] != values[previous]
            ):
                changed[current] = True
        if do_keep_edges:
            changed[positions[-1]] = True
    return changed


# ============================================================
# VALUES
# ============================================================
def is_column_float(df, name: str) -> bool:
    return _nw(df).schema[name].is_float()


def normalise_nulls(df):
    """
    Give every missing value in a column of Python objects one representation.

    A timeline built in memory with pandas carries `nan` wherever a column does not apply
    -- that is what `concat` leaves behind when a frame without a `function` column is
    joined to one that has it. Round-tripping through parquet, JSON or feather brings
    those back as `None` instead, while CSV and pickle keep `nan`, so a loaded timeline
    was not equal to the one saved and the difference depended on the format chosen. The
    distinction carries no meaning here -- both say "no value" -- so `file.load` settles
    on one: `nan` with pandas, null with polars.
    """
    return _adapter.normalise_nulls(own(df))


# ============================================================
# FILES
# ============================================================
def write_pickle(df, path):
    _adapter.write_pickle(own(df), path)


def write_csv(df, path):
    _adapter.write_csv(own(df), path)


def write_json(df, path):
    _adapter.write_json(own(df), path)


def write_parquet(df, path):
    _adapter.write_parquet(own(df), path)


def write_feather(df, path):
    _adapter.write_feather(own(df), path)


def read_pickle(path):
    """
    A pickled timeline, whichever library pickled it: a pandas frame, or the columns the
    polars backend pickles (a polars frame cannot pickle a column of functions).
    """
    o = _adapter.read_pickle(path)
    if isinstance(o, dict) and _PICKLE_MARKER in o:
        # As lists, so that each column is typed as the library reads those values.
        return _adapter.from_columns({n: list(v) for n, v in o["columns"].items()})
    return own(o)


def read_csv(path):
    return own(_adapter.read_csv(path))


def read_json(path):
    return own(_adapter.read_json(path))


def read_parquet(path):
    return own(_adapter.read_parquet(path))


def read_feather(path):
    return own(_adapter.read_feather(path))


# ============================================================
# TESTS
# ============================================================
def _same(a, b, rtol, atol):
    if isnull(a) and isnull(b):
        return True
    if isnull(a) or isnull(b):
        return False
    numbers = (float, np.floating)
    if rtol is not None and (isinstance(a, numbers) or isinstance(b, numbers)):
        try:
            return a == b or math.isclose(
                float(a), float(b), rel_tol=rtol, abs_tol=atol
            )
        except (TypeError, ValueError):
            return False
    return bool(a == b)


def _assert_equal__generic(
    df1, df2, check_dtype=True, check_exact=None, rtol=None, atol=None
):
    """
    As `pandas.testing.assert_frame_equal` compares: same columns in the same order, same
    rows, nulls equal to nulls, and floats equal to within `rtol` (default 1e-5) relative
    or `atol` (default 1e-8) absolute, unless `check_exact`.
    """
    if check_exact:
        rtol, atol = None, 0.0
    else:
        rtol = 1e-5 if rtol is None else rtol
        atol = 1e-8 if atol is None else atol
    f1, f2 = _nw(df1), _nw(df2)
    assert list(f1.columns) == list(f2.columns), "columns differ: {} != {}".format(
        list(f1.columns), list(f2.columns)
    )
    assert len(f1) == len(f2), "row counts differ: {} != {}".format(len(f1), len(f2))
    for name in f1.columns:
        if check_dtype:
            assert (
                f1.schema[name] == f2.schema[name]
            ), "dtypes of {!r} differ: {} != {}".format(
                name, f1.schema[name], f2.schema[name]
            )
        a, b = f1[name].to_numpy(), f2[name].to_numpy()
        bad = [i for i in range(len(a)) if not _same(a[i], b[i], rtol, atol)]
        assert not bad, "column {!r} differs at rows {}: {!r} != {!r}".format(
            name, bad[:10], a[bad[0]], b[bad[0]]
        )


def assert_equal(df1, df2, check_dtype=True, check_exact=None, rtol=None, atol=None):
    """
    Raises `AssertionError` unless the two frames are equal, as
    `pandas.testing.assert_frame_equal` judges it, on either library.
    """
    return _adapter.assert_equal(
        own(df1),
        own(df2),
        check_dtype=check_dtype,
        check_exact=check_exact,
        rtol=rtol,
        atol=atol,
    )
