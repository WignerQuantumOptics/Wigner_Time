import pytest

from wigner_time import util


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
