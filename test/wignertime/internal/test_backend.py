"""
The dataframe backend: `wt_frame.INTERFACE` is the contract, one implementation keeps it
for pandas and polars, and `pandas-strict` checks that the package keeps to it.

The order rules are tested here on whichever library the suite runs on, since neither
library keeps them by default.
"""

import os
import subprocess
import sys

import numpy as np
import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal.dataframe import _narwhals


def _python(code, backend=None):
    env = dict(os.environ)
    env.pop("WIGNERTIME_STRICT_LOG", None)
    env.pop("WIGNERTIME_BACKEND", None)
    if backend is not None:
        env["WIGNERTIME_BACKEND"] = backend
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )


# --- the contract --------------------------------------------------------------------


def test_the_implementation_covers_the_whole_interface():
    assert [name for name in wt_frame.INTERFACE if not hasattr(_narwhals, name)] == []


def test_the_implementation_offers_nothing_outside_the_interface():
    """
    A helper defined in the implementation but missing from `INTERFACE` would be reachable
    only by importing the implementation directly, which is how a second path around the
    interface would start. `use` and `library` configure it, and are not operations.
    """
    defined = {
        name
        for name, value in vars(_narwhals).items()
        if not name.startswith("_")
        and callable(value)
        and getattr(value, "__module__", None) == _narwhals.__name__
    }
    assert defined - set(wt_frame.INTERFACE) == {"use", "library"}


def test_every_frame_is_built_in_the_active_library():
    frame = wt_frame.new(
        [[0.0, "x", 1.0, "c"]], columns=["time", "variable", "value", "context"]
    )
    assert isinstance(frame, wt_frame.CLASS)
    assert wt_frame.CLASS.__module__.split(".")[0] == wt_frame.LIBRARY


def test_an_unknown_backend_is_refused():
    result = _python("import wignertime.internal.dataframe", "nonsense")
    assert result.returncode != 0
    assert "is not a backend" in result.stderr


_WITHOUT_EITHER = """
import importlib.abc, sys
class Absent(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("pandas", "polars"):
            raise ModuleNotFoundError(name)
sys.meta_path.insert(0, Absent())
import wignertime.internal.dataframe
"""


def test_without_pandas_or_polars_the_package_says_which_to_install():
    result = _python(_WITHOUT_EITHER)
    assert result.returncode != 0
    assert (
        "wigner-time[pandas]" in result.stderr
        and "wigner-time[polars]" in result.stderr
    )


# --- the other library ---------------------------------------------------------------


def _foreign(rows, columns):
    other = "polars" if wt_frame.LIBRARY == "pandas" else "pandas"
    module = pytest.importorskip(other)
    if other == "pandas":
        return module.DataFrame(rows, columns=columns)
    return module.DataFrame(rows, schema=columns, orient="row")


def test_a_frame_of_the_other_library_is_converted_where_it_enters():
    onto = _foreign(
        [[0.0, "coil__A", 1.0, "init"]], ["time", "variable", "value", "context"]
    )
    timeline = tl.to_timeline(tl.update(coil__A=2.0, time=1.0), onto=onto)
    assert isinstance(timeline, wt_frame.CLASS)
    assert list(wt_frame.column(timeline, "value")) == [1.0, 2.0]
    assert list(wt_frame.column(timeline, "context")) == ["init", "init"]


# --- the order rules -------------------------------------------------------------------

_TIES = [
    [1.0, "a", 1.0],
    [0.0, "b", 2.0],
    [1.0, "c", 3.0],
    [0.0, "d", 4.0],
    [1.0, "e", 5.0],
] * 40  # enough rows that an unstable sort would reorder the ties


def _ties():
    return wt_frame.new(_TIES, columns=["time", "variable", "value"])


def test_sort_keeps_the_written_order_among_ties():
    ordered = wt_frame.sort(_ties(), "time")
    expected = [
        r[1] for r in sorted(_TIES, key=lambda r: r[0])
    ]  # Python's sort is stable
    assert list(wt_frame.column(ordered, "variable")) == expected


def test_group_by_gives_groups_in_first_appearance_order_and_rows_in_written_order():
    frame = wt_frame.new(
        [["y", 1], ["x", 2], ["y", 3], [None, 4], ["x", 5]], columns=["k", "v"]
    )
    groups = [
        (k, list(wt_frame.column(g, "v"))) for k, g in wt_frame.group_by(frame, "k")
    ]
    assert groups == [("y", [1, 3]), ("x", [2, 5]), (None, [4])]


def test_drop_duplicates_keeps_the_row_written_last():
    frame = wt_frame.new(
        [[0.0, "x", 1.0], [0.0, "x", 2.0], [1.0, "x", 3.0], [0.0, "x", 4.0]],
        columns=["time", "variable", "value"],
    )
    kept = wt_frame.drop_duplicates(frame, subset=["time", "variable"])
    assert list(wt_frame.column(kept, "value")) == [3.0, 4.0]
    assert list(wt_frame.duplicated(frame, subset=["time", "variable"])) == [
        True,
        True,
        False,
        False,
    ]


def test_masks_are_numpy_and_aligned_by_position():
    mask = wt_frame.duplicated(_ties(), subset=["time"])
    assert (
        isinstance(mask, np.ndarray) and mask.dtype == bool and len(mask) == len(_TIES)
    )


def test_a_column_of_functions_survives_building_and_stacking():
    def f(o, t):
        return 0

    frame = wt_frame.with_column(
        _ties(), "function", f, where=np.arange(len(_TIES)) < 2
    )
    stacked = wt_frame.concat([frame, _ties()])
    functions = wt_frame.column(stacked, "function")
    assert functions[0] is f and functions[1] is f
    assert wt_frame.isnull(functions[2:]).all()


# --- the strict backend ----------------------------------------------------------------


@pytest.fixture
def strict():
    if wt_frame.LIBRARY != "pandas":
        pytest.skip("the strict backend is pandas")
    from wignertime.internal.dataframe import _strict

    if _strict._LOG is not None:
        pytest.skip("the census logs rather than raises")
    return _strict


def _as_package_code(expression, frame):
    return eval(
        compile(expression, "<package code>", "eval"),
        {"__name__": "wignertime.somewhere", "frame": frame},
    )


@pytest.mark.parametrize(
    "expression", ["frame['a']", "frame.empty", "frame.loc[0]", "list(frame)"]
)
def test_strict_refuses_package_code_that_touches_a_frame(strict, expression):
    frame = strict.new([[1, 2]], columns=["a", "b"])
    with pytest.raises(strict.BackendLeak, match="wignertime.somewhere"):
        _as_package_code(expression, frame)


def test_strict_allows_the_interface_and_code_outside_the_package(strict):
    frame = strict.new([[1, 2]], columns=["a", "b"])
    assert isinstance(frame, strict.StrictFrame)
    assert _as_package_code("len(frame)", frame) == 1
    assert list(strict.column(frame, "a")) == [1]
    assert frame["a"].tolist() == [1]  # this module is not the package


def test_strict_refuses_a_series_handed_across_the_interface(strict):
    import pandas as pd

    with pytest.raises(strict.BackendLeak, match="returned a pandas Series"):
        strict._wrap(lambda: pd.Series([1.0]))()
