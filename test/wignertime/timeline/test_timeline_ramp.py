import pytest
from munch import Munch
import numpy as np

from wignertime import ramp_function, timeline as tl

# NOTE: the commented-out `display` call below needs
# `from wignertime.adwin import display`, and with it the optional `display`
# extra. It is not imported at module scope so that these tests remain runnable
# without that extra.
from wignertime.internal import dataframe as wt_frame

import pathlib as pl
import sys

from wignertime.demo import full_experiment as ex


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


@pytest.fixture
def tl_anchor():
    return tl._populate_timeline(
        [
            ["lockbox_MOT__V", 0.0],
            ["⚓_001", 0.0],
        ],
        t=0.0,
        context="init",
    )


@pytest.mark.parametrize(
    "args",
    [
        Munch(lockbox_MOT__V=5, duration=100e-3, context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5], context="init"),
        Munch(lockbox_MOT__V=[100e-3, 5, "init"]),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origin=["last", "variable"],
            origin2=["variable"],
        ),
        Munch(
            lockbox_MOT__V=[100e-3, 5],
            context="init",
            origin=["last", "variable"],
            origin2=["variable", "variable"],
        ),
    ],
)
def test_ramp0(args):
    timeline = tl._populate_timeline(
        [
            ["lockbox_MOT__V", 0.0, 0.0],
            ["⚓_001", 0.0, 0.0],
        ],
        context="init",
    )
    tl_ramp = tl.ramp(timeline, **args)
    tl_check = tl._populate_timeline(
        [
            ["lockbox_MOT__V", [0.0, 0.0, "init"]],
            ["⚓_001", [0.0, 0.0, "init"]],
            ["lockbox_MOT__V", [[0.0, 0.0, "init"], [100e-3, 5, "init"]]],
        ],
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


@pytest.mark.parametrize(
    "args",
    [
        Munch(
            lockbox_MOT__V=5,
            duration=0.05,
            origin=[0.05, "variable"],
            origin2=["variable"],
        ),
        Munch(
            lockbox_MOT__V=[50e-3, 5], origin=["last", "variable"], origin2=["variable"]
        ),
        Munch(
            lockbox_MOT__V=[50e-3, 4.8],
            origin=["last", "variable"],
            origin2=["variable", "variable"],
        ),
    ],
)
def test_ramp1(args):
    timeline = tl._populate_timeline(
        [["lockbox_MOT__V", [50e-3, 0.2]], ["⚓_001", [0.0, 0.0]]], context="init"
    )

    tl_ramp = tl.ramp(timeline, **args, context="init")
    tl_check = tl._populate_timeline(
        [
            ["lockbox_MOT__V", [50e-3, 0.2]],
            [
                "⚓_001",
                [
                    0.0,
                    0.0,
                ],
            ],
            [
                "lockbox_MOT__V",
                [
                    [
                        50.0e-3,
                        0.2,
                    ],
                    [
                        100e-3,
                        5,
                    ],
                ],
            ],
        ],
        context="init",
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox_MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_start_stated_explicitly_is_protected_by_default(tl_anchor):
    """
    A start value written in the 2-D form is taken as written (A8/#106).
    `lockbox_MOT__V` sits at 0.2, and the ramp still starts at the 0.0 that was written,
    with a time-only `origin="anchor"` as with none at all. Contrast
    `test_ramp_start_stated_explicitly_with_explicit_value_origin`, where the caller
    writes a value origin too.
    """
    timeline = tl._populate_timeline(
        [["lockbox_MOT__V", [50e-3, 0.2]], ["⚓_001", [0.0, 0.0]]], context="init"
    )
    result = tl.ramp(
        timeline,
        lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
        origin="anchor",
        context="init",
    )
    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.05, 0.0],
        [0.10, 5.0],
    ]


def test_ramp_start_stated_explicitly_with_explicit_value_origin(tl_anchor):
    """
    A stated start value is offset by a value origin the caller *writes*: what keeps a
    stated start as written is only the default for the value slot, and a default never
    overrides a slot the caller filled (see `internal.origin.auto`). `lockbox_MOT__V`
    sits at 0.2, so the written start of 0.0 comes out as 0.2.
    """
    timeline = tl._populate_timeline(
        [["lockbox_MOT__V", [50e-3, 0.2]], ["⚓_001", [0.0, 0.0]]], context="init"
    )
    result = tl.ramp(
        timeline,
        lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
        origin=["anchor", "variable"],
        context="init",
    )
    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.05, 0.2],
        [0.10, 5.0],
    ]


def test_ramp_start_stated_explicitly_can_be_kept_literal(tl_anchor):
    """
    `origin=[0.0, 0.0]` is no shift in either slot, so a stated 2-D start comes back
    exactly as written even when the caller wants no origin at all.
    """
    timeline = tl._populate_timeline(
        [["lockbox_MOT__V", [50e-3, 0.2]], ["⚓_001", [0.0, 0.0]]], context="init"
    )
    result = tl.ramp(
        timeline,
        lockbox_MOT__V=[[0.05, 0.0], [0.05, 5]],
        origin=[0.0, 0.0],
        context="init",
    )
    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.05, 0.0],
        [0.10, 5.0],
    ]


def test_ramp_inherits_context_by_default(tl_anchor):
    """
    `context` defaults to `wt_config.INFER`: a `ramp` that does not state its own
    context lands in `tl_anchor`'s "init".
    """
    result = tl.ramp(tl_anchor, lockbox_MOT__V=5, duration=100e-3)
    assert sorted(set(result["context"])) == ["init"]


def test_ramp_context_none_inherits_too(tl_anchor):
    """
    `context=None` means the same as the default, so a stage that takes `context=None`
    and passes it on to `ramp` inherits as if it had passed nothing (#142).
    """
    wt_frame.assert_equal(
        tl.ramp(tl_anchor, lockbox_MOT__V=5, duration=100e-3, context=None),
        tl.ramp(tl_anchor, lockbox_MOT__V=5, duration=100e-3),
    )


def test_ramp_refuses_an_empty_context(tl_anchor):
    """
    #156. `context=""` used to switch inheritance off and leave the ramp's rows without a
    context. Every row has one, stated or inherited, so there is nothing to switch off.
    """
    with pytest.raises(ValueError, match="is not a context"):
        tl.ramp(tl_anchor, lockbox_MOT__V=5, duration=100e-3, context="")


def test_ramp_combined():
    """
    Hold at the variable's current value for 5 s, then ramp to 10 over 1 s.

    This was written in 2025-03 (`2927057`) as a translation of the `wait` mechanism
    that the origin machinery replaced, using the 2-D form with a start value of 0.0 as
    an *offset* -- which worked only because the value origin was added on top of it
    (A8). The 2-D form was never needed: `t` places the start point, and the default
    origin supplies its value. All four spellings were measured equal on 2026-09-18.
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
        tl._populate_timeline("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(lockbox_MOT__V=10.0, t=5.0, duration=1.0),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)


@pytest.mark.parametrize(
    "args",
    [[[0.05, 0.0], [0.05, 5]]],
)
def test_ramp_start(tl_anchor, args):
    tl_ramp = tl.ramp(tl_anchor, lockbox_MOT__V=args, duration=100e-3)

    tl_check = tl._populate_timeline(
        [
            ["lockbox_MOT__V", [0.0, 0.0, "init"]],
            ["⚓_001", [0.0, 0.0, "init"]],
            [
                "lockbox_MOT__V",
                [[0.05, 0.0, "init"], [0.1, 5, "init"]],
            ],
        ],
    )
    tl_check["function"] = [np.nan, np.nan, ramp_function.tanh, ramp_function.tanh]
    return wt_frame.assert_equal(tl_ramp, tl_check)


# === Heterogeneous input is probably a bad idea
# @pytest.mark.parametrize(
#     "args",
#     [[[0.05], [0.05, 5]], [0.05, [0.05, 5]]],
# )
# def test_ramp_start2(tl_anchor, args):
#     tl_ramp = tl.ramp(tl_anchor, lockbox_MOT__V=args, duration=0.0)

#     tl_check = tl._populate_timeline(
#         [
#             ["lockbox_MOT__V", [0.0, 0.0, "init"]],
#             ["⚓_001", [0.0, 0.0, "init"]],
#             [
#                 "lockbox_MOT__V",
#                 [[0.00, 0.05, "init"], [0.1, 5, "init"]],
#             ],
#         ],
#     )
#     tl_check["function"] = [np.nan, np.nan, ramp_function.tanh, ramp_function.tanh]
#     return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_expand():
    tl_ramp = tl.stack(
        tl._populate_timeline("lockbox_MOT__V", [[1.0, 1.0]], context="badger"),
        tl.ramp(
            lockbox_MOT__V=[1.0, 10.0],
            origin=["lockbox_MOT__V", "lockbox_MOT__V"],
            origin2=["variable"],
        ),
        lambda tline: tl.expand(tline, time_resolution=0.2),
    )
    tl_check = wt_frame.new(
        [
            [1.0, "lockbox_MOT__V", 1.0, "badger"],
            [1.0, "lockbox_MOT__V", 1.000000, "badger"],
            [1.2, "lockbox_MOT__V", 1.218198, "badger"],
            [1.4, "lockbox_MOT__V", 3.071266, "badger"],
            [1.6, "lockbox_MOT__V", 7.928734, "badger"],
            [1.8, "lockbox_MOT__V", 9.781802, "badger"],
            [2.0, "lockbox_MOT__V", 10.000000, "badger"],
        ],
        columns=["time", "variable", "value", "context"],
    )
    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_random_ramp():
    tl_ramp = tl.stack(
        tl._populate_timeline(
            ["device_pump", [0.0, 0.0, "ADwin_Init"]],
            ["lockbox_MOT__V", [1.0, 00.0, "ADwin_Init"]],
            ["lockbox_MOT__V", [2.0, 10.0, "blah"]],
            ["⚓_001", [2.5, 0.0, "blah"]],
            ["device_pump", [3.0, 1.0, "something_important"]],
            ["⚓_002", [3.5, 0.0, "something_important"]],
            ["lockbox_MOT__V", [6.0, 5.0, "something_important"]],
            ["device_pump", [7.0, 0.0, "ADwin_Finish"]],
            ["lockbox_MOT__V", [7.0, 0.0, "ADwin_Finish"]],
        ),
        tl.ramp(lockbox_MOT__V=11.0, duration=1.0, origin=["blah", "variable"]),
        context="blah",
    )

    return wt_frame.assert_equal(
        tl_ramp[["variable", "time", "value", "context"]],
        wt_frame.new(
            [
                ["device_pump", 0.0, 0.0, "ADwin_Init"],
                ["lockbox_MOT__V", 1.0, 0.0, "ADwin_Init"],
                ["lockbox_MOT__V", 2.0, 10.0, "blah"],
                ["⚓_001", 2.5, 0.0, "blah"],
                ["device_pump", 3.0, 1.0, "something_important"],
                ["⚓_002", 3.5, 0.0, "something_important"],
                ["lockbox_MOT__V", 6.0, 5.0, "something_important"],
                ["device_pump", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox_MOT__V", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox_MOT__V", 2.5, 10.0, "blah"],
                ["lockbox_MOT__V", 3.5, 11.0, "blah"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


def test_rampReal():
    timeline = tl.stack(
        ex.init(),
        ex.MOT(duration=1),
        ex.MOT__detuned_growth(),
        tl.ramp(t=1, duration=0.1, lockbox_MOT__MHz=-2),
        tl.ramp(t=0.5, duration=0.1, lockbox_MOT__MHz=-1),
    )
    timeline__simplified = timeline[timeline["time"] >= 0.0][
        ["variable", "time", "value"]
    ].reset_index(drop=True)

    expected = wt_frame.new(
        [
            ["shutter_MOT", 0.00, 1.00],
            ["shutter_repump", 0.00, 1.00],
            ["coil_MOTlower__A", 0.00, -1.00],
            ["coil_MOTupper__A", 0.00, -0.98],
            ["⚓_001", 1.00, 0.0],
            ["lockbox_MOT__MHz", 1.00, 0.00],
            ["lockbox_MOT__MHz", 1.01, -5.00],
            ["⚓_002", 1.10, 0.0],
            ["lockbox_MOT__MHz", 2.10, -5.00],
            ["lockbox_MOT__MHz", 2.20, -2.00],
            ["lockbox_MOT__MHz", 1.60, -5.00],
            ["lockbox_MOT__MHz", 1.70, -1.00],
        ],
        columns=["variable", "time", "value"],
    )

    # print(timeline__simplified)
    # print(expected)
    # display.channels(timeline, variables=["lockbox_MOT__MHz"])
    return wt_frame.assert_equal(
        timeline__simplified,
        expected,
    )


def test_rampReal2():
    timeline = tl.stack(
        ex.init(),
        ex.MOT(duration=1),
        ex.MOT__detuned_growth(),
        tl.ramp(t=1, duration=0.1, lockbox_MOT__MHz=-2),
        tl.ramp(t=0.5, duration=0.1, lockbox_MOT__MHz=-1),
        tl.ramp(t=0.75, duration=0.1, lockbox_MOT__MHz=-5),
    )
    timeline__simplified = timeline[timeline["context"] == "MOT"][
        ["variable", "time", "value", "context"]
    ].reset_index(drop=True)

    # print(
    #     timeline[timeline["context"] == "MOT"][["variable", "time", "value", "context"]]
    # )

    expected = wt_frame.new(
        [
            ["shutter_MOT", 0.0, 1.0, "MOT"],
            ["shutter_repump", 0.0, 1.0, "MOT"],
            ["coil_MOTlower__A", 0.0, -1.0, "MOT"],
            ["coil_MOTupper__A", 0.0, -0.98, "MOT"],
            ["⚓_001", 1.0, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 1.0, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 1.01, -5.0, "MOT"],
            ["⚓_002", 1.1, 0.0, "MOT"],
            ["lockbox_MOT__MHz", 2.1, -5.0, "MOT"],
            ["lockbox_MOT__MHz", 2.2, -2.0, "MOT"],
            ["lockbox_MOT__MHz", 1.6, -5.0, "MOT"],
            ["lockbox_MOT__MHz", 1.7000000000000002, -1.0, "MOT"],
            ["lockbox_MOT__MHz", 1.85, -1.0, "MOT"],
            ["lockbox_MOT__MHz", 1.9500000000000002, -5.0, "MOT"],
        ],
        columns=["variable", "time", "value", "context"],
    )

    return wt_frame.assert_equal(timeline__simplified, expected)


# Check that no-ops don't cause failures
def test_rampDoesNotRaise1(tl_anchor):
    tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=10.0, duration=1.0))


def test_ramp_of_zero_duration_raises(tl_anchor):
    """
    A3, settled 2026-09-18. Both boundaries would occupy one instant, so there is no
    ramp to expand, and a `duration` that comes out as zero is almost always a slip in
    the caller's arithmetic. Until then this returned the timeline untouched, so the
    command simply was not there.
    """
    with pytest.raises(ValueError, match="must end after it begins"):
        tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=10.0, duration=0.0))


def test_ramp_of_negative_duration_raises(tl_anchor):
    """
    The same error with a sign, and it was the worse of the two: `expand` sorts each
    ramp's boundaries by time, so a backwards ramp had its endpoints silently *swapped*.
    Measured on `bb55695`, with `c__A` sitting at 4.0:

        ramp(c__A=9.0, duration=-1.0)  ->  ramp 9.0 -> 4.0, one second in the past

    i.e. the variable finished at its old value rather than at the target, and the
    transition landed on top of whatever preceded it. Nothing said so.
    """
    with pytest.raises(ValueError, match="must end after it begins"):
        tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=10.0, duration=-1.0))


def test_a_flat_ramp_is_kept(tl_anchor):
    """
    The other half of A3: `lockbox_MOT__V` already sits at 0.0, so this ramp changes no
    value -- but it *occupies a second*, and discarding it shortened the timeline and
    pulled everything after it forward, silently. It is kept, and
    `adwin.validate.drop_repeats` removes the resulting value redundancy before the
    hardware.
    """
    result = tl.stack(tl_anchor, tl.ramp(lockbox_MOT__V=0.0, duration=1.0))

    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.0, 0.0],
        [1.0, 0.0],
    ]


def test_boundary_frames_are_compared_variable_by_variable():
    """
    B1/#108. `new1` and `new2` do not hold their variables in the same order once the
    1-D and 2-D input forms are mixed in one call: `new1` takes the explicitly started
    variables first, `new2` the inferred ones. The degenerate-row mask subtracted them
    positionally, so it compared one variable's boundary against another's.

    Here nothing is degenerate -- `X__A` runs 7.0 -> 5.0 and `Y__A` 5.0 -> 7.0, at
    different times -- but positionally each start matches the *other* variable's end in
    value, so every row was flagged, and A3's early return then discarded the entire
    ramp without a word. Measured on `5d5a0cd`: 0 rows added instead of 4.
    """
    base = tl.create(X__A=1.0, Y__A=5.0, t=0.0, context="s")
    result = tl.ramp(
        base, X__A=[[1.0, 7.0], [2.0, 5.0]], Y__A=7.0, duration=3.0, origin=0.0
    )

    assert len(result) - len(base) == 4
    assert set(result[result["function"].notna()]["variable"]) == {"X__A", "Y__A"}


def test_ramp_leaves_the_timeline_it_was_given_alone():
    """
    B4/#111, and the invariant behind it: `ramp` derives its start points from the same
    frame the end points come from, overwriting their time and value. Were that a slice
    rather than a copy, the write would reach the end points and zero the values the
    ramp is aiming at.

    Also the package-wide rule -- no in-place modification, every core function returns a
    new timeline -- which nothing else pins for `ramp`.
    """
    import warnings

    base = tl.stack(
        tl.create(c__A=2.0, d__A=3.0, t=0.0, context="s"),
        tl.anchor(1.0, context="s"),
    )
    before = base.copy()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = tl.ramp(base, c__A=9.0, d__A=[[0.0, 1.0], [0.5, 7.0]], duration=0.5)

    assert [w.category.__name__ for w in caught] == []
    wt_frame.assert_equal(base, before)

    ends = result[result["function"].notna()].groupby("variable")["value"].last()
    assert ends["c__A"] == pytest.approx(9.0)
    assert ends["d__A"] == pytest.approx(7.0)


# --- how many points a ramp is made of (B6/#113, A13) -------------------------


def test_a_ramp_function_declares_how_many_points_it_takes():
    """
    The number belongs to the interpolating function, not to the caller expanding it.
    An undeclared one is taken to want two, which keeps a hand-written
    `lambda origin, terminus, time_resolution: ...` working without ceremony.
    """
    assert ramp_function.points(ramp_function.tanh) == 2
    assert ramp_function.points(ramp_function.linear) == 2
    assert ramp_function.points(lambda origin, terminus, time_resolution: None) == 2

    @ramp_function.with_points(3)
    def spline(origin, middle, terminus, time_resolution=1e-6):
        raise NotImplementedError

    assert ramp_function.points(spline) == 3


def test_a_third_point_is_refused_rather_than_discarded(tl_anchor):
    """
    A13. `ramp` read the first two points and dropped the rest in silence, while its own
    docstring promised an error -- the defect A10 fixed in `create`, in the one function
    that sweep did not reach.
    """
    with pytest.raises(ValueError, match="needs 2 point"):
        tl.ramp(tl_anchor, lockbox_MOT__V=[[0.0, 1.0], [0.5, 5.0], [1.0, 9.0]])


def test_expand_no_longer_takes_num__bounds(tl_anchor):
    """
    Removed rather than renamed. Left in place it would have been swallowed by
    `**function_args` and filtered out against the ramp function's signature, so a caller
    still passing it would have been ignored without a word.
    """
    timeline = tl.ramp(tl_anchor, lockbox_MOT__V=5.0, duration=1.0)
    with pytest.raises(TypeError, match="no longer takes `num__bounds`"):
        tl.expand(timeline, num__bounds=2, time_resolution=0.1)


def test_expand_names_the_variable_whose_ramp_rows_do_not_pair(tl_anchor):
    """
    B6. The old global stride meant one variable with an odd number of rows misaligned
    the pairing of every variable after it, and surfaced as a bare
    `ValueError: not enough values to unpack (expected 2, got 1)`.
    """
    timeline = tl.ramp(tl_anchor, lockbox_MOT__V=5.0, duration=1.0)
    timeline.loc[len(timeline)] = [
        2.0,
        "lockbox_MOT__V",
        3.0,
        "init",
        ramp_function.tanh,
    ]

    with pytest.raises(ValueError, match="lockbox_MOT__V has 3 ramp row"):
        tl.expand(timeline, time_resolution=0.1)


def test_two_ramps_of_one_variable_still_expand(tl_anchor):
    """Grouping per variable must still chunk that variable's rows, not merge them."""
    timeline = tl.stack(
        tl_anchor,
        tl.ramp(lockbox_MOT__V=5.0, duration=1.0),
        tl.ramp(lockbox_MOT__V=0.0, duration=1.0, t=2.0),
    )
    expanded = tl.expand(timeline, time_resolution=0.25)
    values = expanded[expanded["variable"] == "lockbox_MOT__V"]["value"].tolist()

    assert values[-1] == pytest.approx(0.0)
    assert max(values) == pytest.approx(5.0)


# --- #157: a variable is in at most one ramp at a time -------------------------


@pytest.fixture
def coil_at_zero():
    return tl.stack(tl.create(coil_X__A=0.0, t=0.0, context="s"), tl.anchor(5.0))


def test_a_ramp_starting_inside_another_of_its_variable_raises(coil_at_zero):
    """
    The case #157 measured: the second ramp took the first one's *start* value, 0 A,
    where the coil stood at 5 A, and `expand` then paired the four boundaries in time
    order, so the coil held at 0 A until 6 s and jumped to 10 A.
    """
    first = tl.ramp(timeline=coil_at_zero, coil_X__A=10.0, duration=1.0)
    with pytest.raises(ValueError, match="at most one ramp") as e:
        tl.ramp(timeline=first, coil_X__A=20.0, duration=1.0, t=0.5)
    assert "coil_X__A: this ramp, 5.5..6.5 s, overlaps its ramp over 5.0..6.0 s" in str(
        e.value
    )
    assert "within rounding" not in str(e.value)


@pytest.mark.parametrize(
    "t, duration",
    [
        (-0.5, 1.0),  # begins before, ends inside
        (0.25, 0.5),  # entirely inside
        (-0.5, 2.0),  # encloses it
    ],
)
def test_every_kind_of_overlap_raises(coil_at_zero, t, duration):
    first = tl.ramp(timeline=coil_at_zero, coil_X__A=10.0, duration=1.0)
    with pytest.raises(ValueError, match="at most one ramp"):
        tl.ramp(
            timeline=first, coil_X__A=20.0, duration=duration, t=t, origin=[5.0, None]
        )


def test_a_ramp_may_start_as_another_ends(coil_at_zero):
    """The ordinary sequence, as `magnetic_trapping`'s two `pull_coils` do it."""
    first = tl.ramp(timeline=coil_at_zero, coil_X__A=10.0, duration=1.0)
    second = tl.ramp(timeline=first, coil_X__A=20.0, duration=1.0, t=1.0)
    values = tl.expand(second, time_resolution=0.25)
    assert values[values["variable"] == "coil_X__A"]["value"].iloc[-1] == 20.0


def test_meeting_by_rounding_is_refused_and_said_to_be_rounding():
    """
    The two times are reached by different sums: 0.1 + 0.2 is 0.30000000000000004, so a
    ramp placed at 0.3 in absolute time starts 4e-17 s before the first one ends. Its
    start value is looked up at 0.3, which the first one's end row does not yet precede,
    so a tolerance here would let it start from the wrong value. On this branch the
    lookup is still widened by `config.TIME_RESOLUTION`, which happens to cover it;
    `issue#94` removes that widening.
    """
    base = tl.stack(tl.create(coil_X__A=0.0, t=0.0, context="s"), tl.anchor(0.1))
    first = tl.ramp(timeline=base, coil_X__A=10.0, duration=0.2)
    assert first["time"].max() > 0.3
    with pytest.raises(ValueError, match="within rounding"):
        tl.ramp(timeline=first, coil_X__A=20.0, duration=0.2, t=0.3, origin=[0.0, None])


def test_placed_from_the_others_end_the_same_ramp_is_kept():
    base = tl.stack(tl.create(coil_X__A=0.0, t=0.0, context="s"), tl.anchor(0.1))
    first = tl.ramp(timeline=base, coil_X__A=10.0, duration=0.2)
    second = tl.ramp(timeline=first, coil_X__A=20.0, duration=0.2, origin="last")
    rows = second[second["variable"] == "coil_X__A"]
    assert rows["value"].iloc[-2] == 10.0  # it starts where the first one ended


def test_ramps_of_different_variables_may_overlap():
    base = tl.stack(
        tl.create(coil_X__A=0.0, coil_Y__A=0.0, t=0.0, context="s"), tl.anchor(5.0)
    )
    first = tl.ramp(timeline=base, coil_X__A=10.0, duration=1.0)
    both = tl.ramp(timeline=first, coil_Y__A=10.0, duration=1.0, t=0.5)
    assert set(both["variable"]) >= {"coil_X__A", "coil_Y__A"}
