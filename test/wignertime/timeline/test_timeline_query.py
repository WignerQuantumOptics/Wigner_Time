import pytest

from wignertime.internal import dataframe as frame
from wignertime.internal import origin


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


@pytest.mark.parametrize("input_value", [df_previous1])
def test_previous(input_value):
    row = df_previous2.loc[0]

    return frame.assert_series_equal(origin.previous(input_value), row)


def test_previous_ties_go_to_the_row_written_last():
    """
    `thing2` and `thing4` share the latest time; the later-written row wins. This is the
    order the removed `sort_by` path did not guarantee (D2, #116): it sorted with NumPy's
    quicksort, which reorders equal keys -- even among five rows, on an AVX2 machine.
    """
    row = df_previous2.loc[3]
    return frame.assert_series_equal(origin.previous(df_previous2), row)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousTime(input_value):
    row = df_previous2.loc[2]
    return frame.assert_series_equal(origin.previous(input_value, time__max=3.5), row)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousContext(input_value):
    row = df_previous2.loc[2]
    return frame.assert_series_equal(
        origin.previous(input_value, variable="blah", column="context"), row
    )
