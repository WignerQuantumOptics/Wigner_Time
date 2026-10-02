import math
from copy import deepcopy

import pytest
import pandas as pd

from wignertime.timeline import build as tl
from wignertime.timeline.internal import anchor as anchor
from wignertime.internal import dataframe as frame

from wignertime.demo import full_experiment as ex

# NOTE: the commented-out `adwin_display` calls below need
# `from wignertime.backend.adwin import display as adwin_display`, and with it the
# optional `display` extra. It is not imported at module scope so that these
# tests remain runnable without that extra.


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
    tl__new = tl.to_timeline(
        tl.stack(
            ex.init(shutter__imaging=0, AOM__imaging=1, trigger__camera=0),
            ex.MOT(),
        )
    )

    tl__original = pd.DataFrame(
        [
            {
                "time": -math.inf,
                "variable": "lockbox__MOT__MHz",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "coil__compensation_X__A",
                "value": 0.25,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "coil__compensation_Y__A",
                "value": 1.5,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "coil__MOT_lower_plus__A",
                "value": 0.1,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "coil__MOT_upper_plus__A",
                "value": -0.1,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__MOT",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__repump",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__OP_aux",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__OP",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__science",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__MOT",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__repump",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__OP1",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__OP2",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__science",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__transverse_pump",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__science__trans",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "trigger__TC__V",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "shutter__imaging",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "AOM__imaging",
                "value": 1.0,
                "context": "ADwin_LowInit",
            },
            {
                "time": -math.inf,
                "variable": "trigger__camera",
                "value": 0.0,
                "context": "ADwin_LowInit",
            },
            {"time": 0.0, "variable": "shutter__MOT", "value": 1.0, "context": "MOT"},
            {
                "time": 0.0,
                "variable": "shutter__repump",
                "value": 1.0,
                "context": "MOT",
            },
            {
                "time": 0.0,
                "variable": "coil__MOT_lower__A",
                "value": -1.0,
                "context": "MOT",
            },
            {
                "time": 0.0,
                "variable": "coil__MOT_upper__A",
                "value": -0.98,
                "context": "MOT",
            },
            {"time": 15.0, "variable": "⚓__001", "value": 0.0, "context": "MOT"},
        ]
    )
    # print(tl__new)
    # print(tl__original)
    # adwin_display.channels(tl__original, do_show=False)
    # adwin_display.quantities(tl__new)

    return frame.assert_equal(tl__new, tl__original)


def test_MOTdetuned():
    tl__new = tl.to_timeline(
        tl.stack(
            ex.init(shutter__imaging=0, AOM__imaging=1, trigger__camera=0),
            ex.MOT(),
            ex.MOT_detuned_growth(),
        )
    ).drop(columns="function")

    tl__original = pd.DataFrame(
        [
            [-math.inf, "lockbox__MOT__MHz", 0.0, "ADwin_LowInit"],
            [-math.inf, "coil__compensation_X__A", 0.25, "ADwin_LowInit"],
            [-math.inf, "coil__compensation_Y__A", 1.5, "ADwin_LowInit"],
            [-math.inf, "coil__MOT_lower_plus__A", 0.1, "ADwin_LowInit"],
            [-math.inf, "coil__MOT_upper_plus__A", -0.1, "ADwin_LowInit"],
            [-math.inf, "AOM__MOT", 1.0, "ADwin_LowInit"],
            [-math.inf, "AOM__repump", 1.0, "ADwin_LowInit"],
            [-math.inf, "AOM__OP_aux", 0.0, "ADwin_LowInit"],
            [-math.inf, "AOM__OP", 1.0, "ADwin_LowInit"],
            [-math.inf, "AOM__science", 1.0, "ADwin_LowInit"],
            [-math.inf, "shutter__MOT", 0.0, "ADwin_LowInit"],
            [-math.inf, "shutter__repump", 0.0, "ADwin_LowInit"],
            [-math.inf, "shutter__OP1", 0.0, "ADwin_LowInit"],
            [-math.inf, "shutter__OP2", 1.0, "ADwin_LowInit"],
            [-math.inf, "shutter__science", 0.0, "ADwin_LowInit"],
            [-math.inf, "shutter__transverse_pump", 0.0, "ADwin_LowInit"],
            [-math.inf, "AOM__science__trans", 1.0, "ADwin_LowInit"],
            [-math.inf, "trigger__TC__V", 0.0, "ADwin_LowInit"],
            [-math.inf, "shutter__imaging", 0.0, "ADwin_LowInit"],
            [-math.inf, "AOM__imaging", 1.0, "ADwin_LowInit"],
            [-math.inf, "trigger__camera", 0.0, "ADwin_LowInit"],
            [0.0, "shutter__MOT", 1.0, "MOT"],
            [0.0, "shutter__repump", 1.0, "MOT"],
            [0.0, "coil__MOT_lower__A", -1.0, "MOT"],
            [0.0, "coil__MOT_upper__A", -0.98, "MOT"],
            [15.0, "⚓__001", 0.0, "MOT"],
            [15.0, "lockbox__MOT__MHz", 0.0, "MOT"],
            [15.01, "lockbox__MOT__MHz", -5.0, "MOT"],
            [15.1, "⚓__002", 0.0, "MOT"],
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


def test_fullDemo():
    actual = tl.to_timeline(
        tl.stack(
            ex.init(),
            ex.MOT(duration=1),
            ex.MOT_detuned_growth(),
            ex.molasses(),
            ex.optical_pumping(),
            ex.magnetic_trapping(),
            ex.pull_coils(50e-3, -4.1, -4.7, -0.6, -0.6),
            ex.finish(),
        )
    ).drop(columns=["function"])
    expected = pd.DataFrame(
        {
            "time": [
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                -math.inf,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                1.0,
                1.01,
                1.1,
                1.1,
                1.1,
                1.1009,
                1.1009,
                1.1,
                1.101,
                1.1027,
                1.105,
                1.105,
                1.105,
                1.105,
                1.10505,
                1.10505,
                1.005,
                1.10505,
                1.10513,
                1.10357,
                1.205,
                1.10335,
                1.205,
                1.10513,
                1.10513,
                1.10513,
                1.10513,
                1.10513,
                1.10513,
                1.10513,
                1.10518,
                1.10518,
                1.10518,
                1.10518,
                1.10518,
                1.10518,
                1.10518,
                1.10518,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.10818,
                1.15818,
                1.15818,
                1.15818,
                1.15818,
                2.10818,
                2.10818,
                2.10818,
                2.10818,
                2.10818,
                2.10818,
                2.10818,
                2.10818,
                2.1181799999999997,
                2.1181799999999997,
                2.1181799999999997,
                2.1181799999999997,
                2.1181799999999997,
                2.1181799999999997,
                2.1181799999999997,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
                math.inf,
            ],
            "variable": [
                "lockbox__MOT__MHz",
                "coil__compensation_X__A",
                "coil__compensation_Y__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "AOM__MOT",
                "AOM__repump",
                "AOM__OP_aux",
                "AOM__OP",
                "AOM__science",
                "shutter__MOT",
                "shutter__repump",
                "shutter__OP1",
                "shutter__OP2",
                "shutter__science",
                "shutter__transverse_pump",
                "AOM__science__trans",
                "trigger__TC__V",
                "shutter__MOT",
                "shutter__repump",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "⚓__001",
                "lockbox__MOT__MHz",
                "lockbox__MOT__MHz",
                "⚓__002",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "lockbox__MOT__MHz",
                "lockbox__MOT__MHz",
                "shutter__MOT",
                "AOM__MOT",
                "⚓__003",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "AOM__OP",
                "AOM__OP",
                "AOM__OP",
                "shutter__OP1",
                "shutter__OP1",
                "shutter__OP2",
                "shutter__OP2",
                "shutter__repump",
                "AOM__repump",
                "⚓__004",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "⚓__005",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "⚓__006",
                "lockbox__MOT__MHz",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__compensation_X__A",
                "coil__compensation_Y__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "lockbox__MOT__MHz",
                "coil__MOT_lower__A",
                "coil__MOT_upper__A",
                "coil__compensation_X__A",
                "coil__compensation_Y__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "lockbox__MOT__MHz",
                "coil__compensation_X__A",
                "coil__compensation_Y__A",
                "coil__MOT_lower_plus__A",
                "coil__MOT_upper_plus__A",
                "AOM__MOT",
                "AOM__repump",
                "AOM__OP_aux",
                "AOM__OP",
                "AOM__science",
                "shutter__MOT",
                "shutter__repump",
                "shutter__OP1",
                "shutter__OP2",
                "shutter__science",
                "shutter__transverse_pump",
                "AOM__science__trans",
                "trigger__TC__V",
            ],
            "value": [
                0.0,
                0.25,
                1.5,
                0.1,
                -0.1,
                1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                1.0,
                -1.0,
                -0.98,
                0.0,
                0.0,
                -5.0,
                0.0,
                -1.0,
                -0.98,
                0.0,
                0.0,
                -5.0,
                -90.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                -0.12,
                0.12,
                0.0,
                1.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                -0.12,
                0.12,
                0.1,
                -0.1,
                -1.8,
                -1.7,
                0.1,
                -0.1,
                -1.8,
                -1.7,
                0.1,
                -0.1,
                -4.8,
                -4.7,
                0.1,
                -0.1,
                0.0,
                -4.8,
                -4.7,
                0.1,
                -0.1,
                -4.1,
                -4.7,
                -0.5,
                -0.7,
                0.0,
                -90.0,
                -4.1,
                -4.7,
                0.25,
                1.5,
                -0.5,
                -0.7,
                0.0,
                -1.0,
                -0.98,
                0.25,
                1.5,
                0.1,
                -0.1,
                0.0,
                0.25,
                1.5,
                0.1,
                -0.1,
                1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                0.0,
                1.0,
                0.0,
                0.0,
                1.0,
                0.0,
            ],
            "context": [
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "ADwin_LowInit",
                "MOT",
                "MOT",
                "MOT",
                "MOT",
                "MOT",
                "MOT",
                "MOT",
                "MOT",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "molasses",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "magnetic_trapping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "optical_pumping",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "finalRamps",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
                "ADwin_Finish",
            ],
        }
    )

    # print("actual")
    # i1 = 50
    # i2 = i1 + 10
    # print(actual[i1:i2])
    # print("expected")
    # print(expected[i1:i2])
    return frame.assert_equal(actual, expected)


def test_trigger_camera_interweaves_into_a_finished_timeline():
    """
    `sec:interweaving`: a placed stage is attached to a named point of a timeline that is
    already complete, `finish` included, without restructuring it. This is how the lab
    images the sample after each preparation stage.
    """
    full = tl.to_timeline(
        tl.stack(
            ex.init(trigger__camera=0),
            ex.MOT(duration=1),
            ex.MOT_detuned_growth(),
            ex.molasses(),
            ex.optical_pumping(),
            ex.magnetic_trapping(),
            ex.finish(trigger__camera=0),
        )
    )
    woven = tl.to_timeline(
        ex.trigger_camera(2e-3, 1e-3, context="imaging", origin="molasses"), onto=full
    )

    time__molasses = full[anchor.mask(full) & (full["context"] == "molasses")][
        "time"
    ].max()
    time__final_ramps = full[anchor.mask(full) & (full["context"] == "finalRamps")][
        "time"
    ].max()
    imaging = woven[woven["context"] == "imaging"]

    # measured from the end of molasses, not from the end of the timeline ...
    assert imaging["variable"].tolist() == ["trigger__camera", "trigger__camera"]
    assert imaging["time"].tolist() == pytest.approx(
        [time__molasses + 2e-3, time__molasses + 3e-3]
    )
    assert imaging["value"].tolist() == [1, 0]
    # ... so it lands inside the run, during magnetic trapping ...
    assert imaging["time"].max() < time__final_ramps
    # ... and nothing that was already there moves.
    frame.assert_equal(woven[woven["context"] != "imaging"], full)
