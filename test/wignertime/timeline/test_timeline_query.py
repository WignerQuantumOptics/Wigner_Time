import pytest

from wignertime import timeline as tl
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


@pytest.mark.parametrize("input_value", [df_previous1, df_previous1])
def test_previous(input_value):
    row = df_previous2.loc[0]

    return frame.assert_series_equal(tl.previous(input_value), row)


@pytest.mark.parametrize("input_value", [df_previous1])
def test_previousSort(input_value):
    row = df_previous2.loc[0]
    return frame.assert_series_equal(tl.previous(input_value, sort_by="time"), row)


@pytest.mark.parametrize("input_value", [df_previous2])
def test_previousSort2(input_value):
    row = df_previous2.loc[3]
    return frame.assert_series_equal(tl.previous(input_value, sort_by="time"), row)


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


def test_previous_sorting_does_not_touch_the_caller_or_warn():
    """
    B3/#110. `tl__filtered` is a boolean-mask slice, and `sort_values(inplace=True)` on
    one is undefined: pandas 2 answers correctly but raises `SettingWithCopyWarning`, and
    pandas 3 makes copy-on-write unconditional (#88). Rebinding instead is both correct
    and quiet.

    The existing `sort_by` tests do not catch it, because getting the right answer was
    never the problem.
    """
    import warnings

    timeline = tl.create(
        a__A=[[3.0, 30.0], [1.0, 10.0], [2.0, 20.0]],
        b__A=[[0.5, 5.0]],
        context="s",
    )
    before = timeline.copy()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        row = tl.previous(timeline, variable="a__A", sort_by="time")

    assert row["time"] == pytest.approx(3.0)
    assert row["value"] == pytest.approx(30.0)
    assert [w.category.__name__ for w in caught] == []
    frame.assert_equal(timeline, before)
