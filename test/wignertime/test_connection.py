import re

import pytest
from munch import Munch

from wignertime import timeline as tl
from wignertime import variable
from wignertime import config as wt_config
from wignertime.adwin import connection as adcon
from wignertime.internal import dataframe as wt_frame


@pytest.mark.parametrize(
    "input",
    [
        adcon.new("AOM__MOT__V", 1, 1),
        adcon.new(["AOM__MOT__V", 1, 1]),
    ],
)
def test_connectionSingle(input):
    return wt_frame.assert_equal(
        input, wt_frame.new([Munch(variable="AOM__MOT__V", module=1, channel=1)])
    )


def test_connectionMany():
    tst = adcon.new(
        ["shutter__MOT", 1, 11], ["shutter__repump", 1, 12], ["shutter__imaging", 1, 13]
    )
    return wt_frame.assert_equal(
        tst,
        wt_frame.new(
            [
                Munch(variable="shutter__MOT", module=1, channel=11),
                Munch(variable="shutter__repump", module=1, channel=12),
                Munch(variable="shutter__imaging", module=1, channel=13),
            ]
        ),
    )


def test_connectionName():
    connections = adcon.new(
        ["shutter__MOT", 1, 11],
        ["shutter__repump", 1, 12],
        ["shutter__imaging", 1, 13],
    )
    names = wt_frame.column(connections, "variable")
    assert all(re.match(wt_config.VARIABLE__REGEX, name) for name in names)


def test_connectionName002():
    assert adcon.is_valid_name(
        adcon.new(
            ["shutter__MOT", 1, 11],
            ["shutter__repump", 1, 12],
            ["shutter__imaging", 1, 13],
        )
    )


def test_connectionName003():
    assert (
        adcon.is_valid_name(
            tl._populate_timeline(
                ["shutter__MOT", 1, 11],
                ["shutter_repump", 1, 12],  # the old grammar, refused by the new one
                ["shutter__imaging", 1, 13],
                context="s",
            )
        )
        == False
    )


@pytest.mark.parametrize(
    "input",
    [
        ("AOM_MOT__V", 1, 1),  # the old grammar: a `_` in <device>
        (["AOMMOT", 1, 1]),
    ],
)
def test_connectionSingleInvalid(input):
    with pytest.raises(ValueError):
        adcon.new(*input)
