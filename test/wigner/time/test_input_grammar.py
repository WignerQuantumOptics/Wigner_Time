"""
The input grammar of `create`, exercised over shapes rather than over examples.

C5 asked for the grammar to be settled, documented and made total: every shape should
either produce the documented frame or raise, with nothing landing in between. These
tests are the "nothing in between" half.
"""

import itertools

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame

VARIABLE = "AOM_imaging"
FOLLOWS = [
    (1.0, dict(time=0.0, value=1.0, context="")),
    ([2.0, 1.0], dict(time=2.0, value=1.0, context="")),
    ([2.0, 1.0, "ctx"], dict(time=2.0, value=1.0, context="ctx")),
]


def _one(frame):
    assert len(frame) == 1
    row = frame.iloc[0]
    return dict(time=row["time"], value=row["value"], context=row["context"])


@pytest.mark.parametrize("follows,expected", FOLLOWS)
def test_the_three_ways_of_naming_a_variable_agree(follows, expected):
    """
    Keyword, flat positional and row positional are one grammar, not three.

    They did not agree before: the row form read only its second element and dropped the
    rest, so `["v", t, value, context]` produced the *time* as its value and lost the
    context entirely (A10 / #58).
    """
    by_keyword = tl.create(**{VARIABLE: follows})
    by_row = tl.create([VARIABLE, follows])

    assert _one(by_keyword) == expected
    wt_frame.assert_equal(by_row, by_keyword)

    if isinstance(follows, list):
        # the brackets around `<follows>` are optional in the positional forms
        wt_frame.assert_equal(tl.create([VARIABLE, *follows]), by_keyword)
        wt_frame.assert_equal(tl.create(VARIABLE, *follows), by_keyword)
    else:
        wt_frame.assert_equal(tl.create(VARIABLE, follows), by_keyword)


def test_several_instants_for_one_variable():
    frame = tl.create(**{VARIABLE: [[0.0, 1.0], [2.0, 0.0]]})
    assert list(frame["time"]) == [0.0, 2.0]
    assert list(frame["value"]) == [1.0, 0.0]


def test_rows_may_be_batched():
    wt_frame.assert_equal(
        tl.create([["a_x__V", 1.0], ["b_y__V", 2.0]]),
        tl.create(["a_x__V", 1.0], ["b_y__V", 2.0]),
    )


@pytest.mark.parametrize("follows,expected", FOLLOWS)
def test_t_and_context_are_defaults_not_overrides(follows, expected):
    frame = tl.create(**{VARIABLE: follows}, t=99.0, context="kw")

    assert frame.iloc[0]["time"] == (
        99.0 if not isinstance(follows, list) else expected["time"]
    )
    assert frame.iloc[0]["context"] == (
        "kw" if expected["context"] == "" else expected["context"]
    )


def test_mixing_positional_and_keyword_raises():
    """
    A11. The keywords used to be discarded in silence, so the variable was absent from
    the experiment rather than merely mis-stated.
    """
    with pytest.raises(ValueError, match="cannot be mixed"):
        tl.create(["a_x__V", 1.0], b_y__V=2.0)


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda: tl.create([]), id="empty row"),
        pytest.param(
            lambda: tl.create(["a_x__V", 1.0], []), id="empty row among others"
        ),
        pytest.param(lambda: tl.create(VARIABLE), id="name with nothing following"),
        pytest.param(lambda: tl.create(VARIABLE, 1, 2, 3, 4), id="too many elements"),
        pytest.param(
            lambda: tl.create(**{VARIABLE: [[[[1.0, 2.0]]]]}), id="too deeply nested"
        ),
    ],
)
def test_unsupported_shapes_raise_rather_than_guess(call):
    """
    Every rejection must name what arrived. They used to cite `__ensure_time_context`, a
    private function, or escape as a bare `IndexError: list index out of range`.
    """
    with pytest.raises(ValueError) as caught:
        call()

    assert "__ensure_time_context" not in str(caught.value)


def test_no_shape_lands_in_between():
    """
    The totality property C5 asks for: across a generated spread of shapes, each either
    produces a frame with the documented columns or raises `ValueError` -- never a
    partial frame, a silent drop, or an error from inside pandas or numpy.
    """
    scalars = [1.0, 0]
    pairs = [[t, v] for t, v in itertools.product([0.0, 2.0], scalars)]
    triples = [[0.0, 1.0, "c"]]
    nested = [[[0.0, 1.0], [1.0, 2.0]]]
    malformed = [[], [1.0, 2.0, 3.0, 4.0], [[[[1.0]]]], "string", {}]

    shapes = scalars + pairs + triples + nested + malformed
    builders = [
        lambda f: tl.create(**{VARIABLE: f}),
        lambda f: tl.create([VARIABLE, f]),
        lambda f: tl.create(VARIABLE, f),
    ]

    for follows, build in itertools.product(shapes, builders):
        try:
            frame = build(follows)
        except ValueError:
            continue
        assert list(frame.columns) == ["time", "variable", "value", "context"]
        assert len(frame) >= 1
        assert set(frame["variable"]) == {VARIABLE}
