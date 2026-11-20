# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For PC-level loading and saving of stored timelines. 
"""

import functools
import importlib.util
import inspect
import json
import math
import re
import sys
import warnings
from pathlib import Path
from typing import Callable

import pandas as pd

from wignertime import ramp_function
from wignertime.internal import dataframe as wt_frame

COLUMN__FUNCTION = "function"
COLUMN__KEYWORDS = "function__keywords"
"""
In a file, the keyword arguments a ramp's function binds, as a JSON object. It is written
only when some ramp binds any, and `load` folds it back into the functions.
"""

FORMATS__PYTHON = {".pkl", ".pickle"}
"""The formats that hold Python objects as they are, functions included."""


def _times__to_json(df: wt_frame.CLASS) -> wt_frame.CLASS:
    """
    JSON has no infinity, and pandas writes one as `null`, which reads back as `nan`. So
    the state before the run, at −∞, and the state after it, at +∞ (#154), would come
    back at no time at all, on neither side. They are written as the strings `"-inf"`
    and `"inf"` instead, which is still standard JSON, and `load` reads them back.
    """
    if "time" not in df.columns or not any(
        isinstance(t, float) and math.isinf(t) for t in df["time"]
    ):
        return df
    return df.assign(
        time=[
            (
                ("inf" if t > 0 else "-inf")
                if isinstance(t, float) and math.isinf(t)
                else t
            )
            for t in df["time"]
        ]
    )


def _available_writers() -> dict[str, Callable[[wt_frame.CLASS, Path], None]]:
    writers: dict[str, Callable[[wt_frame.CLASS, Path], None]] = {
        ".pkl": lambda df, p: df.to_pickle(p),
        ".pickle": lambda df, p: df.to_pickle(p),
        ".csv": lambda df, p: df.to_csv(p, index=False),
        ".json": lambda df, p: _times__to_json(df).to_json(p, orient="records"),
    }

    if _has_module("pyarrow") or _has_module("fastparquet"):
        writers[".parquet"] = lambda df, p: df.to_parquet(p, index=False)

    if _has_module("pyarrow"):
        writers[".feather"] = lambda df, p: df.to_feather(p)

    return writers


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _next_available_path(path: Path) -> Path:
    if not path.exists():
        return path

    suffix = path.suffix
    stem = path.stem

    m = re.match(r"^(.*)__([0-9]{3})$", stem)
    if m:
        base = m.group(1)
        n = int(m.group(2))
    else:
        base = stem
        n = 1

    while True:
        n += 1
        candidate = path.with_name(f"{base}__{n:03d}{suffix}")
        if not candidate.exists():
            return candidate


def _infer_caller_name(obj: object) -> str | None:
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        return None

    caller = frame.f_back.f_back
    if caller is None:
        return None

    matches: list[str] = []

    for scope in (caller.f_locals, caller.f_globals):
        for name, value in scope.items():
            if value is obj and name.isidentifier():
                matches.append(name)

    if not matches:
        return None

    # Prefer names containing "timeline", then shortest/first stable-looking name.
    matches = sorted(
        set(matches), key=lambda x: ("timeline" not in x.lower(), len(x), x)
    )
    return matches[0]


def _sanitize_stem(name: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "_", name).strip("._")
    return cleaned or "timeline"


def _function__name(f) -> str | None:
    """
    `module.qualname` of a function that can be found again under that name, or `None`.

    A lambda and a function defined inside another have no such name: theirs holds
    `<lambda>` or `<locals>`, and names nothing a later session could look up.
    """
    module = getattr(f, "__module__", None)
    qualname = getattr(f, "__qualname__", None)
    if not module or not qualname or "<" in qualname:
        return None
    found = sys.modules.get(module)
    for part in qualname.split("."):
        found = getattr(found, part, None)
    return f"{module}.{qualname}" if found is f else None


def _function__as_data(f) -> tuple[str, str | None] | None:
    """
    A ramp's function as data: its name and, as a JSON object, the keyword arguments it
    binds. `None` when it cannot be written so.

    That covers a function defined at the top of a module, and a `functools.partial` of one
    whose keywords are numbers, strings, booleans, `None`, or lists and dicts of those:
    `functools.partial(ramp_function.tanh, sharpness=3)`. It does not cover a lambda, a
    function defined inside another, a partial that binds positional arguments, or a keyword
    JSON cannot give back as it was, such as a tuple or an infinity.
    """
    keywords = {}
    if isinstance(f, functools.partial):
        if f.args:
            return None
        keywords, f = dict(f.keywords), f.func
    name = _function__name(f)
    if name is None:
        return None
    if not keywords:
        return name, None
    try:
        text = json.dumps(keywords, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return None
    if json.loads(text) != keywords:
        return None
    return name, text


def _function__text(f) -> str:
    """What is written for a function that cannot be saved as data: something to read."""
    module = getattr(f, "__module__", None)
    qualname = getattr(f, "__qualname__", None)
    return f"{module}.{qualname}" if module and qualname else repr(f)


def _functions__to_data(df: wt_frame.CLASS, path: Path) -> wt_frame.CLASS:
    """
    The frame as a text format can hold it: each ramp's function as its name, with the
    keyword arguments it binds in `COLUMN__KEYWORDS` (D27, #191). `load` rebuilds them.

    A function that cannot be written so is written as text, as all of them were, and the
    ramps it belongs to are named in a warning, since the reloaded timeline will not expand.
    It is a warning and not an error because a timeline is often saved after its run, when
    refusing would lose the record of what ran.
    """
    out = df.copy()
    if COLUMN__FUNCTION in out.columns:
        names, keywords, lost = [], [], []
        for index, f in zip(out.index, out[COLUMN__FUNCTION]):
            if not callable(f):
                names.append(f)
                keywords.append(None)
                continue
            data = _function__as_data(f)
            if data is None:
                names.append(_function__text(f))
                keywords.append(None)
                lost.append(index)
            else:
                names.append(data[0])
                keywords.append(data[1])
        out[COLUMN__FUNCTION] = names
        if any(k is not None for k in keywords):
            out[COLUMN__KEYWORDS] = keywords
        if lost:
            rows = out.loc[lost]
            described = sorted(
                {
                    "{} ({}): {}".format(
                        row.get("variable", "?"),
                        row.get("context", "?"),
                        row[COLUMN__FUNCTION],
                    )
                    for _, row in rows.iterrows()
                }
            )
            warnings.warn(
                "{} keeps these ramps' functions as text only, so the timeline loaded from "
                "it will not expand:\n  {}\nA ramp's function is saved when it is defined "
                "at the top of a module, or is a `functools.partial` of such a function "
                "with keyword arguments, e.g. `functools.partial(ramp_function.tanh, "
                "sharpness=3)`. A lambda, or a function defined inside another, is not. "
                "The expanded timeline, and the record `upload` returns, hold no "
                "functions and save without loss.".format(
                    path.name, "\n  ".join(described)
                ),
                stacklevel=3,
            )

    # Any other column that holds callables is written as text, as before.
    for column in out.columns:
        if column != COLUMN__FUNCTION and out[column].map(callable).any():
            out[column] = out[column].map(
                lambda v: _function__text(v) if callable(v) else v
            )
    return out


def _functions__known(functions) -> dict[str, Callable]:
    """
    The functions `load` may put back, by name: those of `wignertime.ramp_function`, and
    the ones the caller hands over, as a list (each under its own name) or as a dict.

    A file names its functions, and a name is resolved here and nowhere else. `load` does
    not import what a file names: which code runs is for the caller to say, not for a file.
    """
    known = {
        f"{ramp_function.__name__}.{name}": f
        for name, f in vars(ramp_function).items()
        if callable(f)
        and not name.startswith("_")
        and getattr(f, "__module__", None) == ramp_function.__name__
    }
    if functions is None:
        return known
    if isinstance(functions, dict):
        return {**known, **functions}
    for f in functions:
        name = _function__name(f)
        if name is None:
            raise ValueError(
                "{!r} has no name a file could refer to it by: it is a lambda, or defined "
                "inside another function. Hand it over under the name the file uses, as "
                "`functions={{name: function}}`.".format(f)
            )
        known[name] = f
    return known


def _functions__from_data(df: wt_frame.CLASS, path: Path, functions) -> wt_frame.CLASS:
    """
    Puts the functions back that `_functions__to_data` wrote as names and keywords.

    A name that is not known stays as text, and is reported: the rest of the timeline is
    still worth reading, and expanding it raises at that ramp.
    """
    if COLUMN__FUNCTION not in df.columns:
        return df
    known = _functions__known(functions)
    bound = df[COLUMN__KEYWORDS] if COLUMN__KEYWORDS in df.columns else [None] * len(df)
    restored, unknown = [], set()
    for name, keywords in zip(df[COLUMN__FUNCTION], bound):
        if not isinstance(name, str):
            restored.append(name)
        elif name not in known:
            restored.append(name)
            unknown.add(name)
        elif isinstance(keywords, str):
            restored.append(functools.partial(known[name], **json.loads(keywords)))
        else:
            restored.append(known[name])
    out = df.drop(columns=[COLUMN__KEYWORDS], errors="ignore")
    out[COLUMN__FUNCTION] = pd.Series(restored, index=out.index, dtype=object)
    if unknown:
        warnings.warn(
            "{} names ramp functions that are not known here, so they stay as text and "
            "the timeline will not expand:\n  {}\nA function of "
            "`wignertime.ramp_function` is found by itself. Hand over any other: "
            "`load(path, functions=[my_ramp])`. A name with `<lambda>` or `<locals>` in "
            "it was never saved as data.".format(
                path.name, "\n  ".join(sorted(unknown))
            ),
            stacklevel=3,
        )
    return wt_frame.normalise_nulls(out)


def save(df: wt_frame.CLASS, path: str | Path | None = None) -> Path:
    """
    Writes the given timeline to file, according to convenient features.

        --------
        - If `path` has a recognized suffix, save in that format if the required
          dependency is available.
        - If `path` has no suffix:
            - save as parquet if possible
            - otherwise save as pickle
        - If `path` is an existing directory, or ends with a path separator, generate a
          filename from the caller's variable name for `df`, falling back to "timeline".
          A name without a suffix that does not exist yet is a file, by the rule above:
          `save(t, "run42")` writes `run42.parquet`. (It used to make a directory,
          `run42/`, against that rule, D26.)
        - If the target already exists, append __002, __003, ... before the suffix.

        Returns
        -------
        Path
            The actual path written.

        Supported suffixes
        ------------------
        .parquet, .feather, .pickle, .csv, .json

        Ramps
        -----
        A ramp's function is saved as data, its name and the keyword arguments it binds,
        when it is defined at the top of a module or is a `functools.partial` of such a
        function, and `load` gives it back (#191). Any other, such as a lambda, is written
        as text in every format but pickle, with a warning that names the ramps: the
        reloaded timeline can be read, not expanded.
    """
    if path is None:
        path = Path.cwd()
    # Asked of the argument as given: `Path` drops a trailing separator.
    looks_like_dir = str(path).endswith(("/", "\\"))
    path = Path(path).expanduser()

    writers = _available_writers()

    is_existing_dir = path.exists() and path.is_dir()

    if is_existing_dir or looks_like_dir:
        path.mkdir(parents=True, exist_ok=True)
        stem = _infer_caller_name(df) or "timeline"

        if ".parquet" in writers:
            ext = ".parquet"
        elif ".pkl" in writers:
            ext = ".pkl"
        elif ".pickle" in writers:
            ext = ".pickle"
        else:
            # Fallback to the first available writer if needed
            ext = next(iter(writers))

        path = path / f"{_sanitize_stem(stem)}{ext}"

    elif not path.suffix:
        if ".parquet" in writers:
            ext = ".parquet"
        elif ".pkl" in writers:
            ext = ".pkl"
        elif ".pickle" in writers:
            ext = ".pickle"
        else:
            ext = next(iter(writers))

        path = path.with_suffix(ext)

    suffix = path.suffix.lower()
    if suffix not in writers:
        supported = ", ".join(sorted(writers))
        raise ValueError(
            f"Unsupported file suffix {suffix!r}. Supported writable formats: {supported}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path = _next_available_path(path)

    writer = writers[suffix]
    export_df = df if suffix in FORMATS__PYTHON else _functions__to_data(df, path)
    writer(export_df, path)

    return path


def load(path: str | Path, functions=None) -> wt_frame.CLASS:
    """
    Reads the given file into memory.

    The ramp functions that `save` wrote as data are put back: those of
    `wignertime.ramp_function` by themselves, and any other when it is handed over in
    `functions`, as a list of functions or as a dict from the name in the file to the
    function. A name that is not known stays as text, with a warning. Nothing a file names
    is imported.
    """
    path = Path(path).expanduser()

    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()

    match suffix:
        case ".pkl" | ".pickle":
            df = wt_frame.read_pickle(path)

        case ".csv":
            df = wt_frame.read_csv(path)

        case ".json":
            df = wt_frame.read_json(path)
            if "time" in df.columns and df["time"].dtype == object:
                df["time"] = df["time"].astype(float)  # "-inf" and "inf" (#154)

        case ".parquet":
            if not (_has_module("pyarrow") or _has_module("fastparquet")):
                raise ImportError(
                    "Reading parquet requires 'pyarrow' or 'fastparquet'."
                )
            df = wt_frame.read_parquet(path)

        case ".feather":
            if not _has_module("pyarrow"):
                raise ImportError("Reading feather requires 'pyarrow'.")
            df = wt_frame.read_feather(path)

        case _:
            raise ValueError(f"Unsupported file suffix: {suffix}")

    # Parquet, JSON and feather return a missing value as `None` where the in-memory
    # timeline holds `nan`; CSV and pickle keep `nan`. Settle on one, so that a
    # round-trip is faithful whichever format was chosen.
    df = wt_frame.normalise_nulls(df)
    return (
        df if suffix in FORMATS__PYTHON else _functions__from_data(df, path, functions)
    )
