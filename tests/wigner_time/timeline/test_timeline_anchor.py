import pytest
from munch import Munch

from wigner_time import config as wt_config
from wigner_time import ramp_function
from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame


def test_anchor__basic():
    # TODO: WIP
    tl_anchor = tl.stack(
        tl.create(
            lockbox_MOT__MHz=0.0,
            shutter_OP001=0,
            shutter_OP002=1,
            context="ADwin_LowInit",
        ),
        tl.anchor(t=10.0, context="InitialAnchor"),
        tl.ramp(lockbox_MOT__V=[1.0, 10.0], context="new ramp"),
    )

    tl_check = tl.create(
        lockbox_MOT__V=[
            [1.0, 1.0, "ADwin_LowInit"],
            [6.0, 1.0, "new ramp"],
            [7.0, 10.0, "new ramp"],
        ],
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check["time"] > 1.0),
        "function",
    ] = ramp_function.tanh

    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(lockbox_MOT__V=[1.0, 10.0], context="new ramp"),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)

    print(tl_anchor)
    assert tl_anchor
