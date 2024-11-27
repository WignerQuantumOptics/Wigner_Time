import pytest

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame

def test_ramp():
    timeline =  wt_frame.new(
        [
            [0.0, "lockbox_MOT__V", 0.0, "init"],
            [0.0, "ANCHOR", 0.0, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return wt_frame.assert_equal(
        tl.ramp(timeline,
                lockbox_MOT__V=5,
                duration=100e-3),
        tl.create(lockbox_MOT__V=[])
    )
