import pytest

from wignertime.timeline import build as tl

from wignertime.internal import tags as wt_tags
from wignertime.timeline.internal import stages as wt_stages
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util


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
    [["AOM__MOT__V", 1, 1], [["AOM__MOT__V", 1, 1]]],
)
def test_ensure_2d_multi(input):
    assert util.ensure_2d(input) == [["AOM__MOT__V", 1, 1]]


# @pytest.fixture
# @pytest.mark.parametrize(
#     "input",
#     [
#         wt_stages.populate_timeline("AOM__imaging", [[0.0, 0.0]]),
#     ],
# )


def test_function__deferred():
    tl.ramp(AOM__imaging__V=[1.0, 1.0])

    actual = tl.to_timeline(
        tl.stack(
            tl.ramp(AOM__imaging__V=[1.0, 1.0]),
            tl.update(AOM__imaging__V=[1.0, 0.0]),
        ),
        onto=wt_stages.populate_timeline("AOM__imaging__V", 0.0, 0.0, context="s"),
    )

    return wt_frame.assert_equal(
        actual[["time", "variable", "value"]],
        tl.to_timeline(
            tl.update(
                AOM__imaging__V=[[0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [2.0, 0.0]],
                context="s",
            )
        )[["time", "variable", "value"]],
    )


###############################################################################
#   D3 / #117 -- a shared default must not be reachable through `ensure_pair`
###############################################################################


@pytest.mark.parametrize(
    "input",
    [["a", 0.0], ["a"], [], ("a", 0.0)],
)
def test_ensure_pair_never_returns_its_argument(input):
    """
    The package's single normalisation point for origins must hand back a new list.

    A signature default like `ramp`'s `origin2=[wt_tags.VARIABLE, 0.0]` is one object shared
    by every call in the process. That is safe only while nothing downstream can write
    through it, and `ensure_pair` is the one place everything downstream comes from.
    Until 2026-09-22 the two-element case returned the argument itself while the
    one-element and empty cases built a fresh list -- an asymmetry with no reason
    behind it and the whole of the exposure.
    """
    assert util.ensure_pair(input) is not input


def test_ensure_pair_normalises_a_tuple_to_a_list():
    """An immutable default is a legitimate way to write one, and must not change the type."""
    assert util.ensure_pair(("a", 0.0)) == ["a", 0.0]
