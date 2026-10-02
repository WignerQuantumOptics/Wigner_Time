import pytest

from wignertime.internal import dataframe as frame
from wignertime.timeline import query as origin


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
    assert origin.previous(input_value) == frame.row(df_previous2, 0)


def test_previous_ties_go_to_the_row_written_last():
    """
    `thing2` and `thing4` share the latest time; the later-written row wins. This is the
    order the removed `sort_by` path did not guarantee (D2, #116): it sorted with NumPy's
    quicksort, which reorders equal keys -- even among five rows, on an AVX2 machine.
    """
    assert origin.previous(df_previous2) == frame.row(df_previous2, 3)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousTime(input_value):
    assert origin.previous(input_value, time__max=3.5) == frame.row(df_previous2, 2)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousContext(input_value):
    assert origin.previous(input_value, variable="blah", column="context") == frame.row(
        df_previous2, 2
    )
