"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

from collections.abc import Callable

# In the medium term, this should have a polars counterpart namespace so that we can switch between the two easily.
from copy import deepcopy

import pandas as pd
from numpy import identity

CLASS = pd.DataFrame


def new(data, columns: list | None = None):
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


def subframe(df: CLASS, column: str, values: list, func: Callable | None = None):
    """
    Returns a filtered df, where func(`column`) has values in `values`.
    """
    if func:
        return df[df[column].map(func).isin(values)].reset_index(drop=True)

    return df[df[column].isin(values)].reset_index(drop=True)


def row_from_max_column(df, column="time"):
    """
    Finds the maximum value of the column and returns the corresponding row.
    """
    # The reversal is necessary to ensure that the highest index maximum is returned. This avoids subtle bugs in choosing the previous context etc.
    return df.loc[df[column][::-1].idxmax()]


def increment_selected_rows(
    df, column__increment="time", column__match="variable", in_place=True, **incs
):
    """
    Keywords are variable=<increment> pairs. If none are provided then the original df is returned.
    """
    if incs is not None:
        dff = df if in_place else deepcopy(df)
        for k, v in incs.items():
            dff.loc[dff[column__match] == k, column__increment] += v
        return dff
    else:
        return df


def drop_duplicates(df, subset=None, keep="last"):
    return df.drop_duplicates(subset=subset, keep=keep, ignore_index=True).copy()


def insert_dataframes(df: CLASS, indices: list[int], dfs: list[CLASS]) -> CLASS:
    """
    Inserts multiple DataFrames (`dfs`) into an existing DataFrame (`df`) at specified `indices`.
    """
    # Sort the insertions by index to ensure correct order of insertion
    if len(indices) != len(dfs):
        raise ValueError("`indices` and `dfs` are different lengths.")
    insertions = zip(indices, dfs)
    insertions = sorted(insertions, key=lambda x: x[0])

    # Track the cumulative offset caused by insertions
    offset = 0
    result_parts = []
    current_start = 0

    for index, new_df in insertions:
        # Adjust index for previous insertions
        adjusted_index = index + offset

        # Add the portion of the original DataFrame up to the insertion point
        result_parts.append(df.iloc[current_start:adjusted_index])

        # Add the new DataFrame
        result_parts.append(new_df)

        # Update offset and the starting point for the next slice
        offset += len(new_df)
        current_start = adjusted_index

    # Add the remainder of the original DataFrame
    result_parts.append(df.iloc[current_start:])

    # Concatenate all parts into a single DataFrame
    return pd.concat(result_parts, ignore_index=True).reset_index(drop=True)


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
        .astype(df[column__change].dtype)
    )

    return dff


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)


def assert_series_equal(s1, s2):
    return pd.testing.assert_series_equal(s1, s2)
