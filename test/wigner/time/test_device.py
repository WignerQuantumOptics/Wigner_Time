import pytest
import numpy as np

from wignertime.internal import dataframe as wt_frame
from wignertime import device as dev


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

    return wt_frame.assert_equal(input, comparison)


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
    return wt_frame.assert_equal(
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


def test_check_safety_range001():
    df = dev.new(
        ["coil_compensationY__A", 0.33, -5, 5],
        ["coil_MOTlower__A", 0.5, -2.5, 3],
        ["coil_MOTupper__A", 0.5, -np.inf, np.inf],
    )
    df["value"] = [5.0, -2.5, 0.0]

    assert dev.check_within_range(df) == True


@pytest.mark.parametrize(
    "input",
    [
        -5.0001,
        5.00000001,
        -2.6,
        "test",
    ],
)
def test_check_safety_range002(input):
    df = dev.new(
        ["coil_compensationY__A", 0.33, -5, 5],
        ["coil_MOTlower__A", 0.5, -2.5, 3],
        ["coil_MOTupper__A", 0.5, -np.inf, np.inf],
    )
    df["value"] = input

    with pytest.raises(ValueError):
        dev.check_within_range(df)
