from copy import deepcopy
import pandas as pd

from wigner_time import timeline as tl
from wigner_time import anchor as anchor
from wigner_time.internal import dataframe as frame

import pathlib as pl
import sys


sys.path.append(str(pl.Path.cwd() / "doc"))
import experimentDemo as ex

# import importlib
# importlib.reload(ex)
# from wigner_time.adwin import display as adwin_display


def replace_anchor_symbol(df, symbol__old="Anchor", symbol__new="⚓"):
    timeline = deepcopy(df)
    timeline["variable"] = timeline["variable"].replace(symbol__old, symbol__new)
    return timeline


def label_anchors(df):
    timeline = deepcopy(df)
    timeline.sort_values(by=["time", "variable"])
    indices = list(timeline[timeline["variable"] == "⚓"].index)

    for i, ind in enumerate(indices):
        timeline.loc[ind, "variable"] = "⚓_{:03}".format(i + 1)

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
        ex.init(shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
    )

    tl__original = pd.DataFrame(
        [
            {
                "time": -1e-06,
                "variable": "lockbox_MOT__MHz",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "coil_compensationX__A",
                "value": 0.25,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "coil_compensationY__A",
                "value": 1.5,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "coil_MOTlowerPlus__A",
                "value": 0.1,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "coil_MOTupperPlus__A",
                "value": -0.1,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_MOT",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_repump",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_OP_aux",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_OP",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_science",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_MOT",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_repump",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_OP001",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_OP002",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_science",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_transversePump",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_science__V",
                "value": 5.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "trigger_TC__V",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "shutter_imaging",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "AOM_imaging",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -1e-06,
                "variable": "trigger_camera",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {"time": 0.0, "variable": "shutter_MOT", "value": 1.0, "context": "MOT"},
            {"time": 0.0, "variable": "shutter_repump", "value": 1.0, "context": "MOT"},
            {
                "time": 0.0,
                "variable": "coil_MOTlower__A",
                "value": -1.0,
                "context": "MOT",
            },
            {
                "time": 0.0,
                "variable": "coil_MOTupper__A",
                "value": -0.98,
                "context": "MOT",
            },
            {"time": 15.0, "variable": "⚓_001", "value": 0.0, "context": "MOT"},
        ]
    )
    # print(tl__new)
    # print(tl__original)

    # adwin_display.channels(tl__original, do_show=False)
    # adwin_display.channels(tl__new)

    return frame.assert_equal(tl__new, tl__original)


def test_MOTdetuned():
    tl__new = tl.stack(
        ex.init(shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
        ex.MOT_detunedGrowth(),
    ).drop(columns="function")

    tl__original = pd.DataFrame(
        [
            [-1e-06, "lockbox_MOT__MHz", 0.0, "ADwin_LowInit"],
            [-1e-06, "coil_compensationX__A", 0.25, "ADwin_LowInit"],
            [-1e-06, "coil_compensationY__A", 1.5, "ADwin_LowInit"],
            [-1e-06, "coil_MOTlowerPlus__A", 0.1, "ADwin_LowInit"],
            [-1e-06, "coil_MOTupperPlus__A", -0.1, "ADwin_LowInit"],
            [-1e-06, "AOM_MOT", 1.0, "ADwin_LowInit"],
            [-1e-06, "AOM_repump", 1.0, "ADwin_LowInit"],
            [-1e-06, "AOM_OP_aux", 0.0, "ADwin_LowInit"],
            [-1e-06, "AOM_OP", 1.0, "ADwin_LowInit"],
            [-1e-06, "AOM_science", 1.0, "ADwin_LowInit"],
            [-1e-06, "shutter_MOT", 0.0, "ADwin_LowInit"],
            [-1e-06, "shutter_repump", 0.0, "ADwin_LowInit"],
            [-1e-06, "shutter_OP001", 0.0, "ADwin_LowInit"],
            [-1e-06, "shutter_OP002", 1.0, "ADwin_LowInit"],
            [-1e-06, "shutter_science", 0.0, "ADwin_LowInit"],
            [-1e-06, "shutter_transversePump", 0.0, "ADwin_LowInit"],
            [-1e-06, "AOM_science__V", 5.0, "ADwin_LowInit"],
            [-1e-06, "trigger_TC__V", 0.0, "ADwin_LowInit"],
            [-1e-06, "shutter_imaging", 0.0, "ADwin_LowInit"],
            [-1e-06, "AOM_imaging", 1.0, "ADwin_LowInit"],
            [-1e-06, "trigger_camera", 0.0, "ADwin_LowInit"],
            [0.0, "shutter_MOT", 1.0, "MOT"],
            [0.0, "shutter_repump", 1.0, "MOT"],
            [0.0, "coil_MOTlower__A", -1.0, "MOT"],
            [0.0, "coil_MOTupper__A", -0.98, "MOT"],
            [15.0, "⚓_001", 0.0, "MOT"],
            [15.0, "lockbox_MOT__MHz", 0.0, "MOT"],
            [15.01, "lockbox_MOT__MHz", -5.0, "MOT"],
            [15.1, "⚓_002", 0.0, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return frame.assert_equal(tl__new, tl__original)


def remove_rows_within_time(df, time_threshold):
    """
    Removes all rows (except the first and last) where 'variable' is the same
    and 'time' values differ by less than 'time_threshold'.

    Args:
        df (pd.DataFrame): Input DataFrame with 'time' and 'variable' columns.
        time_threshold (float): Threshold for time differences to define blocks.

    Returns:
        pd.DataFrame: Filtered DataFrame retaining only the first and last rows of each block.
    """
    df = df.sort_values(by=["variable", "time"]).reset_index(drop=True)

    def filter_blocks(group):
        group["block"] = (
            group["time"].diff().fillna(float("inf")) > time_threshold
        ).cumsum()

        return group.groupby("block", group_keys=False).apply(lambda x: x.iloc[[0, -1]])

    result = df.groupby("variable", group_keys=False).apply(filter_blocks)

    return result.drop(columns=["block"])


def remove_anchors(timeline):
    df = timeline[~anchor.mask(timeline)]
    return df
