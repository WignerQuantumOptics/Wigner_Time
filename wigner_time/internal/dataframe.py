"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

import pandas as pd

# ^^^ This should change at somepoint!


def new(data, columns):
    return pd.DataFrame(data, columns=columns)


def join(df1, df2, label="variable"):
    return df1.join(
        df2.set_index(label),
        on=label,
    )


def concat(dfs, ignore_index=True):
    return pd.concat(dfs, ignore_index=ignore_index)


def assert_equal(df1, df2):
    return pd.testing.assert_frame_equal(df1, df2)
