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
