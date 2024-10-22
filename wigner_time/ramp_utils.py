# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np


def linear(point_start, point_end, time_resolution=5e-6):
    """
    A series of [time, value] pairs according to the line defined by two points and the time resolution.
    """
    t1, v1 = point_start
    t2, v2 = point_end
    m = (v2 - v1) / (t2 - t1)
    times = np.arange(t1, t2, time_resolution)

    return np.array([times, m * (times - t1) + v1]).transpose()


def to_point_end(point_start, val1, val2, relative=[True, False]):
    """
    Convenience for switching between absolute values and shifts.
    """

    return [
        point_start[0] + val1 if relative[0] else val1,
        point_start[1] + val2 if relative[1] else val2,
    ]


def nonlinear(i, f, factor):
    """
    factor should be between -/+0.5

        TODO: Better name
    """

    return factor * (f - i) + (f + i) / 2.0


def tanhFactor(cc, ti=3):
    """
    cc should be an array
    TODO: if this is the case, then it should be type hinted or controlled in some way.
    """
    return np.tanh(ti * (2.0 * (cc - cc[0]) / (cc[-1] - cc[0]) - 1.0)) / (
        2.0 * np.tanh(ti)
    )


def tanh(point_start, point_end, time_resolution=5 * 1e-6, ti=3):
    """
    Hyperbolic tan, with a call signature adapted for practical timeline population.
    """

    t1, iv = point_start
    t2, fv = point_end
    cc = np.arange(t1, t2, time_resolution)

    return np.array([cc, nonlinear(iv, fv, tanhFactor(cc, ti))]).transpose()
