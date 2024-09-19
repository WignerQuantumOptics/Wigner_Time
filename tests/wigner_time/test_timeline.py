import pytest
import pandas as pd

from wigner_time import timeline as tl


@pytest.fixture
def df_simple():
    return pd.DataFrame(
        [
            [0.0, "AOM_imaging", 0.0, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return pd.DataFrame(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df_wait():
    return pd.DataFrame(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
            [10.0, "AOM_repump", 0, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def dfseq():
    return pd.DataFrame(
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


def test_createSimple(df_simple):
    tst = tl.create("AOM_imaging", 0.0, 0.0)
    return pd.testing.assert_frame_equal(tst, df_simple)


def test_createSingle(df_simple):
    tst = tl.create("AOM_imaging", [[0.0, 0.0]])
    return pd.testing.assert_frame_equal(tst, df_simple)


def test_createOriginal(df):
    tst = tl.create(
        [
            ["AOM_imaging", [[0.0, 0.0]]],
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[0.0, 1.0]]],
        ],
        context="init",
    )
    return pd.testing.assert_frame_equal(tst, df)


def test_createManyListPairs(df):
    tst = tl.create(
        [
            ["AOM_imaging", 0.0],
            ["AOM_imaging__V", 2],
            ["AOM_repump", 1.0],
        ],
        context="init",
        t=0.0,
    )
    return pd.testing.assert_frame_equal(tst, df)


def test_createManyArgs(df):
    tst = tl.create(
        ["AOM_imaging", 0.0],
        ["AOM_imaging__V", 2],
        ["AOM_repump", 1.0],
        context="init",
        t=0.0,
    )
    return pd.testing.assert_frame_equal(tst, df)


def test_createManyKWargs(df):
    tst = tl.create(
        context="init",
        t=0.0,
        AOM_imaging=0.0,
        AOM_imaging__V=2,
        AOM_repump=1.0,
    )
    return pd.testing.assert_frame_equal(tst, df)


def test_updateArgs(dfseq):
    tst = tl.update(
        tl.create("lockbox_MOT__V", [[0.0, 0.0]]),
        tl.wait(5.0, "lockbox_MOT__V"),
        tl.shift("lockbox_MOT__V", 1.0, 1.0, fargs={"time_resolution": 0.2}),
        tl.wait(),  # This shouldn't do anything for a timeline of a single variable.
    )
    return pd.testing.assert_frame_equal(tst, dfseq)


def test_waitVariable(df_wait):
    return pd.testing.assert_frame_equal(
        tl.wait(variables=["AOM_imaging"], timeline=df_wait, context="test"),
        pd.DataFrame(
            {
                "time": {0: 0.0, 1: 0.0, 2: 0.0, 3: 10.0, 4: 10.0},
                "variable": {
                    0: "AOM_imaging",
                    1: "AOM_imaging__V",
                    2: "AOM_repump",
                    3: "AOM_repump",
                    4: "AOM_imaging",
                },
                "value": {0: 0.0, 1: 2.0, 2: 1.0, 3: 0.0, 4: 0.0},
                "context": {0: "init", 1: "init", 2: "init", 3: "init", 4: "test"},
            }
        ),
    )


def test_waitAll(df_wait):
    return pd.testing.assert_frame_equal(
        tl.wait(timeline=df_wait),
        pd.DataFrame(
            [
                [0.0, "AOM_imaging", 0.0, "init"],
                [0.0, "AOM_imaging__V", 2.0, "init"],
                [0.0, "AOM_repump", 1.0, "init"],
                [10.0, "AOM_repump", 0.0, "init"],
                [10.0, "AOM_imaging", 0.0, "init"],
                [10.0, "AOM_imaging__V", 2.0, "init"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


###########################################################################
#                               scratch                                   #
###########################################################################

import importlib
