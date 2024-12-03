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


# TODO: FIx this merge
@pytest.mark.parametrize("input", [df_duplicate1])
def test_increment_selected_rows(input):
    return frame.assert_equal(
        frame.increment_selected_rows(input, thing=1.0),
        frame.new(
            [
                ["thing2", 7.0, 5, "init"],
                ["thing2", 7.0, 5, "init"],
                ["thing", 1.0, 5, "init"],
                ["thing", 1.0, 7.0, "different"],
                ["thing3", 3.0, 5, "blah"],
                ["thing4", 7.0, 5, "init"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


def test_replace_column__filtered():
    df = frame.new_schema(
        [
            ["thing2", 7.0, 5, "init"],
            ["thing", 0.0, 7.0, "different"],
            ["thing3", 3.0, 5, "blah"],
            ["thing4", 7.0, 5, "init"],
        ],
        {
            "variable": str,
            "time": float,
            "value": float,
            "context": str,
        },
    )
    return frame.assert_equal(
        frame.replace_column__filtered(df, {"init": -1, "different": -500}),
        frame.new_schema(
            [
                ["thing2", -1, 5, "init"],
                ["thing", -500, 7.0, "different"],
                ["thing3", 3.0, 5, "blah"],
                ["thing4", -1.0, 5, "init"],
            ],
            {
                "variable": str,
                "time": float,
                "value": float,
                "context": str,
            },
        ),
    )


if __name__ == "__main__":
    import importlib

    importlib.reload(frame)

    print(frame.row_from_max_column(df_simple2))
