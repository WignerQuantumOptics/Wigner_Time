# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For PC-level loading and saving of stored timelines. 
"""

from pathlib import Path
from typing import Callable
from typing import Any

import inspect
import importlib.util
import re

from wignertime.internal import dataframe as wt_frame


def _available_writers() -> dict[str, Callable[[wt_frame.CLASS, Path], None]]:
    writers: dict[str, Callable[[wt_frame.CLASS, Path], None]] = {
        ".pkl": lambda df, p: df.to_pickle(p),
        ".pickle": lambda df, p: df.to_pickle(p),
        ".csv": lambda df, p: df.to_csv(p, index=False),
        ".json": lambda df, p: df.to_json(p, orient="records"),
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


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _stringify_callables_for_export(df: wt_frame.CLASS, suffix: str) -> wt_frame.CLASS:
    """
    Return a dataframe suitable for export.

    For formats that do not support arbitrary Python objects, any callable values
    are converted to strings. Pickle-like formats are left unchanged.
    """
    # Pickle can preserve Python callables/objects as-is.
    if suffix in {".pkl", ".pickle"}:
        return df

    def _stringify_if_callable(value: Any) -> Any:
        if callable(value):
            try:
                return f"{value.__module__}.{value.__qualname__}"
            except Exception:
                return repr(value)
        return value

    # Work on a copy so the original dataframe is not mutated.
    out = df.copy()

    # Only touch columns that actually contain callables.
    for col in out.columns:
        series = out[col]
        if series.map(callable).any():
            out[col] = series.map(_stringify_if_callable)

    return out


def save(df: wt_frame.CLASS, path: str | Path | None = None) -> Path:
    """
    Writes the given timeline to file, according to convenient features.

        --------
        - If `path` has a recognized suffix, save in that format if the required
          dependency is available.
        - If `path` has no suffix:
            - save as parquet if possible
            - otherwise save as pickle
        - If `path` is a directory (or looks like a directory), generate a filename
          from the caller's variable name for `df`, falling back to "timeline".
        - If the target already exists, append __002, __003, ... before the suffix.

        Returns
        -------
        Path
            The actual path written.

        Supported suffixes
        ------------------
        .parquet, .feather, .pickle, .csv, .json
    """
    if path is None:
        path = Path.cwd()
    path = Path(path).expanduser()

    writers = _available_writers()

    is_existing_dir = path.exists() and path.is_dir()
    looks_like_dir = str(path).endswith(("/", "\\")) or (
        not path.suffix and not path.exists()
    )

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
    export_df = _stringify_callables_for_export(df, suffix)
    writer(export_df, path)

    return path


def load(path: str | Path) -> wt_frame.CLASS:
    """
    Reads the given file into memory.
    """
    path = Path(path).expanduser()

    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()

    match suffix:
        case ".pkl" | ".pickle":
            return wt_frame.read_pickle(path)

        case ".csv":
            return wt_frame.read_csv(path)

        case ".json":
            return wt_frame.read_json(path)

        case ".parquet":
            if not (_has_module("pyarrow") or _has_module("fastparquet")):
                raise ImportError(
                    "Reading parquet requires 'pyarrow' or 'fastparquet'."
                )
            return wt_frame.read_parquet(path)

        case ".feather":
            if not _has_module("pyarrow"):
                raise ImportError("Reading feather requires 'pyarrow'.")
            return wt_frame.read_feather(path)

        case _:
            raise ValueError(f"Unsupported file suffix: {suffix}")
