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
                "value__digits": [None, 54613.0, None, None],
            }
        ),
    )
