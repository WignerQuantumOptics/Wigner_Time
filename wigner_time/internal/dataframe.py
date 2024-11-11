"""
This namespace is for abstracting out the implementation of dataframe manipulation.

Particularly relevant for the pandas to polars upgrade.
"""

import pandas as pd

# ^^^ This should change at somepoint!


def join(df1, df2, label="variable"):
    return df1.join(
        df2.set_index(label),
        on=label,
    )
