# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import numpy as np

from wignertime import config as wt_config
from wignertime.internal import util as wt_util


ATTRIBUTE__POINTS = "__wigner_time_points__"
"""
How many time-value pairs a ramp function interpolates between.

This belongs to the function, not to the caller expanding it: `tanh` is defined by two
points, and an interpolation wanting interior control points would be defined by more.
`expand` used to take the number as an argument instead (`num__bounds`), which meant it
could be given a value the data did not match, and could not be told apart from the
caller's other keywords. See KNOWN_ISSUES B6.

The name it replaces was wrong as well as misplaced: for two points "bounds" is exact,
since start and end *are* the boundaries -- but that is the one case where the number
need not be stated at all. A third point is an interior control point, not a bound.
"""

POINTS__DEFAULT = 2
"""Assumed of a ramp function that does not say, which is every hand-written one."""


def with_points(number):
    """
    Declare how many time-value pairs a ramp function interpolates between.

    Decorating is optional: an undeclared function is taken to want `POINTS__DEFAULT`,
    which keeps a user's `lambda origin, terminus, time_resolution: ...` working without
    ceremony.
    """

    def decorate(f):
        setattr(f, ATTRIBUTE__POINTS, number)
        return f

    return decorate


def points(f) -> int:
    """
    How many time-value pairs `f` interpolates between. See `ATTRIBUTE__POINTS`.
    """
    return getattr(f, ATTRIBUTE__POINTS, POINTS__DEFAULT)


@with_points(2)
def linear(
    origin: list[float],
    terminus: list[float],
    time_resolution: float = wt_config.TIME_RESOLUTION,
):
    """
    A series of [time, value] pairs according to the line defined by two points and the time resolution.
    """
    t1, v1 = origin
    t2, v2 = terminus
    m = (v2 - v1) / (t2 - t1)
    times = np.arange(t1, t2, time_resolution)

    return np.array([times, m * (times - t1) + v1]).transpose()


def _normalize(initial: float, final: float, factor: float):
    """
    factor should be in [-0.5,+0.5].
    """

    return factor * (final - initial) + (final + initial) / 2.0


def _tanh__scaled(x: np.ndarray, sharpness=3):
    return np.tanh(sharpness * (2.0 * (x - x[0]) / (x[-1] - x[0]) - 1.0)) / (
        2.0 * np.tanh(sharpness)
    )


@with_points(2)
def tanh(
    origin: list[float],
    terminus: list[float],
    time_resolution: float = wt_config.TIME_RESOLUTION,
    sharpness: float = 3,
):
    """
    Hyperbolic tan, with a call signature adapted for practical timeline population.

    origin/terminus are time-value pairs
    `sharpness` is a measure of how linear the 'slope' of the function is around the halfway point and in practice is used for easing transitions between the end-points. For example, sharpness ~0 (!=0) gives a linear ramp between `origin` and `terminus`, whereas large values approximate a step-function at the half-way point. In-between these values, the ramps returned will start and end gradually, with a linear movement in the middle.
    """

    t1, v1 = origin
    t2, v2 = terminus
    times = wt_util.range__inclusive(t1, t2, time_resolution)

    return np.array(
        [times, _normalize(v1, v2, _tanh__scaled(times, sharpness))]
    ).transpose()


# import matplotlib.pyplot as plt

# xs = np.linspace(0.0, 7.0, 100)
# for ti in [1e-3, 2, 3.14, 100]:
#     plt.plot(
#         tanh([0.0, 0.0], [1.0, 5.0], sharpness=ti)[:, 0],
#         tanh([0.0, 0.0], [1.0, 5.0], sharpness=ti)[:, -1],
#         label=ti,
#     )
# plt.legend()
# plt.show()
