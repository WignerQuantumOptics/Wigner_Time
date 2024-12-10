from copy import deepcopy
import pandas as pd

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame

import pathlib as pl
import sys

import importlib

sys.path.append(str(pl.Path.home() / "projects/Wigner_Time/doc"))
import experiment as ex

importlib.reload(ex)


def replace_anchor_symbol(df, symbol__old="Anchor", symbol__new="⚓"):
    timeline = deepcopy(df)
    timeline["variable"] = timeline["variable"].replace(symbol__old, symbol__new)
    return timeline


def label_anchors(df):
    timeline = deepcopy(df)
    timeline.sort_values(by=["time", "variable"])
    indices = list(timeline[timeline["variable"] == "⚓"].index)

    for i, ind in enumerate(indices):
        timeline.loc[ind, "variable"] = "⚓__{:03}".format(i + 1)

    return timeline


def update_anchor(df):
    return label_anchors(replace_anchor_symbol(df))


def filter_ramp(df, variable, context):
    filtered_rows = df[(df["variable"] == variable) & (df["context"] == context)]

    min_row = filtered_rows.loc[filtered_rows["value"].idxmin()]
    max_row = filtered_rows.loc[filtered_rows["value"].idxmax()]

    keep_indices = [min_row.name, max_row.name]
    return df.drop(
        df[
            (df["variable"] == variable)
            & (df["context"] == context)
            & (~df.index.isin(keep_indices))
        ].index
    ).reset_index(drop=True, inplace=False)


def filter_ramps(df, var_cons, index=0):
    """
    Recursively applies `filter_ramp` to the DataFrame using variable-context pairs.
    """
    if not var_cons:
        return df

    variable, context = var_cons[0]
    remaining_pairs = var_cons[1:]
    filtered_df = filter_ramp(df, variable, context)

    return filter_ramps(filtered_df, remaining_pairs)


def test_MOT():

    tl__new = tl.stack(
        ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
    )

    timeline_old = pd.read_parquet("~/WT_dat/MOT.parquet")
    tl__original = update_anchor(timeline_old)

    return frame.assert_equal(tl__new, tl__original)


def test_MOTdetuned():
    tl__new = tl.stack(
        ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
        ex.MOT_detunedGrowth(),
    ).drop(columns="function")

    timeline_old = pd.read_parquet("~/WT_dat/MOT_detuned.parquet")
    tl__original = filter_ramp(update_anchor(timeline_old), "lockbox_MOT__MHz", "MOT")

    return frame.assert_equal(tl__new, tl__original)

    # def test_multipleRamps():
    #     # TODO: WIP
    #     tl__new = tl.stack(
    #         ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
    #         ex.MOT(),
    #         # ex.MOT_detunedGrowth(),
    #         # ex.molasses(),
    #     )  # .drop(columns="function")
    # print(tl__new)
    # return frame.assert_equal(tl__new, tl__original)
