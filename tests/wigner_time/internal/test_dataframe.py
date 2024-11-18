import pytest
import pandas as pd

# TODO: This should be abstracted

from wigner_time.internal import dataframe as frame


df_simple1 = frame.new(
    [
        ["thing2", 7.0, 5.0, "init"],
        ["thing", 0.0, 5.0, "init"],
        ["thing3", 3.0, 5.0, "blah"],
    ],
    columns=["variable", "time", "value", "context"],
)
df_simple2 = frame.new(
    [
        ["thing2", 7.0, 5, "init"],
        ["thing", 0.0, 5, "init"],
        ["thing3", 3.0, 5, "blah"],
        ["thing4", 7.0, 5, "init"],
    ],
    columns=["variable", "time", "value", "context"],
)


@pytest.mark.parametrize("input_value", [df_simple1, df_simple2])
def test_row_from_max_column(input_value):
    row = df_simple2.loc[0]

    return pd.testing.assert_series_equal(frame.row_from_max_column(input_value), row)


df_duplicate1 = frame.new(
    [
        ["thing2", 7.0, 5, "init"],
        ["thing2", 7.0, 5, "init"],
        ["thing", 0.0, 5, "init"],
        ["thing", 0.0, 7.0, "different"],
        ["thing3", 3.0, 5, "blah"],
        ["thing4", 7.0, 5, "init"],
    ],
    columns=["variable", "time", "value", "context"],
)


@pytest.mark.parametrize("input_value", [df_duplicate1])
def test_drop_duplicates(input_value):
    return frame.assert_equal(
        frame.drop_duplicates(input_value),
        frame.new(
            [
                ["thing2", 7.0, 5, "init"],
                ["thing", 0.0, 5, "init"],
                ["thing", 0.0, 7.0, "different"],
                ["thing3", 3.0, 5, "blah"],
                ["thing4", 7.0, 5, "init"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


@pytest.mark.parametrize("input_value", [df_duplicate1])
def test_drop_duplicatesSubset(input_value):
    return frame.assert_equal(
        frame.drop_duplicates(input_value, subset=["variable", "time"]),
        frame.new(
            [
                ["thing2", 7.0, 5, "init"],
                ["thing", 0.0, 7.0, "different"],
                ["thing3", 3.0, 5, "blah"],
                ["thing4", 7.0, 5, "init"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


if __name__ == "__main__":
    import importlib

    importlib.reload(frame)

    print(frame.row_from_max_column(df_simple2))
