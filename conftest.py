# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The suite runs against one dataframe backend at a time:

    pytest                          # pandas
    pytest --backend=pandas-strict  # pandas, refusing any operation that bypasses `wt_frame`
    pytest --backend=polars         # not implemented yet; lists what is missing

The backend is fixed when `wignertime` is first imported, so it is passed through the
environment before collection. `WIGNERTIME_BACKEND` works as well as the option.

Tests of pandas' own behaviour, rather than the package's, carry `@pytest.mark.pandas_only`
and are skipped on other backends.
"""

import os
import sys

import pytest

BACKENDS = ("pandas", "pandas-strict", "polars")


def pytest_addoption(parser):
    parser.addoption(
        "--backend",
        choices=BACKENDS,
        default=os.environ.get("WIGNERTIME_BACKEND", "pandas"),
        help="the dataframe backend wignertime runs on (default: pandas, or $WIGNERTIME_BACKEND)",
    )


def pytest_configure(config):
    backend = config.getoption("--backend")
    if (
        "wignertime" in sys.modules
        and os.environ.get("WIGNERTIME_BACKEND", "pandas") != backend
    ):
        raise pytest.UsageError(
            "wignertime was imported before the backend could be set; "
            "use WIGNERTIME_BACKEND instead of --backend here."
        )
    os.environ["WIGNERTIME_BACKEND"] = backend
    config.addinivalue_line(
        "markers",
        "pandas_only: tests pandas behaviour itself; skipped on non-pandas backends",
    )


def pytest_report_header(config):
    return f"wignertime dataframe backend: {config.getoption('--backend')}"


def pytest_collection_modifyitems(config, items):
    if config.getoption("--backend").startswith("pandas"):
        return
    skip = pytest.mark.skip(reason="pandas_only")
    for item in items:
        if "pandas_only" in item.keywords:
            item.add_marker(skip)
