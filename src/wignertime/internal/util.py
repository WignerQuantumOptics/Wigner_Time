# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The inevitable `util` module for miscellaneous functions that haven't been organized yet.
"""

from collections.abc import Iterable, Sequence
from typing import Callable, OrderedDict
import inspect

import numpy as np
import math

from wignertime.config import wtlog
from wignertime.internal import dataframe as wt_frame


def is_sequence(x, is_string=False):
    """
    Checks if x is a non-string sequence by default. Strings can be included using the 'is_string' flag.
    """

    if not is_string:
        return isinstance(x, Sequence) and not isinstance(x, str)
    else:
        return isinstance(x, Sequence)


def shape(coll):
    """
    Recursively determine the maximum dimensions of a nested list or array.
    Works independently of whether the input is a NumPy array or a Python list.
    """
    if isinstance(coll, (list, np.ndarray)) and len(coll) > 0:
        return [len(coll)] + shape(coll[0])
    return []


def max_dimension(coll):
    """
    Following on from `shape`, returns the highest dimension in a potentially heterogeneous shape.
    """
    wtlog.debug(coll)
    return max([max(shape(a)) for a in coll])


def ensure_iterable(x, is_string=False):
    """
    'x' if iterable, [x] otherwise.

    is_string determines if 'x' is allowed to be a string.
    """
    if not is_string:
        return x if (isinstance(x, Iterable) and not isinstance(x, str)) else [x]
    else:
        return x if isinstance(x, Iterable) else [x]


def ensure_iterable_with_None(x, is_string=False) -> list:
    """
    'x' if iterable, [x] otherwise.

    is_string determines if 'x' is allowed to be a string.
    """
    if not is_string:
        return x if (isinstance(x, Iterable) and not isinstance(x, str)) else [x, None]
    else:
        return x if isinstance(x, Iterable) else [x, None]


def ensure_pair(l: list):
    """
    [x,y,...] -> error
    [x,y]     -> [x,y]
    [x]       -> [x,None]
    []        -> [None,None]
    """
    match l:
        case [*x] if len(l) == 2:
            return l
        case [x]:
            return [x, None]
        case []:
            return [None, None]
        case [*x] if len(l) > 2:
            raise ValueError(
                "Too many elements in an origin: {!r}. An origin is a"
                " `[time, value]` pair, so at most two.".format(l)
            )
        case _:
            raise ValueError(f"Unexpected argument to `ensure_pair`.")


def ensure_2d(input_data):
    """Ensure the input is converted to a 2D list."""
    if isinstance(input_data, (list, tuple)):
        if len(input_data) > 0 and isinstance(input_data[0], (list, tuple)):
            return input_data
        return [input_data]
    return [[input_data]]


def is_collection(x, is_string=False):
    """
    Checks if x is a non-string sequence or numpy array by default. Strings can be included using the 'is_string' flag.
    """

    if not is_string:
        return (
            isinstance(x, Sequence) or isinstance(x, np.ndarray)
        ) and not isinstance(x, str)
    else:
        return isinstance(x, Sequence) or isinstance(x, np.ndarray)


def filter_dict(d, ks):
    return dict(filter(lambda item: item[0] in ks, d.items()))


def range__inclusive(start, stop, step):
    """
    Numpy's `arange`, but including the final value.

    Adapting arange, by adding the step size, leads to awkward corner cases, so we use a modified `linspace` instead.

    The interval count is rounded before the ceiling is taken, because `stop - start` is
    a difference of absolute times and so carries floating-point noise whose sign
    depends on where the interval sits on the axis. Bare `ceil` turned that noise into a
    different number of points: a nominally 0.8 s ramp at a resolution of 0.2 s gave 5
    points (step 0.2) at t=5.0 and 6 points (step 0.16) at t=10.0. The endpoints and the
    shape were right either way, but the sampling -- and hence the row count reaching
    the hardware -- depended on when the ramp happened to be scheduled. See
    KNOWN_ISSUES B9.
    """
    # Uses `math` because it returns an integer rather than a float.
    intervals = (stop - start) / step
    intervals__whole = round(intervals)
    num = np.abs(
        (
            intervals__whole
            if math.isclose(intervals, intervals__whole, rel_tol=1e-9)
            else math.ceil(intervals)
        )
        + 1
    )
    return np.linspace(start, stop, num=num)


def sample(lst: list, N: int):
    """
    Retrive `N`, equally and maximally spaced, elements from the `list`.
    """
    indices = np.linspace(0, len(lst) - 1, N, dtype=int)
    return [lst[i] for i in indices]


def function__filtered_kws(f: Callable, **kws) -> Callable:
    """
    Converts the given function into a function lambda, where `kws` is used to update relevant arguments and other supplied kws are ignored.
    """
    sig = inspect.signature(f)
    is_acceptable_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
    if is_acceptable_kwargs:
        return lambda *args: f(*args, **kws)
    else:
        # Filter only allowed kwargs
        accepted_keys = {
            k
            for k, p in sig.parameters.items()
            if p.kind in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD)
        }
        filtered_kwargs = {k: v for k, v in kws.items() if k in accepted_keys}
        return lambda *args: f(*args, **filtered_kwargs)


def flatten_keys(d: OrderedDict, ks: str) -> OrderedDict:
    """
    Recursively flattens the dictionary until the given key doesn't exist anymore.
    """
    d = OrderedDict(d)  # make a shallow copy to avoid mutating input

    while True:
        found = False
        for key in ks:
            if key in d:
                nested = d.pop(key)
                if not isinstance(nested, dict):
                    raise TypeError(
                        f"{key} must be a dictionary, got {type(nested).__name__}"
                    )
                d.update(nested)
                found = True
        if not found:
            break

    return d


def args_in_function(f: Callable, kwargs, exclude=(), call_frame=None) -> OrderedDict:
    """
    Gets the local variable values relevant to the function call.

    NOTE: strongly dependent on the environment in which it is called.
    """
    # TODO: populate kwargs automatically?
    if call_frame is None:
        frame = inspect.currentframe().f_back
    else:
        frame = call_frame

    sig = inspect.signature(f)
    bound_args = sig.bind_partial(**frame.f_locals)
    bound_args.apply_defaults()

    args = flatten_keys(
        OrderedDict(
            {k: v for k, v in bound_args.arguments.items() if k not in exclude}
        ),
        kwargs,
    )

    return args


def accepts_keyword(f, name: str) -> bool:
    """
    Whether `f` would accept `name` as a keyword argument.

    True if `f` declares the parameter, or if it collects `**kwargs` -- which is what
    keeps `default_state` and the functions wrapping it open to the variable injection
    described in the manuscript's `sec:forwarding`, while an ordinary stage, having
    declared what it forwards, is closed.

    Permissive when the signature cannot be read at all (some builtins and C callables),
    since refusing there would reject a legitimate target on the strength of not being
    able to inspect it.
    """
    try:
        parameters = inspect.signature(f).parameters
    except (TypeError, ValueError):
        return True

    return name in parameters or any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()
    )


ATTRIBUTE__DEFERRED = "__wigner_time_deferred__"
"""
Marks an object as a *deferred timeline function*: something that takes a timeline and
returns a timeline. Set by `function__lambda` and by `timeline.stack`, and by nothing
else.

This exists because the distinction cannot be recovered any other way. A deferred call,
a composed `stack` and an uncalled user stage are all plain `function` objects, and
their signatures do not separate them -- a stage is free to take `(x, **kwargs)` too.
The tag is therefore the only thing that can tell `stack` a constituent is the kind of
callable it knows how to apply.
"""


def mark_deferred(f):
    """
    Tag `f` as a deferred timeline function and return it. See `ATTRIBUTE__DEFERRED`.
    """
    setattr(f, ATTRIBUTE__DEFERRED, True)
    return f


def is_deferred(f) -> bool:
    """
    Whether `f` was produced by the deferral machinery, rather than merely being callable.
    """
    return getattr(f, ATTRIBUTE__DEFERRED, False) is True


def takes_one_timeline(f) -> bool:
    """
    Whether `f` looks like a timeline transformer: something callable with exactly one
    required positional argument.

    A fallback for `is_deferred`, so that an ordinary hand-written
    `lambda tline: expand(tline, ...)` can be a `stack` constituent without being tagged.

    It discriminates the case that matters. A stage written to the convention of the
    manuscript defaults everything and takes `timeline=None`, so it has *no* required
    positional argument; a stage with required parameters, like `pull_coils`, has several.
    Only a transformer has exactly one. Permissive when the signature cannot be read.
    """
    try:
        parameters = inspect.signature(f).parameters.values()
    except (TypeError, ValueError):
        return True

    return (
        len(
            [
                p
                for p in parameters
                if p.default is p.empty
                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            ]
        )
        == 1
    )


def ensure_timeline(
    timeline,
    name__function: str,
    name__argument: str = "timeline",
    columns__required=None,
    column__context: str = "context",
):
    """
    Check the `timeline` argument against its contract, naming the mistake where it is
    made rather than letting it surface downstream.

    Three outcomes, and the third is the point of the function:

    - a dataframe -- evaluate against it, after checking it carries `columns__required`
      and normalising a null `context` to the empty string
    - `None`      -- defer, returning a callable
    - anything else -- `TypeError`

    Returns the timeline, which may be a normalised copy, so callers must use the result.

    A **callable** is the mistake the deferral design invites. Nesting one core call
    inside another -- `expand(ramp(...))` -- reads like ordinary composition but is not:
    a core function called without a `timeline` returns a *function*, so the inner call
    arrives here as the `timeline` argument. Deferred calls compose as siblings of a
    `stack`, in execution order, never by nesting.

    **Anything else** -- a list, a string, an int, a dict -- used to fail much later and
    cryptically, on whatever dataframe attribute was touched first, naming neither the
    function nor the argument. It is rejected here instead, with both.
    """
    if timeline is None:
        return timeline

    if isinstance(timeline, wt_frame.CLASS):
        if columns__required is not None:
            missing = [c for c in columns__required if c not in timeline.columns]
            if missing:
                raise TypeError(
                    "`{}` was given a frame missing the column(s) {}. A timeline has "
                    "{}; `context` is required and is the empty string where "
                    "unspecified, not absent and not `None` (#28).".format(
                        name__function, missing, list(columns__required)
                    )
                )

        # A hand-built frame can carry a null here, which used to propagate as a real
        # `None` into every row that inherited from it. The empty string is the
        # documented minimum, so normalise rather than carry two spellings of "no
        # context" through the rest of the package.
        if (
            column__context in timeline.columns
            and wt_frame.isnull(timeline[column__context]).any()
        ):
            return wt_frame.fill_null(timeline, column__context, "")

        return timeline

    if callable(timeline):
        raise TypeError(
            "\n".join(
                [
                    "`{}` was given a deferred function where a timeline was"
                    " expected.".format(name__function),
                    "",
                    "That is what a core function returns when called without"
                    " `timeline=`, so this usually means two calls were nested:",
                    "",
                    "    {}(ramp(...))    # `ramp(...)` here is a function, not a"
                    " timeline".format(name__function),
                    "",
                    "Deferred calls compose as siblings of a `stack`, in execution"
                    " order:",
                    "",
                    "    stack(timeline, ramp(...), {}(...))".format(name__function),
                ]
            )
        )

    raise TypeError(
        "\n".join(
            [
                "`{}` was given {} as `{}`, where a timeline or `None` was"
                " expected.".format(
                    name__function, type(timeline).__name__, name__argument
                ),
                "",
                "A timeline is a dataframe. `None` defers the call, returning a"
                " function for a `stack` to apply later.",
            ]
        )
    )


def function__lambda(lambda_key="timeline", kwargs=["vtvc_dict"]):
    """
    Returns a function lamba based on the given function, and current local values, where the existing kwargs can be overwritten.

    The `lambda_key` determines which variable becomes the primary argument in the lambda.

    NOTE: strongly dependent on the environment in which it is called.
    """

    frame = inspect.currentframe().f_back
    name__f = frame.f_code.co_name
    f = frame.f_globals[name__f]

    kwargs = args_in_function(f, kwargs=kwargs, call_frame=frame)

    lambda_pair = [lambda_key, kwargs.pop(lambda_key)]

    if lambda_pair is not None:
        k, v = lambda_pair
    else:
        raise ValueError("Function `f` needs to have arguments in `function__lambda`.")

    return mark_deferred(
        lambda x, **kwargs__new: f(
            **{
                k: x,
                **kwargs,
                **kwargs__new,
            }
        )
    )
