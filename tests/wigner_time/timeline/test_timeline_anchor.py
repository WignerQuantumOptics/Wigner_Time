import pytest
from munch import Munch

from wigner_time import config as wt_config
from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame


def test_anchor__basic():
    tl_anchor = tl.stack(
        tl.create(
            lockbox_MOT__MHz=0.0,
            shutter_OP001=0,
            shutter_OP002=1,
            context="ADwin_LowInit",
        ),
        tl.anchor(t=0.0, context="InitialAnchor"),
    )
