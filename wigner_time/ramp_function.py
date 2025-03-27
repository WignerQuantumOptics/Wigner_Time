# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import numpy as np
from wigner_time import util as wt_util


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
