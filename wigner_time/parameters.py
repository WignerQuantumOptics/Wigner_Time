# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

import pandas as pd
from munch import Munch


def from_dict(dct=None, labels=["parameter", "value"], extras={}, **kwargs):
    """
    TODO: Add to a dictionary manipulating API rather than here?

    Now allows direct instantiation using kwargs. The downside of this is that the parameters have to come after the other arguments
    """
    items = kwargs if dct==None else dct
    rows = []
    for k, v in items.items():
        rows.append([k, v] + list(extras.values()))

    return pd.DataFrame(rows, columns=labels + list(extras.keys()))

def vals(df, labels=['parameter', 'value']):
    """
    Convenience for accessing parameter values by name.
    """
    return Munch(df[labels].values)

def update(parameters,dct,context):
    """
    Updating the parameters DataFrame with a dictionary containing modified or new parameters.
    """
    return pd.concat([
        parameters,
        from_dict(
            dct,
            extras={"context":"{}".format(context)}
            ),
        ],ignore_index=True).drop_duplicates()

if __name__ == "__main__":
    print(from_dict({"test": 1, "test2": 20}, extras=Munch(context="molasses")))

