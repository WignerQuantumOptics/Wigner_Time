# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from collections.abc import Iterable, Sequence
from typing import Callable, OrderedDict
import inspect

import numpy as np
import math

from wigner_time.config import wtlog


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
                f"Two many arguments to `ensure_pair`, {l} should be a pair."
            )
        case _:
            raise ValueError(f"Unexpected argument to `ensure_pair`.")


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
    """
    # Uses `math` because it returns an integer rather than a float.
    num = np.abs(math.ceil((stop - start) / step) + 1)
    return np.linspace(start, stop, num=num)


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


def function__lambda(lambda_key="timeline", kwargs=["vtvc_dict"]):
    """
    Returns a function lamba based on the given function, and current local values, where the existing kwargs can be overwritten.

    The `lambda_key` determines which variable becomes the primary argument in the lambda.
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

    return lambda x, **kwargs__new: f(
        **{
            k: x,
            **kwargs,
            **kwargs__new,
        }
    )
