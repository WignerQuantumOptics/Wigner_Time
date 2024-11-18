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
            ["ANCHOR", 4.5, 5.0, "MOT"],
            ["thing3", 3.0, 5.0, "blah"],
        ],
        columns=["variable", "time", "value", "context"],
    )


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df),
        lambda df: origin.find(df, "anchor"),
    ],
)
def test_originAnchor(input, df_001):
    return pd.testing.assert_series_equal(
        input(df_001),
        df_001.iloc[2],
    )


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, "thing3"),
    ],
)
def test_originSpecificVariable(input, df_001):
    return pd.testing.assert_series_equal(
        input(df_001),
        df_001.iloc[3],
    )


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, "time"),
    ],
)
def test_originTime(input, df_001):
    return pd.testing.assert_series_equal(
        input(df_001),
        df_001.iloc[0],
    )


@pytest.mark.parametrize(
    "input",
    [
        lambda df: origin.find(df, 5.0),
    ],
)
def test_originNumber(input, df_001):
    assert input(df_001) == 5.0
