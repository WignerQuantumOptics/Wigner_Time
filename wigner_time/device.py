"""
A device is represented by a dataframe that contains a `unit_range` and (optionally) a `safety_range`.

The unit range is used for conversion and the saftey range is for sanity checking the output.
"""

from wigner_time.internal import dataframe as frame


def add_devices(df, devices):
    """ """
    return frame.join(df, devices)
