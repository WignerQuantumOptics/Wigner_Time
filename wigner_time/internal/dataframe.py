"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

# In the medium term, this should have a polars counterpart namespace so that we can switch between the two easily.

from copy import deepcopy
import pandas as pd


CLASS = pd.DataFrame


def new(data, columns: list):
    return pd.DataFrame(data, columns=columns)


def cast(df, col_type: dict):
    """
    Coerces column types according to the given schema (`col_type`).

    First, restricts the schema to match what is relevant to the dataframe.
    """

    return df.astype({k: col_type[k] for k in set(df.columns) if k in col_type.keys()})


def new_schema(data, schema: dict):
    """
    Makes another dataframe using `new`, but where the schema parameter provides some convenience.
    """
    return cast(
        new(
            data,
            list(schema.keys()),
        ),
        schema,
    )


def join(df1, df2, label="variable"):
    return df1.join(
        df2.set_index(label),
        on=label,
    )


def concat(dfs, ignore_index=True):
    return pd.concat(dfs, ignore_index=ignore_index)


def isnull(o):
    """
    Detect missing values for an array-like object.
    """
    return pd.isnull(o)


def row_from_max_column(df, column="time"):
    """
    Finds the maximum value of the column and returns the corresponding row.
    """
    return df.loc[df[column].idxmax()]


def drop_duplicates(df, subset=None, keep="last"):
    return df.drop_duplicates(subset=subset, keep=keep, ignore_index=True).copy()


def duplicated(df, subset=["time", "variable"], keep="last"):
    return df.duplicated(subset=subset, keep=keep)


def replace_column__filtered(
    df,
    dict__replacement,
    column__change="time",
    column__filter="context",
    is_in_place=False,
):
    """
    Replaces all values of `column__change` with the corresponding dictionary values, for which the rows match the keys of column__filter.

    e.g. Replaces the `time` values with the numbers in {"ADwin_LowInit": -2, "ADwin_Init": -1, "ADwin_Finish": 2**31 - 1} according to which `context`s the rows are specified for.
    """
    if not is_in_place:
        dff = deepcopy(df)
    else:
        dff = df

    dff[column__change] = (
        dff[column__filter]
        .map(dict__replacement)
        .fillna(dff[column__change])
        .astype(df["time"].dtype)
    )

    return dff


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)
