"""
The dataframe backend: `wt_frame.INTERFACE` is the contract, and `pandas-strict` is what
checks that the package keeps to it.
"""

import os
import subprocess
import sys

import pandas as pd
import pytest

from wignertime.internal import dataframe as wt_frame
from wignertime.internal.dataframe import _pandas, _strict


def _python(code, backend):
    env = dict(os.environ, WIGNERTIME_BACKEND=backend)
    env.pop("WIGNERTIME_STRICT_LOG", None)
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )


def test_the_pandas_backend_implements_the_whole_interface():
    assert [name for name in wt_frame.INTERFACE if not hasattr(_pandas, name)] == []


def test_the_pandas_backend_offers_nothing_outside_the_interface():
    """
    A helper defined in the backend but missing from `INTERFACE` would be reachable only
    by importing the backend directly, which is how a second pandas-only path would start.
    """
    defined = {
        name
        for name, value in vars(_pandas).items()
        if not name.startswith("_")
        and callable(value)
        and getattr(value, "__module__", None) == _pandas.__name__
    }
    assert defined - set(wt_frame.INTERFACE) == set()


def test_an_unknown_backend_is_refused():
    result = _python("import wignertime.internal.dataframe", "nonsense")
    assert result.returncode != 0
    assert "is not a backend" in result.stderr


def test_the_polars_backend_names_what_it_lacks():
    pytest.importorskip("polars")
    result = _python("from wignertime.internal import dataframe as f; f.sort", "polars")
    assert result.returncode != 0
    assert (
        "`wt_frame.sort` has no implementation for the 'polars' backend"
        in result.stderr
    )


def _as_package_code(expression, frame):
    return eval(
        compile(expression, "<package code>", "eval"),
        {"__name__": "wignertime.somewhere", "frame": frame},
    )


@pytest.mark.skipif(
    _strict._LOG is not None, reason="the census logs rather than raises"
)
@pytest.mark.parametrize(
    "expression", ["frame['a']", "frame.empty", "frame.loc[0]", "list(frame)"]
)
def test_strict_refuses_package_code_that_touches_a_frame(expression):
    frame = _strict.new([[1, 2]], columns=["a", "b"])
    with pytest.raises(_strict.BackendLeak, match="wignertime.somewhere"):
        _as_package_code(expression, frame)


def test_strict_allows_the_interface_and_code_outside_the_package():
    frame = _strict.new([[1, 2]], columns=["a", "b"])
    assert isinstance(frame, _strict.StrictFrame)
    assert _as_package_code("len(frame)", frame) == 1
    assert list(_strict.column(frame, "a")) == [1]
    assert frame["a"].tolist() == [1]  # this module is not the package


@pytest.mark.skipif(
    _strict._LOG is not None, reason="the census logs rather than raises"
)
def test_strict_refuses_a_series_handed_across_the_interface():
    with pytest.raises(_strict.BackendLeak, match="returned a pandas Series"):
        _strict._wrap(lambda: pd.Series([1.0]))()
