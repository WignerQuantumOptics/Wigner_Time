# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

from collections.abc import Iterable, Sequence

import numpy as np


def is_sequence(x, is_string=False):
    """
    Checks if x is a non-string sequence by default. Strings can be included using the 'is_string' flag.
    """

    if not is_string:
        return isinstance(x, Sequence) and not isinstance(x, str)
    else:
        return isinstance(x, Sequence)


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
