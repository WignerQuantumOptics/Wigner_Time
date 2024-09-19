import pytest
import pandas as pd
from munch import Munch

from wigner_time import connection as con


def test_connectionSingleDict():
    tst = con.connection("AOM_MOT__V", 1, 1, type="dict")
    assert tst == Munch(variable="AOM_MOT__V", module=1, channel=1)


def test_connectionManyDict():
    tst = con.connection(
        ["shutter_MOT", 1, 11],
        ["shutter_repump", 1, 12],
        ["shutter_imaging", 1, 13],
        type="dict"
    )
    assert tst == [
        Munch(variable="shutter_MOT", module=1, channel=11),
        Munch(variable="shutter_repump", module=1, channel=12),
        Munch(variable="shutter_imaging", module=1, channel=13),
    ]


def test_connectionSingleDataFrame():
    tst = con.connection("AOM_MOT__V", 1, 1)
    return pd.testing.assert_frame_equal(tst, pd.DataFrame([Munch(variable="AOM_MOT__V", module=1, channel=1)]))



def test_connectionManyDataFrame():
    tst = con.connection(
        ["shutter_MOT", 1, 11],
        ["shutter_repump", 1, 12],
        ["shutter_imaging", 1, 13]

    )
    return pd.testing.assert_frame_equal(tst,pd.DataFrame([
        Munch(variable="shutter_MOT", module=1, channel=11),
        Munch(variable="shutter_repump", module=1, channel=12),
        Munch(variable="shutter_imaging", module=1, channel=13),
    ]))
