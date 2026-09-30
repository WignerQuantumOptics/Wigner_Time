import pytest
import numpy as np

from wignertime.internal import dataframe as wt_frame
from wignertime import device as dev
from wignertime.adwin import connection as adcon


@pytest.mark.parametrize(
    "input",
    [
        dev.new(
            "coil__compensation_X__A",
            3 / 10.0,
            -3.0,
            3.0,
        ),
        dev.new(
            [
                "coil__compensation_X__A",
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
                "coil__compensation_X__A",
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
            ["coil__compensation_Y__A", 0.33, -np.inf, np.inf],
            ["coil__MOT_lower__A", 0.5, -np.inf, np.inf],
            ["coil__MOT_upper__A", 0.5, -np.inf, np.inf],
        ),
        dev.new(
            ["coil__compensation_Y__A", 0.33],
            ["coil__MOT_lower__A", 0.5, -np.inf],
            ["coil__MOT_upper__A", 0.5],
        ),
    ],
)
def test_deviceMultiple(input):
    return wt_frame.assert_equal(
        input,
        wt_frame.new_schema(
            [
                ["coil__compensation_Y__A", 0.33, -np.inf, +np.inf],
                ["coil__MOT_lower__A", 0.5, -np.inf, +np.inf],
                ["coil__MOT_upper__A", 0.5, -np.inf, +np.inf],
            ],
            dev.SCHEMA__expanded,
        ),
    )


def test_input_number():
    with pytest.raises(ValueError):
        dev.new("coil__compensation_X__A", 3 / 10.0, -3.0, 3.0, 5.0)


@pytest.fixture
def func():
    return "does things"


@pytest.mark.parametrize(
    "input",
    [
        ["coil__compensation_Y__A", func],
        # ["coil__compensation_Y__A", lambda x: "does things"],
    ],
)
def test_function(input):
    wt_frame.assert_equal(
        dev.new(*input),
        wt_frame.new_schema(
            [
                ["coil__compensation_Y__A", func, -np.inf, +np.inf],
            ],
            dev.SCHEMA,
        ),
    )


@pytest.mark.parametrize(
    "input",
    [
        ["coil__compensation_Y__A", func, -3, 3],
    ],
)
def test_function002(input):
    wt_frame.assert_equal(
        dev.new(*input),
        wt_frame.new_schema(
            [
                ["coil__compensation_Y__A", func, -3, 3],
            ],
            dev.SCHEMA,
        ),
    )


def test_check_safety_range001():
    df = dev.new(
        ["coil__compensation_Y__A", 0.33, -5, 5],
        ["coil__MOT_lower__A", 0.5, -2.5, 3],
        ["coil__MOT_upper__A", 0.5, -np.inf, np.inf],
    )
    df = wt_frame.with_column(df, "value", [5.0, -2.5, 0.0])

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
        ["coil__compensation_Y__A", 0.33, -5, 5],
        ["coil__MOT_lower__A", 0.5, -2.5, 3],
        ["coil__MOT_upper__A", 0.5, -np.inf, np.inf],
    )
    df = wt_frame.with_column(df, "value", input)

    with pytest.raises(ValueError):
        dev.check_within_range(df)


# --- A14: the two tables must describe the same apparatus ---------------------


def test_device_refuses_a_malformed_name():
    """Parity with `connection.new`, which has always refused one."""
    with pytest.raises(ValueError, match="do not follow the naming convention"):
        dev.new(["notavariable", 1.0, -1, 1])


def test_a_mistyped_device_name_no_longer_passes_silently():
    """
    A14. `coil__MOTT__A` is a perfectly well-formed name, so the shape check cannot catch
    it. The device row joined to nothing, the variable arrived with no bounds, and
    `check_within_range` reads absent bounds as a digital line and skips: 500 A passed on
    a coil declared +/-5 A.
    """
    connections = adcon.new(["coil__MOT__A", 4, 1])
    devices = dev.new(["coil__MOTT__A", 2.0, -5.0, 5.0])

    with pytest.raises(ValueError, match="do not describe the same apparatus"):
        dev.check_correspondence(connections, devices)


def test_an_analogue_channel_without_a_device_is_refused():
    connections = adcon.new(["coil__MOT__A", 4, 1])
    with pytest.raises(ValueError, match="connected, analogue, but no device"):
        dev.check_correspondence(connections, dev.new())


def test_a_digital_channel_needs_no_device():
    """No unit means digital, and a digital line has nothing to calibrate or bound."""
    connections = adcon.new(["shutter__MOT", 1, 11], ["AOM__MOT", 1, 1])
    assert dev.check_correspondence(connections, dev.new())


def test_an_empty_device_table_is_a_table():
    """A purely digital apparatus has no devices; that is a description, not a mistake."""
    devices = dev.new()
    assert wt_frame.n_rows(devices) == 0
    assert wt_frame.columns(devices) == ["variable", "to_V", "value__min", "value__max"]
