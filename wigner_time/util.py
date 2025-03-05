# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from collections.abc import Iterable, Sequence

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
