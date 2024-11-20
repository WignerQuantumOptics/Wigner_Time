import pytest

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame


df_previous1 = frame.new(
    [
        ["thing2", 7.0, 5.0, "init"],
        ["thing", 0.0, 5.0, "init"],
        ["thing3", 3.0, 5.0, "blah"],
    ],
    columns=["variable", "time", "value", "context"],
)
df_previous2 = frame.new(
    [
        ["thing2", 7.0, 5, "init"],
        ["thing", 0.0, 5, "init"],
        ["thing3", 3.0, 5, "blah"],
        ["thing4", 7.0, 5, "init"],
    ],
    columns=["variable", "time", "value", "context"],
)


@pytest.mark.parametrize("input_value", [df_previous1, df_previous1])
def test_previous(input_value):
    row = df_previous2.loc[0]

    return pd.testing.assert_series_equal(tl.previous(input_value), row)


@pytest.mark.parametrize("input_value", [df_previous1])
def test_previousSort(input_value):
    row = df_previous2.loc[0]
    return pd.testing.assert_series_equal(tl.previous(input_value, sort_by="time"), row)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousSort2(input_value):
    row = df_previous2.loc[3]
    return pd.testing.assert_series_equal(tl.previous(input_value, sort_by="time"), row)
