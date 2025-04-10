import pytest
import pandas as pd
from munch import Munch

from wigner_time import timeline as tl
from wigner_time import variable
from wigner_time.adwin import connection as adcon


@pytest.mark.parametrize(
    "input",
    [
        adcon.new("AOM_MOT__V", 1, 1),
        adcon.new(["AOM_MOT__V", 1, 1]),
    ],
)
def test_connectionSingle(input):
    return pd.testing.assert_frame_equal(
        input, pd.DataFrame([Munch(variable="AOM_MOT__V", module=1, channel=1)])
    )


def test_connectionMany():
    tst = adcon.new(
        ["shutter_MOT", 1, 11], ["shutter_repump", 1, 12], ["shutter_imaging", 1, 13]
    )
    return pd.testing.assert_frame_equal(
        tst,
        pd.DataFrame(
            [
                Munch(variable="shutter_MOT", module=1, channel=11),
                Munch(variable="shutter_repump", module=1, channel=12),
                Munch(variable="shutter_imaging", module=1, channel=13),
            ]
        ),
    )


def test_connectionName():
    assert (
        adcon.new(
            ["shutter_MOT", 1, 11],
            ["shutter_repump", 1, 12],
            ["shutter_imaging", 1, 13],
        )
        .variable.str.match(variable.REGEX)
        .all()
    )


def test_connectionName002():
    assert adcon.is_valid_name(
        adcon.new(
            ["shutter_MOT", 1, 11],
            ["shutter_repump", 1, 12],
            ["shutter_imaging", 1, 13],
        )
    )


def test_connectionName003():
    assert (
        adcon.is_valid_name(
            tl.create(
                ["shutter_MOT", 1, 11],
                ["shutter__repump", 1, 12],
                ["shutter_imaging", 1, 13],
            )
        )
        == False
    )


@pytest.mark.parametrize(
    "input",
    [
        ("AOMMOT__V", 1, 1),
        (["AOMMOT", 1, 1]),
    ],
)
def test_connectionSingleInvalid(input):
    with pytest.raises(ValueError):
        adcon.new(*input)
