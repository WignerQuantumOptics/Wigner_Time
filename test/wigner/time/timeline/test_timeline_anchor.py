import pytest
from munch import Munch

from wignertime import config as wt_config
from wignertime import ramp_function
from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame


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

    tl_check = tl._populate_timeline(
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
        tl._populate_timeline(
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


def test_anchor_requires_t():
    """
    C3. `t` is a displacement from whatever the `origin` resolves to, and the two
    readings a default would choose between are different instants -- so there is no
    sensible default and the manuscript documents `t` as positional and required.
    """
    with pytest.raises(TypeError, match="required positional argument"):
        tl.anchor()

    with pytest.raises(TypeError, match="requires `t`"):
        tl.anchor(None)


def test_anchor_chains_on_the_previous_anchor_not_the_last_row():
    """
    C3. The distinction that makes a default impossible: once a stage writes rows past
    its own closing anchor, "here" has two meanings.
    """
    timeline = tl.stack(
        tl.create(coil__A=1.0, t=0.0, context="s1"),
        tl.anchor(3.0),
        tl.update(coil__A=2.0, t=5.0, origin=0.0),
    )

    def anchor_time(frame):
        marks = frame[frame["variable"].str.startswith(wt_config.LABEL__ANCHOR)]
        return marks["time"].max()

    assert anchor_time(tl.anchor(0.0, timeline=timeline)) == 3.0
    assert anchor_time(tl.anchor(0.0, timeline=timeline, origin="last")) == 5.0
