import pytest
from munch import Munch

from wigner_time import ramp_function, timeline as tl
from wigner_time.internal import dataframe as wt_frame


@pytest.fixture
def dfseq():
    return wt_frame.new(
        [
            [0.0, "lockbox_MOT__V", 0.000000, ""],
            [5.0, "lockbox_MOT__V", 0.000000, ""],
            [5.0, "lockbox_MOT__V", 0.000000, ""],
            [5.2, "lockbox_MOT__V", 0.045177, ""],
            [5.4, "lockbox_MOT__V", 0.500000, ""],
            [5.6, "lockbox_MOT__V", 0.954823, ""],
            [5.8, "lockbox_MOT__V", 1.000000, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "args",
    [
        Munch(lockbox_MOT__V=5, duration=100e-3, context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5], context="init"),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origins=[["last", "variable"], ["variable"]],
        ),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origins=[["last", "variable"], ["variable", "variable"]],
        ),
    ],
)
def test_ramp0(args):
    timeline = tl.create(
        [
            ["lockbox_MOT__V", 0.0, 0.0],
            ["ANCHOR", 0.0, 0.0],
        ],
        context="init",
    )
    tl_ramp = tl.ramp(timeline, **args)
    tl_check = tl.create(
        ANCHOR=[0.0, 0.0, "init"],
        lockbox_MOT__V=[[0.0, 0.0, "init"], [100e-3, 5, "init"]],
    )
    tl_check.loc[tl_check["variable"] == "lockbox_MOT__V", "function"] = (
        ramp_function.tanh
    )

    return wt_frame.assert_equal(tl_ramp, tl_check)


@pytest.mark.parametrize(
    "args",
    [
        Munch(
            lockbox_MOT__V=5,
            duration=0.05,
            origins=[[0.05, "variable"], ["variable"]],
        ),
        Munch(
            lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
            origins=[["ANCHOR", "variable"], ["variable"]],
        ),
        Munch(lockbox_MOT__V=[50e-3, 5], origins=[["last", "variable"], ["variable"]]),
        Munch(
            lockbox_MOT__V=[50e-3, 4.8],
            origins=[["last", "variable"], ["variable", "variable"]],
        ),
    ],
)
def test_ramp1(args):
    timeline = tl.create(lockbox_MOT__V=[50e-3, 0.2], ANCHOR=[0.0, 0.0], context="init")

    tl_ramp = tl.ramp(timeline, **args, context="init")
    tl_check = tl.create(
        ANCHOR=[
            0.0,
            0.0,
        ],
        lockbox_MOT__V=[
            [
                50.0e-3,
                0.2,
            ],
            [
                100e-3,
                5,
            ],
        ],
        context="init",
    )
    tl_check.loc[tl_check["variable"] == "lockbox_MOT__V", "function"] = (
        ramp_function.tanh
    )

    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_combined(dfseq):
    """
    Alternative to `wait`-ing 5s.
    """
    tl_check = tl.create(
        lockbox_MOT__V=[
            [1.0, 1.0],
            [
                6.0,
                1.0,
            ],
            [
                7.0,
                10.0,
            ],
        ],
        context="badger",
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check["time"] > 1.0),
        "function",
    ] = ramp_function.tanh

    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[[5.0, 0.0], [1.0, 10.0]],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)


def test_ramp_expand():
    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[1.0, 10.0],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
        lambda tline: tl.expand_ramps(tline, time_resolution=0.2),
    )
    tl_check = wt_frame.new(
        [
            [1.0, "lockbox_MOT__V", 1.000000, "badger"],
            [1.2, "lockbox_MOT__V", 1.218198, "badger"],
            [1.4, "lockbox_MOT__V", 3.071266, "badger"],
            [1.6, "lockbox_MOT__V", 7.928734, "badger"],
            [1.8, "lockbox_MOT__V", 9.781802, "badger"],
            [2.0, "lockbox_MOT__V", 10.000000, "badger"],
        ],
        columns=["time", "variable", "value", "context"],
    )
    return wt_frame.assert_equal(tl_ramp, tl_check)


if __name__ == "__main__":

    timeline = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[1.0, 10.0],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
    )
    print(timeline)
    print(expand_ramps(timeline, time_resolution=0.2))
