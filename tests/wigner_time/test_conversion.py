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
            -3,
            3,
        ),
    )
    print(df_devs)

    return pd.testing.assert_frame_equal(
        conv.add_linear(df_devs, "V"),
        wt_frame.new(
            {
                "time": [0.0, 0.0, 0.0, 0.0],
                "variable": ["AOM_imaging", "AOM_imaging__V", "AOM_repump", "virtual"],
                "value": [0.0, 2.0, 1.0, 1.0],
                "context": ["init", "init", "init", "MOT"],
                "unit__min": [None, -3, None, None],
                "unit__max": [None, 3, None, None],
                "safety__min": [None, -3, None, None],
                "safety__max": [None, 3, None, None],
                "value__digits": [None, 54612, None, None],
            }
        ),
    )
