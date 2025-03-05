import pytest
from munch import Munch

from wigner_time import config as wt_config
from wigner_time import ramp_function
from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame


def test_anchor__basic():
    tl_anchor = tl.stack(
        tl.create(
            lockbox_MOT__MHz=0.0,
            context="ADwin_LowInit",
        ),
        tl.anchor(t=10.0, context="InitialAnchor"),
        tl.ramp(lockbox_MOT__MHz=[1.0, 10.0], context="new ramp"),
    )

    tl_check = tl.create(
        lockbox_MOT__MHz=[
            [0.0, 0.0, "ADwin_LowInit"],
            [10.0, 0.0, "new ramp"],
            [11.0, 10.0, "new ramp"],
        ],
    )

    tl_check = tl.create(
        ["⚓_001", [10.0, 0.0, "InitialAnchor"]],
        timeline=tl_check,
        context="InitialAnchor",
        origin=[0.0, 0.0],
    )

    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__MHz") & (tl_check["time"] > 1.0),
        "function",
    ] = ramp_function.tanh
    tl_check.sort_values(["time", "context"], inplace=True, ignore_index=True)

    return wt_frame.assert_equal(tl_check, tl_anchor)


@pytest.fixture
def df_context1():
    return wt_frame.new(
        [
            ["thing2", 1.0, 5.0, "init"],
            ["thing", 0.0, 5.0, "init"],
            ["thing", 5.0, 5.0, "MOT"],
            ["⚓_001", 4.5, 5.0, "MOT"],
            ["thing3", 3.0, 5.0, "blah"],
        ],
        columns=["variable", "time", "value", "context"],
    )


def test_anchorContext(df_context1):
    return wt_frame.assert_equal(
        tl.create(
            lockbox_MOT__MHz=[1.0, 10.0],
            timeline=df_context1,
            context="ramp",
            origin="MOT",
        ),
        wt_frame.new(
            [
                ["thing2", 1.0, 5.0, "init"],
                ["thing", 0.0, 5.0, "init"],
                ["thing", 5.0, 5.0, "MOT"],
                ["⚓_001", 4.5, 5.0, "MOT"],
                ["thing3", 3.0, 5.0, "blah"],
                ["lockbox_MOT__MHz", 5.5, 10.0, "ramp"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )
