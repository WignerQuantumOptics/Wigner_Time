"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

# In the medium term, this should have a polars counterpart namespace so that we can switch between the two easily.

from copy import deepcopy
import pandas as pd


CLASS = pd.DataFrame


def new(data, columns):
    return pd.DataFrame(data, columns=columns)


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


def cast(df, col_type: dict):
    return df.astype(col_type)


def row_from_max_column(df, column="time"):
    """
    Finds the maximum value of the column and returns the corresponding row.
    """
    return df.loc[df[column].idxmax()]


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


def insert_dataframes(df, indices, dfs):
    """
    Inserts multiple DataFrames (`dfs`) into an existing DataFrame (`df`) at specified `indices`.
    """
    # TODO: Currently doesn't have tests
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


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)


def assert_series_equal(s1, s2):
    return pd.testing.assert_series_equal(s1, s2)
