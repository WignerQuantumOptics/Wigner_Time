import pytest

from wigner_time import timeline as tl
from wigner_time import util as wt_util
from wigner_time.internal import dataframe as wt_frame

# @pytest.fixture
# @pytest.mark.parametrize(
#     "input",
#     [
#         tl.create("AOM_imaging", [[0.0, 0.0]]),
#     ],
# )


def test_function__deferred():
    tl.ramp(AOM_imaging__V=[1.0, 1.0])

    actual = tl.stack(
        tl.create("AOM_imaging__V", 0.0, 0.0),
        tl.ramp(AOM_imaging__V=[1.0, 1.0]),
        #
    )

    return wt_frame.assert_equal(
        actual[["time", "variable", "value"]],
        tl.create(AOM_imaging__V=[[0.0, 0.0], [0.0, 0.0], [1.0, 1.0]])[
            ["time", "variable", "value"]
        ],
    )
