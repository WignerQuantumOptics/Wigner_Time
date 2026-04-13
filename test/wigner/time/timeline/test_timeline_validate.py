import pytest

from wigner.time.internal.timeline import validate
from wigner.time.internal import dataframe as frame

# TODO:
# - Update the test schema to use min and max values rather than ranges
# - Consider whether the sanitize/validate namespace is actually useful.

devices001 = frame.new(
    [
        ["coil_compensationX__A", (-3, 3), (-3, 3)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)
devices002 = frame.new(
    [
        ["coil_compensationX__A", (-5, 5), (-3, 3)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)
devices003 = frame.new(
    [
        ["coil_compensationX__A", (-5, 5), (-5, 5)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)

df_sanitize001 = frame.new(
    [
        [0.0, "AOM_imaging", 0.0, ""],
        [0.0, "AOM_imaging", 0.0, ""],
        [0.0, "coil_compensationX__A", 0.0, "coil"],
        [0.0, "coil_compensationX__A", 10.0, "coil"],
        [10.0, "coil_compensationX__A", 5.0, "coil"],
    ],
    columns=["time", "variable", "value", "context"],
)


@pytest.mark.parametrize(
    "input_value", [[df_sanitize001, devices001], [df_sanitize001, devices002]]
)
def test_sanitize_raises(input_value):
    df, dev = input_value
    with pytest.raises(ValueError):
        validate.sanitize(frame.join(df, dev))


@pytest.mark.parametrize(
    "input_value",
    [
        [df_sanitize001, devices003],
    ],
)
def test_sanitize_success(input_value):
    df, dev = input_value
    return frame.assert_equal(
        validate.sanitize(df),
        frame.new(
            [
                [0.0, "AOM_imaging", 0.0, ""],
                [0.0, "coil_compensationX__A", 10.0, "coil"],
                [10.0, "coil_compensationX__A", 5.0, "coil"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )
