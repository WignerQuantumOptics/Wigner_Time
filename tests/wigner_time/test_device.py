import pytest
import pandas as pd
from munch import Munch

from wigner_time.internal import dataframe as wt_frame
from wigner_time import device as dev


@pytest.mark.parametrize(
    "input",
    [
        dev.new(
            "coil_compensationX__A",
            -3,
            3,
            -2.5,
            2.5,
        ),
        dev.new(
            [
                "coil_compensationX__A",
                -3,
                3,
                -2.5,
                2.5,
            ]
        ),
    ],
)
def test_connectionSingle(input):
    return pd.testing.assert_frame_equal(
        input,
        wt_frame.new(
            [["coil_compensationX__A", -3.0, 3.0, -2.5, 2.5]],
            [
                "variable",
                "unit__min",
                "unit__max",
                "safety__min",
                "safety__max",
            ],
        ),
    )


@pytest.mark.parametrize(
    "input",
    [
        dev.new(
            ["coil_compensationY__A", -3, 3, -3, 3],
            ["coil_MOTlower__A", -5, 5, -5, 5],
            ["coil_MOTupper__A", -5, 5, -5, 5],
        ),
        dev.new(
            ["coil_compensationY__A", -3, 3],
            ["coil_MOTlower__A", -5, 5],
            ["coil_MOTupper__A", -5, 5],
        ),
    ],
)
def test_connectionMultiple(input):
    return pd.testing.assert_frame_equal(
        input,
        pd.DataFrame(
            [
                Munch(
                    variable="coil_compensationY__A",
                    unit__min=-3,
                    unit__max=3,
                    safety__min=-3,
                    safety__max=3,
                ),
                Munch(
                    variable="coil_MOTlower__A",
                    unit__min=-5,
                    unit__max=5,
                    safety__min=-5,
                    safety__max=5,
                ),
                Munch(
                    variable="coil_MOTupper__A",
                    unit__min=-5,
                    unit__max=5,
                    safety__min=-5,
                    safety__max=5,
                ),
            ]
        ).astype(
            {
                "variable": str,
                "unit__min": float,
                "unit__max": float,
                "safety__min": float,
                "safety__max": float,
            }
        ),
    )


@pytest.mark.parametrize(
    "input",
    [
        [
            ["coil_compensationY__A", -3, 3, -3, 3],
            ["coil_MOTlower__A", -5, 5, -5, 5],
            ["coil_MOTupper__A", -5, 5, -6, 5],
        ]
    ],
)
def test_SafetyOverUnit(input):
    with pytest.raises(ValueError):
        dev.new(*input)


def test_nonlinearConversion():
    # TODO:
    return
