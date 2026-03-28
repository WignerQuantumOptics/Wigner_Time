import pytest

from wigner_time import util
from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame


@pytest.mark.parametrize(
    "input",
    ["thing", ["thing"], [["thing"]]],
)
def test_ensure_2d(input):
    assert util.ensure_2d(input) == [["thing"]]


@pytest.mark.parametrize(
    "input",
    [5, [5], [[5]]],
)
def test_ensure_2d_nums(input):
    assert util.ensure_2d(input) == [[5]]


@pytest.mark.parametrize(
    "input",
    [["AOM_MOT__V", 1, 1], [["AOM_MOT__V", 1, 1]]],
)
def test_ensure_2d_multi(input):
    assert util.ensure_2d(input) == [["AOM_MOT__V", 1, 1]]


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
        tl.update(AOM_imaging__V=[1.0, 0.0]),
    )

    return wt_frame.assert_equal(
        actual[["time", "variable", "value"]],
        tl.create(AOM_imaging__V=[[0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [2.0, 0.0]])[
            ["time", "variable", "value"]
        ],
    )
