import pytest
import numpy as np
import pandas as pd
from munch import Munch

from wigner_time.internal import dataframe as wt_frame
from wigner_time import device as dev


@pytest.mark.parametrize(
    "input",
    [
        dev.new(
            "coil_compensationX__A",
            3 / 10.0,
            -3.0,
            3.0,
        ),
        dev.new(
            [
                "coil_compensationX__A",
                3 / 10.0,
                -3.0,
                3.0,
            ]
        ),
    ],
)
def test_deviceSingle(input):
    comparison = wt_frame.new_schema(
        [
            [
                "coil_compensationX__A",
                3 / 10.0,
                -3.0,
                3.0,
            ]
        ],
        dev.SCHEMA__expanded,
    )

    return pd.testing.assert_frame_equal(input, comparison)


@pytest.mark.parametrize(
    "input",
    [
        dev.new(
            ["coil_compensationY__A", 0.33, -np.inf, np.inf],
            ["coil_MOTlower__A", 0.5, -np.inf, np.inf],
            ["coil_MOTupper__A", 0.5, -np.inf, np.inf],
        ),
        dev.new(
            ["coil_compensationY__A", 0.33],
            ["coil_MOTlower__A", 0.5, -np.inf],
            ["coil_MOTupper__A", 0.5],
        ),
    ],
)
def test_deviceMultiple(input):
    return pd.testing.assert_frame_equal(
        input,
        wt_frame.new_schema(
            [
                ["coil_compensationY__A", 0.33, -np.inf, +np.inf],
                ["coil_MOTlower__A", 0.5, -np.inf, +np.inf],
                ["coil_MOTupper__A", 0.5, -np.inf, +np.inf],
            ],
            dev.SCHEMA__expanded,
        ),
    )


def test_input_number():
    with pytest.raises(ValueError):
        dev.new("coil_compensationX__A", 3 / 10.0, -3.0, 3.0, 5.0)


@pytest.fixture
def func():
    return "does things"


@pytest.mark.parametrize(
    "input",
    [
        ["coil_compensationY__A", func],
        # ["coil_compensationY__A", lambda x: "does things"],
    ],
)
def test_function(input):
    wt_frame.assert_equal(
        dev.new(*input),
        wt_frame.new_schema(
            [
                ["coil_compensationY__A", func, -np.inf, +np.inf],
            ],
            dev.SCHEMA,
        ),
    )


@pytest.mark.parametrize(
    "input",
    [
        ["coil_compensationY__A", func, -3, 3],
    ],
)
def test_function002(input):
    wt_frame.assert_equal(
        dev.new(*input),
        wt_frame.new_schema(
            [
                ["coil_compensationY__A", func, -3, 3],
            ],
            dev.SCHEMA,
        ),
    )
