from copy import deepcopy
import pandas as pd

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame

import pathlib as pl
import sys

import importlib

sys.path.append(str(pl.Path.cwd() / "doc"))
import experiment as ex

importlib.reload(ex)
from wigner_time.adwin import display as adwin_display


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

    # The data came from an old version
    # timeline_old = pd.read_parquet("~/WT_dat/MOT.parquet")
    # tl__original = update_anchor(timeline_old)
    # tl__original.loc[tl__original["variable"] == "⚓__002", "context"] = "MOT"

    tl__original = frame.new(
        data=[
            [-2.0, "lockbox_MOT__MHz", 0.00, "ADwin_LowInit"],
            [-2.0, "coil_compensationX__A", 0.25, "ADwin_LowInit"],
            [-2.0, "coil_compensationY__A", 1.50, "ADwin_LowInit"],
            [-2.0, "coil_MOTlowerPlus__A", 0.10, "ADwin_LowInit"],
            [-2.0, "coil_MOTupperPlus__A", -0.10, "ADwin_LowInit"],
            [-2.0, "AOM_MOT", 1.00, "ADwin_LowInit"],
            [-2.0, "AOM_repump", 1.00, "ADwin_LowInit"],
            [-2.0, "AOM_OP_aux", 0.00, "ADwin_LowInit"],
            [-2.0, "AOM_OP", 1.00, "ADwin_LowInit"],
            [-2.0, "shutter_MOT", 0.00, "ADwin_LowInit"],
            [-2.0, "shutter_repump", 0.00, "ADwin_LowInit"],
            [-2.0, "shutter_OP001", 0.00, "ADwin_LowInit"],
            [-2.0, "shutter_OP002", 1.00, "ADwin_LowInit"],
            [-2.0, "shutter_imaging", 0.00, "ADwin_LowInit"],
            [-2.0, "AOM_imaging", 1.00, "ADwin_LowInit"],
            [-2.0, "trigger_camera", 0.00, "ADwin_LowInit"],
            [0.0, "⚓__001", 0.00, "InitialAnchor"],
            [0.0, "shutter_MOT", 1.00, "MOT"],
            [0.0, "shutter_repump", 1.00, "MOT"],
            [0.0, "coil_MOTlower__A", -1.00, "MOT"],
            [0.0, "coil_MOTupper__A", -0.98, "MOT"],
            [15.0, "⚓__002", 0.00, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return frame.assert_equal(tl__new, tl__original)


def test_MOTdetuned():
    tl__new = tl.stack(
        ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
        ex.MOT_detunedGrowth(),
    ).drop(columns="function")

    # timeline_old = pd.read_parquet("~/WT_dat/MOT_detuned.parquet")
    # tl__original = filter_ramp(update_anchor(timeline_old), "lockbox_MOT__MHz", "MOT")
    # tl__original.loc[tl__original["variable"] == "⚓__002", "context"] = "MOT"

    tl__original = frame.new(
        [
            [-2.000000, "lockbox_MOT__MHz", 0.00, "ADwin_LowInit"],
            [-2.000000, "coil_compensationX__A", 0.25, "ADwin_LowInit"],
            [-2.000000, "coil_compensationY__A", 1.50, "ADwin_LowInit"],
            [-2.000000, "coil_MOTlowerPlus__A", 0.10, "ADwin_LowInit"],
            [-2.000000, "coil_MOTupperPlus__A", -0.10, "ADwin_LowInit"],
            [-2.000000, "AOM_MOT", 1.00, "ADwin_LowInit"],
            [-2.000000, "AOM_repump", 1.00, "ADwin_LowInit"],
            [-2.000000, "AOM_OP_aux", 0.00, "ADwin_LowInit"],
            [-2.000000, "AOM_OP", 1.00, "ADwin_LowInit"],
            [-2.000000, "shutter_MOT", 0.00, "ADwin_LowInit"],
            [-2.000000, "shutter_repump", 0.00, "ADwin_LowInit"],
            [-2.000000, "shutter_OP001", 0.00, "ADwin_LowInit"],
            [-2.000000, "shutter_OP002", 1.00, "ADwin_LowInit"],
            [-2.000000, "shutter_imaging", 0.00, "ADwin_LowInit"],
            [-2.000000, "AOM_imaging", 1.00, "ADwin_LowInit"],
            [-2.000000, "trigger_camera", 0.00, "ADwin_LowInit"],
            [0.000000, "⚓__001", 0.00, "InitialAnchor"],
            [0.000000, "shutter_MOT", 1.00, "MOT"],
            [0.000000, "shutter_repump", 1.00, "MOT"],
            [0.000000, "coil_MOTlower__A", -1.00, "MOT"],
            [0.000000, "coil_MOTupper__A", -0.98, "MOT"],
            [15.000000, "⚓__002", 0.00, "MOT"],
            [15.000000, "lockbox_MOT__MHz", 0.00, "MOT"],
            [15.009999, "lockbox_MOT__MHz", -5.00, "MOT"],
            [15.100000, "⚓__003", 0.00, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )
    return frame.assert_equal(tl__new, tl__original)


def testInitToFinish():
    # TODO: Problems:
    # shutter_op1
    # shutter_op2
    # AOM_op
    tl__new = tl.stack(
        ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
        ex.MOT_detunedGrowth(),
        ex.molasses(),
        ex.OP(),
        # ex.magneticTrapping(),
        # ex.finish(
        #     wait=2, MOT_ON=True, shutter_imaging=0, AOM_imaging=1, trigger_camera=0
        # ),
    )
    adwin_display.channels(tl__new)

    tl__old = pd.read_parquet("resources/timeline__init-to-finish.parquet")

    # adwin_display.channels(tl__old)

    # print(tl__new)
    assert False
