import pytest
from munch import Munch
import numpy as np

from wigner_time import ramp_function, timeline as tl
from wigner_time.adwin import display
from wigner_time.internal import dataframe as wt_frame

import pathlib as pl
import sys

sys.path.append(str(pl.Path.cwd() / "doc"))
import experimentDemo as ex


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


@pytest.fixture
def tl_anchor():
    return tl.create(
        [
            ["lockbox_MOT__V", 0.0],
            ["⚓_001", 0.0],
        ],
        t=0.0,
        context="init",
    )


@pytest.mark.parametrize(
    "args",
    [
        Munch(lockbox_MOT__V=5, duration=100e-3, context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5], context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5, "init"]),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origin=["last", "variable"],
            origin2=["variable"],
        ),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origin=["last", "variable"],
            origin2=["variable", "variable"],
        ),
    ],
)
def test_ramp0(args):
    timeline = tl.create(
        [
            ["lockbox_MOT__V", 0.0, 0.0],
            ["⚓_001", 0.0, 0.0],
        ],
        context="init",
    )
    tl_ramp = tl.ramp(timeline, **args)
    tl_check = tl.create(
        [
            ["lockbox_MOT__V", [0.0, 0.0, "init"]],
            ["⚓_001", [0.0, 0.0, "init"]],
            ["lockbox_MOT__V", [[0.0, 0.0, "init"], [100e-3, 5, "init"]]],
        ],
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


@pytest.mark.parametrize(
    "args",
    [
        Munch(
            lockbox_MOT__V=5,
            duration=0.05,
            origin=[0.05, "variable"],
            origin2=["variable"],
        ),
        Munch(
            lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
            origin=["anchor", "variable"],
            origin2=["variable"],
        ),
        Munch(
            lockbox_MOT__V=[50e-3, 5], origin=["last", "variable"], origin2=["variable"]
        ),
        Munch(
            lockbox_MOT__V=[50e-3, 4.8],
            origin=["last", "variable"],
            origin2=["variable", "variable"],
        ),
    ],
)
def test_ramp1(args):
    timeline = tl.create(
        [["lockbox_MOT__V", [50e-3, 0.2]], ["⚓_001", [0.0, 0.0]]], context="init"
    )

    tl_ramp = tl.ramp(timeline, **args, context="init")
    tl_check = tl.create(
        [
            ["lockbox_MOT__V", [50e-3, 0.2]],
            [
                "⚓_001",
                [
                    0.0,
                    0.0,
                ],
            ],
            [
                "lockbox_MOT__V",
                [
                    [
                        50.0e-3,
                        0.2,
                    ],
                    [
                        100e-3,
                        5,
                    ],
                ],
            ],
        ],
        context="init",
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_combined():
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
            origin=["lockbox_MOT__V", "lockbox_MOT__V"],
            origin2=["variable"],
        ),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)


@pytest.mark.parametrize(
    "args",
    [[[0.05, 0.0], [0.05, 5]]],
)
def test_ramp_start(tl_anchor, args):
    tl_ramp = tl.ramp(tl_anchor, lockbox_MOT__V=args, duration=100e-3)

    tl_check = tl.create(
        [
            ["lockbox_MOT__V", [0.0, 0.0, "init"]],
            ["⚓_001", [0.0, 0.0, "init"]],
            [
                "lockbox_MOT__V",
                [[0.05, 0.0, "init"], [0.1, 5, "init"]],
            ],
        ],
    )
    tl_check["function"] = [np.nan, np.nan, ramp_function.tanh, ramp_function.tanh]
    return wt_frame.assert_equal(tl_ramp, tl_check)


# === Heterogeneous input is probably a bad idea
# @pytest.mark.parametrize(
#     "args",
#     [[[0.05], [0.05, 5]], [0.05, [0.05, 5]]],
# )
# def test_ramp_start2(tl_anchor, args):
#     tl_ramp = tl.ramp(tl_anchor, lockbox_MOT__V=args, duration=0.0)

#     tl_check = tl.create(
#         [
#             ["lockbox_MOT__V", [0.0, 0.0, "init"]],
#             ["⚓_001", [0.0, 0.0, "init"]],
#             [
#                 "lockbox_MOT__V",
#                 [[0.00, 0.05, "init"], [0.1, 5, "init"]],
#             ],
#         ],
#     )
#     tl_check["function"] = [np.nan, np.nan, ramp_function.tanh, ramp_function.tanh]
#     return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_expand():
    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[1.0, 10.0],
            origin=["lockbox_MOT__V", "lockbox_MOT__V"],
            origin2=["variable"],
        ),
        lambda tline: tl.expand(tline, time_resolution=0.2),
    )
    tl_check = wt_frame.new(
        [
            [1.0, "lockbox_MOT__V", 1.0, "badger"],
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


def test_random_ramp():
    tl_ramp = tl.stack(
        tl.create(
            ["device_pump", [0.0, 0.0, "ADwin_Init"]],
            ["lockbox_MOT__V", [1.0, 00.0, "ADwin_Init"]],
            ["lockbox_MOT__V", [2.0, 10.0, "blah"]],
            ["⚓_001", [2.5, 0.0, "blah"]],
            ["device_pump", [3.0, 1.0, "something_important"]],
            ["⚓_002", [3.5, 0.0, "something_important"]],
            ["lockbox_MOT__V", [6.0, 5.0, "something_important"]],
            ["device_pump", [7.0, 0.0, "ADwin_Finish"]],
            ["lockbox_MOT__V", [7.0, 0.0, "ADwin_Finish"]],
        ),
        tl.ramp(lockbox_MOT__V=11.0, duration=1.0, origin=["blah", "variable"]),
    )

    return wt_frame.assert_equal(
        tl_ramp[["variable", "time", "value", "context"]],
        wt_frame.new(
            [
                ["device_pump", 0.0, 0.0, "ADwin_Init"],
                ["lockbox_MOT__V", 1.0, 0.0, "ADwin_Init"],
                ["lockbox_MOT__V", 2.0, 10.0, "blah"],
                ["⚓_001", 2.5, 0.0, "blah"],
                ["device_pump", 3.0, 1.0, "something_important"],
                ["⚓_002", 3.5, 0.0, "something_important"],
                ["lockbox_MOT__V", 6.0, 5.0, "something_important"],
                ["device_pump", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox_MOT__V", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox_MOT__V", 2.5, 10.0, "blah"],
                ["lockbox_MOT__V", 3.5, 11.0, "blah"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


def test_rampReal():
    timeline = tl.stack(
        ex.init(),
        ex.MOT(duration=1),
        ex.MOT_detunedGrowth(),
        tl.ramp(t=1, duration=0.1, lockbox_MOT__MHz=-2),
        tl.ramp(t=0.5, duration=0.1, lockbox_MOT__MHz=-1),
    )
    timeline__simplified = timeline[timeline["time"] >= 0.0][
        ["variable", "time", "value"]
    ].reset_index(drop=True)

    expected = wt_frame.new(
        [
            ["shutter_MOT", 0.00, 1.00],
            ["shutter_repump", 0.00, 1.00],
            ["coil_MOTlower__A", 0.00, -1.00],
            ["coil_MOTupper__A", 0.00, -0.98],
            ["⚓_001", 1.00, 0.0],
            ["lockbox_MOT__MHz", 1.00, 0.00],
            ["lockbox_MOT__MHz", 1.01, -5.00],
            ["⚓_002", 1.10, 0.0],
            ["lockbox_MOT__MHz", 2.10, -5.00],
            ["lockbox_MOT__MHz", 2.20, -2.00],
            ["lockbox_MOT__MHz", 1.60, -5.00],
            ["lockbox_MOT__MHz", 1.70, -1.00],
        ],
        columns=["variable", "time", "value"],
    )

    # print(timeline__simplified)
    # print(expected)
    # display.channels(timeline, variables=["lockbox_MOT__MHz"])
    return wt_frame.assert_equal(
        timeline__simplified,
        expected,
    )


def test_rampReal2():
    timeline = tl.stack(
        ex.init(),
        ex.MOT(duration=1),
        ex.MOT_detunedGrowth(),
        tl.ramp(t=1, duration=0.1, lockbox_MOT__MHz=-2),
        tl.ramp(t=0.5, duration=0.1, lockbox_MOT__MHz=-1),
        tl.ramp(t=0.75, duration=0.1, lockbox_MOT__MHz=-5),
    )
    timeline__simplified = timeline[timeline["context"] == "MOT"][
        ["variable", "time", "value", "context"]
    ].reset_index(drop=True)

    # print(
    #     timeline[timeline["context"] == "MOT"][["variable", "time", "value", "context"]]
    # )

    expected = wt_frame.new(
        [
            ["shutter_MOT", 0.0, 1.0, "MOT"],
            ["shutter_repump", 0.0, 1.0, "MOT"],
            ["coil_MOTlower__A", 0.0, -1.0, "MOT"],
            ["coil_MOTupper__A", 0.0, -0.98, "MOT"],
            ["⚓_001", 1.0, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 1.0, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 1.01, -5.0, "MOT"],
            ["⚓_002", 1.1, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 2.1, -5.0, "MOT"],
            ["lockbox_MOT__MHz", 2.2, -2.0, "MOT"],
            ["lockbox_MOT__MHz", 1.6, -5.0, "MOT"],
            ["lockbox_MOT__MHz", 1.7000000000000002, -1.0, "MOT"],
            ["lockbox_MOT__MHz", 1.85, -1.0, "MOT"],
            ["lockbox_MOT__MHz", 1.9500000000000002, -5.0, "MOT"],
        ],
        columns=["variable", "time", "value", "context"],
    )

    return wt_frame.assert_equal(timeline__simplified, expected)


# Check that no-ops don't cause failures
def test_rampDoesNotRaise1(tl_anchor):
    tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=10.0, duration=1.0))


def test_rampDoesNotRaise2(tl_anchor):
    return wt_frame.assert_equal(
        tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=10.0, duration=0.0)), tl_anchor
    )


def test_rampDoesNotRaise3(tl_anchor):
    return wt_frame.assert_equal(
        tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=0.0, duration=1.0)), tl_anchor
    )
