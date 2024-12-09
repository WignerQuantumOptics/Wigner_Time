from copy import deepcopy
import pandas as pd

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame

import pathlib as pl
import sys

sys.path.append(str(pl.Path.home() / "projects/Wigner_Time/doc"))
import experiment as ex


def replace_anchor_symbol(df, symbol__old="Anchor", symbol__new="⚓"):
    timeline = deepcopy(df)
    timeline["variable"] = timeline["variable"].replace(symbol__old, symbol__new)
    return timeline


def label_anchors(df):
    timeline = deepcopy(df)
    timeline.sort_values(by=["time", "variable"])
    indices = list(timeline[timeline["variable"] == "⚓"].index)

    for i, ind in enumerate(indices):
        timeline.loc[ind, "variable"] = "⚓__{:03}".format(i)

    return timeline


def update_anchor(df):
    return label_anchors(replace_anchor_symbol(timeline_old))


timeline_old = pd.read_parquet("~/WT_dat/MOT.parquet")
tl__original = update_anchor(timeline_old)


tl.stack(
    ex.init(t=-2, shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
    ex.MOT(),
    # ex.MOT_detunedGrowth(),
    # ex.molasses(),
    # ex.OP(),
    # ex.magneticTrapping(),
    # ex.finish(wait=2,MOT_ON=True,
    #           shutter_imaging=0,AOM_imaging=1,trigger_camera=0
    #           ),
)
