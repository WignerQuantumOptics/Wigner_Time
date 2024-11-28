import pytest

from wigner_time import ramp_function, timeline as tl
from wigner_time.internal import dataframe as wt_frame

def test_ramp():
    timeline =  tl.create(
        [
            ["lockbox_MOT__V",0.0,  0.0],
            ["ANCHOR",0.0,  0.0],
        ],
        context='init'
    )
    tl_ramp = tl.ramp(timeline,
                lockbox_MOT__V=5,
                      duration=100e-3,
                      context='init')
    tl_check =tl.create(
            ANCHOR=[0.0, 0.0, "init"],
            lockbox_MOT__V=[[0.0, 0.0, 'init'],
            [100e-3, 5, 'init']],
        )
    tl_check.loc[tl_check['variable']=='lockbox_MOT__V', 'function']=ramp_function.tanh
    print(tl_check)

    return wt_frame.assert_equal(
        tl_ramp,
        tl_check

    )
