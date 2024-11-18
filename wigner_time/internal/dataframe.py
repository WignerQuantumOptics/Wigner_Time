"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

# In the medium term, this should have a polars counterpart namespace so that we can switch between the two easily.

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


def row_from_max_column(df, column="time"):
    """
    Finds the maximum value of the column and returns the corresponding row.
    """
    return df.loc[df[column].idxmax()]


def drop_duplicates(df, subset=None, keep="last"):
    return df.drop_duplicates(subset=subset, keep=keep, ignore_index=True).copy()


# ============================================================
# TESTS
# ============================================================
def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)
