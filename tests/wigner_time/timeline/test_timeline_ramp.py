import pytest
from munch import Munch

from wigner_time import ramp_function, timeline as tl
from wigner_time.internal import dataframe as wt_frame


@pytest.fixture
def dfseq():
    return wt_frame.new(
        [
            [0.0, "lockbox_MOT__V", 0.000000, ""],
            [5.0, "lockbox_MOT__V", 0.000000, ""],
            [5.0, "lockbox_MOT__V", 0.000000, ""],
            [5.2, "lockbox_MOT__V", 0.045177, ""],
            [5.4, "lockbox_MOT__V", 0.500000, ""],
            [5.6, "lockbox_MOT__V", 0.954823, ""],
            [5.8, "lockbox_MOT__V", 1.000000, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "args",
    [
        Munch(lockbox_MOT__V=5, duration=100e-3, context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5], context="init"),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origins=[["last", "variable"], ["variable"]],
        ),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origins=[["last", "variable"], ["variable", "variable"]],
        ),
    ],
)
def test_ramp0(args):
    timeline = tl.create(
        [
            ["lockbox_MOT__V", 0.0, 0.0],
            ["ANCHOR", 0.0, 0.0],
        ],
        context="init",
    )
    tl_ramp = tl.ramp(timeline, **args)
    tl_check = tl.create(
        ANCHOR=[0.0, 0.0, "init"],
        lockbox_MOT__V=[[0.0, 0.0, "init"], [100e-3, 5, "init"]],
    )
    tl_check.loc[tl_check["variable"] == "lockbox_MOT__V", "function"] = (
        ramp_function.tanh
    )

    return wt_frame.assert_equal(tl_ramp, tl_check)


@pytest.mark.parametrize(
    "args",
    [
        Munch(
            lockbox_MOT__V=5,
            duration=0.05,
            origins=[[0.05, "variable"], ["variable"]],
        ),
        Munch(
            lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
            origins=[["ANCHOR", "variable"], ["variable"]],
        ),
        Munch(lockbox_MOT__V=[50e-3, 5], origins=[["last", "variable"], ["variable"]]),
        Munch(
            lockbox_MOT__V=[50e-3, 4.8],
            origins=[["last", "variable"], ["variable", "variable"]],
        ),
    ],
)
def test_ramp1(args):
    timeline = tl.create(lockbox_MOT__V=[50e-3, 0.2], ANCHOR=[0.0, 0.0], context="init")

    tl_ramp = tl.ramp(timeline, **args, context="init")
    tl_check = tl.create(
        ANCHOR=[
            0.0,
            0.0,
        ],
        lockbox_MOT__V=[
            [
                50.0e-3,
                0.2,
            ],
            [
                100e-3,
                5,
            ],
        ],
        context="init",
    )
    tl_check.loc[tl_check["variable"] == "lockbox_MOT__V", "function"] = (
        ramp_function.tanh
    )

    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_combined(dfseq):
    """
    Alternative to `wait`-ing 5s.
    """
    tl_check = tl.create(
        lockbox_MOT__V=[
            [1.0, 1.0],
            [
                6.0,
                1.0,
            ],
            [
                7.0,
                10.0,
            ],
        ],
        context="badger",
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check["time"] > 1.0),
        "function",
    ] = ramp_function.tanh

    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[[5.0, 0.0], [1.0, 10.0]],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)


def test_ramp_expand():
    tl_ramp = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[[5.0, 0.0], [1.0, 10.0]],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
    )


if __name__ == "__main__":

    def expand_ramps(timeline, num__bounds=2, **function_args):
        """
        `num__bounds` refers to the number of points (and so rows) needed to define the ramp function in the first place. Currently, this is implicitly assumed to be two, i.e. that `ramp`s are simply defined by the origin, terminus and expansion function.
        """
        # TODO: Make these variables 'private'
        mask_fs = timeline["function"].notna()
        dff = timeline[mask_fs]

        # Work out where the ramps start
        import numpy as np

        indices_drop = dff.index
        inds = np.asarray(indices_drop)
        diff = np.diff(inds)
        inds__split = np.where(diff > 1)[0] + 1
        inds__start = [a[0] for a in np.split(inds, inds__split)]
        print(inds__start)

        # Mark the beginning and end points (allowing for the number of points per ramp specification to increase in the future)
        dff = dff.reset_index(drop=True)
        dff["ramp_group"] = dff.index // num__bounds

        # Fill out the values
        dfs = []
        columns__keep = dff.columns.drop(["function", "ramp_group"])
        for _, group in dff.groupby("ramp_group"):
            pt_start, pt_end = group[["time", "value"]].values
            dfs.append(
                tl.create(
                    [
                        group["variable"][0],
                        group["function"][0](pt_start, pt_end, **function_args),
                    ],
                ).add(group.iloc[0][columns__keep])
            )

        timeline.drop(index=indices_drop, inplace=True)
        timeline.drop(columns=["function"], inplace=True)

        # Add the values back into the main timeline
        return wt_frame.insert_dataframes(timeline, inds__start, dfs)

    timeline = tl.stack(
        tl.create("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[1.0, 10.0],
            fargs={"time_resolution": 0.2},
            origins=[["lockbox_MOT__V", "lockbox_MOT__V"], ["variable"]],
            is_compact=True,
        ),
    )
    print(expand_ramps(timeline, time_resolution=0.2))
