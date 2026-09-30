# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The pandas backend, checked: package code outside `wignertime.internal.dataframe` may
not touch a timeline directly.

Every frame this backend returns is a `StrictFrame`, a `pandas.DataFrame` that raises
`BackendLeak` when an attribute, an item or an iteration is asked of it by a module of
the package other than this one. pandas' own code, the tests and user code are not
checked: the rule is about the package, whose operations must all go through the
interface if another backend is ever to stand in for pandas.

A function of the interface that hands back a `pandas.Series` raises as well. The
interface returns numpy arrays, and a Series given to package code would let a pandas
operation through unchecked.

This is a test instrument. It is slower than `pandas` and is not meant for experiments.

With `WIGNERTIME_STRICT_LOG=<path>` set, a leak is appended to that file (one line per
site, first occurrence only) instead of raised, so that one run of the suite gives the
whole census rather than the first leak on each path.
"""

import functools
import os
import sys

import pandas as pd

from . import _narwhals as _pandas  # used with pandas, which `__init__` has selected

_OWN = __name__.rsplit(".", 1)[0]  # wignertime.internal.dataframe
_PACKAGE = _OWN.split(".", 1)[0]  # wignertime
_LOG = os.environ.get("WIGNERTIME_STRICT_LOG")
_logged: set = set()


class BackendLeak(TypeError):
    """Package code used a pandas operation on a timeline without going through `wt_frame`."""


def _check(depth, what):
    caller = sys._getframe(depth)
    module = caller.f_globals.get("__name__", "")
    if module.split(".", 1)[0] == _PACKAGE and not module.startswith(_OWN):
        site = f"{module}:{caller.f_lineno} ({caller.f_code.co_name}) {what}"
        if _LOG:
            if site not in _logged:
                _logged.add(site)
                with open(_LOG, "a") as log:
                    log.write(site + "\n")
            return
        raise BackendLeak(f"{site}; go through `wt_frame` instead.")


def _key(key):
    if isinstance(key, str) or (
        isinstance(key, list) and all(isinstance(k, str) for k in key)
    ):
        return repr(key)
    return f"<{type(key).__name__}>"


class StrictFrame(pd.DataFrame):
    _metadata: list = []

    @property
    def _constructor(self):
        return StrictFrame

    def __getattribute__(self, name):
        if not (name.startswith("__") and name.endswith("__")):
            _check(2, f"`.{name}`")
        return super().__getattribute__(name)

    def __getitem__(self, key):
        _check(2, f"`[{_key(key)}]`")
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        _check(2, f"`[{_key(key)}] = ...`")
        return super().__setitem__(key, value)

    def __iter__(self):
        _check(2, "iteration")
        return super().__iter__()


def _strict(result, name):
    if isinstance(result, pd.Series) and not _LOG:
        raise BackendLeak(
            f"`wt_frame.{name}` returned a pandas Series; the interface returns numpy arrays."
        )
    if isinstance(result, pd.DataFrame) and not isinstance(result, StrictFrame):
        return StrictFrame(result)
    if isinstance(result, tuple):
        return tuple(_strict(r, name) for r in result)
    if isinstance(result, list):
        return [_strict(r, name) for r in result]
    return result


def _wrap(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return _strict(f(*args, **kwargs), f.__name__)

    return wrapped


def _wrap_iterator(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        for item in f(*args, **kwargs):
            yield _strict(item, f.__name__)

    return wrapped


CLASS = pd.DataFrame

for _name in dir(_pandas):
    _value = getattr(_pandas, _name)
    if _name.startswith("_") or not callable(_value) or isinstance(_value, type):
        continue
    if getattr(_pandas, "_ITERATORS", ()) and _name in _pandas._ITERATORS:
        globals()[_name] = _wrap_iterator(_value)
    else:
        globals()[_name] = _wrap(_value)
