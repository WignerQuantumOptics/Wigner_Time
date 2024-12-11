import pytest
import pandas as pd

from wigner_time.internal import dataframe as frame
from wigner_time.internal import origin


@pytest.fixture
def df_001():
    return frame.new(
        [
            ["thing2", 7.0, 5.0, "init"],
            ["thing", 0.0, 5.0, "init"],
            ["⚓__001", 4.5, 5.0, "MOT"],
            ["thing3", 3.0, 5.0, "blah"],
        ],
        columns=["variable", "time", "value", "context"],
    )


@pytest.fixture
def df_002():
    return frame.new(
        [
            ["thing2", 7.0, 5.0, "init"],
            ["thing", 0.0, 5.0, "init"],
            ["thing3", 3.0, 5.0, "blah"],
        ],
        columns=["variable", "time", "value", "context"],
    )


def test_originFailSafely(df_001):
    assert origin.find(df_001) == [None, None]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, "anchor"),
    ],
)
def test_originAnchor(input, df_001):
    assert input(df_001) == [4.5, None]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, "thing3"),
    ],
)
def test_originSpecificVariable(input, df_001):
    assert input(df_001) == [3.0, None]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, "last"),
    ],
)
def test_originTime(input, df_002):
    assert input(df_002) == [7.0, None]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, 5.0),
        lambda df: origin.find(df, [5.0, None]),
    ],
)
def test_originNumber(input, df_001):
    assert input(df_001) == [5.0, None]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, [5.0, 0.0]),
    ],
)
def test_originNumbers(input, df_001):
    assert input(df_001) == [5.0, 0.0]


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, [None, -10.0]),
    ],
)
def test_originNumbers2(input, df_001):
    assert input(df_001) == [None, -10.0]


@pytest.fixture
def df_context1():
    return frame.new(
        [
            ["thing2", 7.0, 5.0, "init"],
            ["thing", 0.0, 5.0, "init"],
            ["thing", 5.0, 5.0, "MOT"],
            ["⚓__001", 4.5, 5.0, "MOT"],
            ["thing3", 3.0, 5.0, "blah"],
        ],
        columns=["variable", "time", "value", "context"],
    )


def test_originContext(df_context1):
    assert origin.find(df_context1, "init") == [7.0, None]


def test_originContextAnchor(df_context1):
    assert origin.find(df_context1, "MOT") == [4.5, None]
