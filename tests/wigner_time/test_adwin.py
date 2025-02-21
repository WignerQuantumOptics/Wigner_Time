import pathlib as pl
import sys
import pytest
import pandas as pd

from wigner_time.adwin import core as adwin
from wigner_time.adwin import connection as con
from wigner_time import device
from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame

sys.path.append(str(pl.Path.cwd() / "doc"))
import experiment as ex


@pytest.fixture
def df_simple():
    return pd.DataFrame(
        [
            [0.0, "AOM_imaging", 0.0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1.0, "init"],
            [0.0, "virtual", 1.0, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def connections_simple():
    return con.new(
        ["AOM_imaging", 1, 1],
        ["AOM_imaging__V", 1, 2],
        ["AOM_repump", 2, 3],
    )


def test_remove_unconnected_variables(df_simple, connections_simple):
    return pd.testing.assert_frame_equal(
        adwin.remove_unconnected_variables(df_simple, connections_simple),
        pd.DataFrame(
            {
                "time": [0.0] * 3,
                "variable": ["AOM_imaging", "AOM_imaging__V", "AOM_repump"],
                "value": [0.0, 2.0, 1.0],
                "context": ["init"] * 3,
            }
        ),
    )


def test_add_linear_conversion(df_simple):
    df_devs = device.add(
        df_simple,
        device.new(
            "AOM_imaging__V",
            -3,
            3,
        ),
    )

    return pd.testing.assert_frame_equal(
        adwin.add_linear_conversion(df_devs, "V"),
        pd.DataFrame(
            {
                "time": [0.0, 0.0, 0.0, 0.0],
                "variable": ["AOM_imaging", "AOM_imaging__V", "AOM_repump", "virtual"],
                "value": [0.0, 2.0, 1.0, 1.0],
                "context": ["init", "init", "init", "MOT"],
                "unit_range": [None, (-3, 3), None, None],
                "safety_range": [None, (-3, 3), None, None],
                "value__digits": [None, 54613.0, None, None],
            }
        ),
    )


def test_add_cycle():
    df = pd.DataFrame({"time": range(10), "value": range(11, 21)})
    df["context"] = (
        ["MOT"] * 4 + ["ADwin_LowInit"] * 3 + ["ADwin_Init"] * 2 + ["ADwin_Finish"]
    )
    tst = frame.cast(adwin.add_cycle(df), adwin.SCHEMA)

    return pd.testing.assert_frame_equal(
        tst,
        frame.cast(
            pd.DataFrame(
                {
                    "time": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                    "value": [11, 12, 13, 14, 15.0, 16, 17, 18, 19, 20],
                    "context": [
                        "MOT",
                        "MOT",
                        "MOT",
                        "MOT",
                        "ADwin_LowInit",
                        "ADwin_LowInit",
                        "ADwin_LowInit",
                        "ADwin_Init",
                        "ADwin_Init",
                        "ADwin_Finish",
                    ],
                    "cycle": [
                        0,
                        200000,
                        400000,
                        600000,
                        -2,
                        -2,
                        -2,
                        -1,
                        -1,
                        2147483647,
                    ],
                }
            ),
            adwin.SCHEMA,
        ),
    )


###############################################################################
#                        dealing with special contexts                        #
###############################################################################

df_special1 = frame.new(
    [
        [0.0, "AOM_imaging", 0.0, "ADwin_Init"],
        [10.0, "AOM_imaging", 0.0, "ADwin_Init"],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM_repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)


df_special2 = frame.new(
    [
        [0.0, "AOM_imaging", 0, "ADwin_Init"],
        [10.0, "AOM_imaging", 1, "ADwin_Init"],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM_repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)

df_special3 = frame.cast(
    frame.new(
        [
            [0.0, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [0.0, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
            [0.0, "AOM_imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
        ],
        columns=[
            "time",
            "variable",
            "value",
            "context",
            "module",
            "channel",
            "cycle",
            "value_digits",
        ],
    ),
    adwin.SCHEMA,
)


df_special3__corrected = frame.cast(
    frame.new(
        [
            [-1, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [-1, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
            [2**31 - 1, "AOM_imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
        ],
        columns=[
            "time",
            "variable",
            "value",
            "context",
            "module",
            "channel",
            "cycle",
            "value_digits",
        ],
    ),
    adwin.SCHEMA,
)


df_special4 = frame.new_schema(
    [
        [0.0, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
        [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
    ],
    schema=adwin.SCHEMA,
)


@pytest.mark.parametrize("input_value", [df_special1, df_special2])
def test_sanitize_raises(input_value):
    with pytest.raises(ValueError):
        adwin.sanitize_special_contexts(input_value)


def test_sanitize_success():
    return pd.testing.assert_frame_equal(
        adwin.sanitize(df_special3), df_special3__corrected
    )


def test_to_adbasic():
    connections = con.new(
        ["shutter_MOT", 1, 11],
        ["lockbox_MOT__MHz", 3, 8],
    )

    devices = pd.DataFrame(
        columns=["variable", "unit_range", "safety_range"],
        data=[
            ["lockbox_MOT__V", (-10, 10), (-10, 10)],
            ["lockbox_MOT__MHz", (-200, 200), (-200, 200)],
        ],
    )

    print(
        tl.stack(
            tl.create(
                lockbox_MOT__MHz=0.0,
                shutter_MOT=0,
                context="ADwin_LowInit",
            ),
            tl.anchor(t=0.0, origin=0.0, context="InitialAnchor"),
            tl.update(
                shutter_MOT=1,
                context="MOT",
            ),
            tl.anchor(15),
            tl.ramp(
                lockbox_MOT__MHz=-5,
                duration=10e-3,
                context="MOT",
            ),
            tl.anchor(100e-3),
        )
    )

    tuples = adwin.to_data(
        tl.stack(
            tl.create(
                lockbox_MOT__MHz=0.0,
                shutter_MOT=0,
                context="ADwin_LowInit",
            ),
            tl.anchor(t=0.0, origin=0.0, context="InitialAnchor"),
            tl.update(
                shutter_MOT=1,
                context="MOT",
            ),
            tl.anchor(15),
            tl.ramp(
                lockbox_MOT__MHz=-5,
                duration=10e-3,
                context="MOT",
            ),
            tl.anchor(100e-3),
        ),
        connections,
        devices,
        time_resolution=5e-3,
    )
    tuples__guess = [
        [
            (-2, 3, 8, 32768),
            (3000000, 3, 8, 32768),
            (3001000, 3, 8, 32358),
            (3002000, 3, 8, 31949),
        ],
        [
            (-2, 1, 11, 0),
            (0, 1, 11, 1),
        ],
    ]

    # assert False
    assert tuples == tuples__guess
