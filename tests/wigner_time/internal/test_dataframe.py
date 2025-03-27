import pytest

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
        ["thing4", 7.0, 5, "init"],
        ["thing2", 7.0, 5.0, "init"],
        ["thing", 0.0, 5, "init"],
        ["thing3", 3.0, 5, "blah"],
    ],
    columns=["variable", "time", "value", "context"],
)


@pytest.mark.parametrize("input_value", [df_simple1, df_simple2])
def test_row_from_max_column(input_value):
    row = ["thing2", 7.0, 5.0, "init"]
    assert list(frame.row_from_max_column(input_value)) == row


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


@pytest.mark.parametrize("input", [df_simple1])
def test_insert_dataframes(input):
    frame.assert_equal(
        frame.insert_dataframes(input, [1], [df_simple1]),
        frame.new(
            [
                ["thing2", 7.0, 5.0, "init"],
                ["thing2", 7.0, 5.0, "init"],
                ["thing", 0.0, 5.0, "init"],
                ["thing3", 3.0, 5.0, "blah"],
                ["thing", 0.0, 5.0, "init"],
                ["thing3", 3.0, 5.0, "blah"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


@pytest.mark.parametrize("input", [df_simple1])
def test_subframe(input):
    return frame.assert_equal(
        frame.subframe(input, "variable", ["thing2"]),
        frame.new(
            [
                ["thing2", 7.0, 5.0, "init"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


@pytest.mark.parametrize("input", [df_simple1])
def test_subframe002(input):
    calc = frame.subframe(input, "variable", [5], func=len)
    new = frame.new(
        [
            ["thing", 0.0, 5.0, "init"],
        ],
        columns=["variable", "time", "value", "context"],
    )
    # print(calc)
    # print(new)
    return frame.assert_equal(
        calc,
        new,
    )
