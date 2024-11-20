import pytest
import pandas as pd

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame


@pytest.fixture
def df_simple():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0.0, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "input",
    [
        tl.create("AOM_imaging", 0.0, 0.0),
        tl.create("AOM_imaging", [[0.0, 0.0]]),
    ],
)
def test_createSimple(input, df_simple):
    return wt_frame.assert_equal(input, df_simple)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[0.0, 1.0]]],
            ],
            context="init",
        ),
        tl.create(
            [
                ["AOM_imaging", 0.0],
                ["AOM_imaging__V", 2],
                ["AOM_repump", 1.0],
            ],
            context="init",
            t=0.0,
        ),
        tl.create(
            ["AOM_imaging", 0.0],
            ["AOM_imaging__V", 2],
            ["AOM_repump", 1.0],
            context="init",
            t=0.0,
        ),
        tl.create(
            context="init",
            t=0.0,
            AOM_imaging=0.0,
            AOM_imaging__V=2,
            AOM_repump=1.0,
        ),
    ],
)
def test_createDifferent(input, df):
    return wt_frame.assert_equal(input, df)
