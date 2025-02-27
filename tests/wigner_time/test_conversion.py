import pytest
import pandas as pd
from munch import Munch

from wigner_time.internal import dataframe as wt_frame
from wigner_time import timeline as tl
from wigner_time import device
from wigner_time import conversion as conv


@pytest.fixture
def df_simple():
    return tl.create(
        AOM_imaging=[0.0, 0.0, "init"],
        AOM_imaging__V=[0.0, 2.0, "init"],
        AOM_repump=[0.0, 1.0, "init"],
        virtual=[0.0, 1.0, "MOT"],
    )


@pytest.mark.parametrize(
    "gain",
    [1, 2, 4, 8],
)
def test_unit_to_digits(gain):
    assert conv.unit_to_digits(0, [-10, 10], gain=gain) == 2**15


@pytest.mark.parametrize(
    "input",
    list(zip([10, 5, 2.5, 1.25], [1, 2, 4, 8])),
)
def test_unit_to_digits002(input):
    assert conv.unit_to_digits(input[0], [-10, 10], gain=input[1]) == 2**16 - 1


def test_add_linear_conversion(df_simple):
    df_devs = device.add(
        df_simple,
        device.new(
            "AOM_imaging__V",
            1.0,
            -3,
            3,
        ),
    )

    df_added = conv._add_linear(df_devs)

    return pd.testing.assert_frame_equal(
        df_added,
        wt_frame.new(
            {
                "time": [0.0, 0.0, 0.0, 0.0],
                "variable": ["AOM_imaging", "AOM_imaging__V", "AOM_repump", "virtual"],
                "value": [0.0, 2.0, 1.0, 1.0],
                "context": ["init", "init", "init", "MOT"],
                "to_V": [None, 1.0, None, None],
                "value__min": [None, -3, None, None],
                "value__max": [None, 3, None, None],
                "value__digits": [None, 39321, None, None],
            }
        ).astype(
            {
                "time": float,
                "variable": str,
                "value": float,
                "context": str,
                "to_V": float,
                "value__min": float,
                "value__max": float,
                "value__digits": "Int32",
            }
        ),
    )


def test_add():
    df_devs = device.add(
        tl.create(
            AOM_imaging=[0.0, 0.0, "init"],
            AOM_imaging__transparency=[0.0, 0.5, "init"],
            coil_MOT__A=[0.0, 1.0, "init"],
            virtual=[0.0, 1.0, "MOT"],
        ),
        device.new(
            [
                "AOM_imaging__transparency",
                lambda x: x + 10,
                0.0,
                1.0,
            ],
            ["coil_MOT__A", 0.333, -5.0, 5.0],
        ),
    )

    print(conv.add(df_devs))
    assert False
