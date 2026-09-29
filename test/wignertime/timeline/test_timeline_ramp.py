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
            [0.0, "lockbox__MOT__V", 0.000000, ""],
            [5.0, "lockbox__MOT__V", 0.000000, ""],
            [5.0, "lockbox__MOT__V", 0.000000, ""],
            [5.2, "lockbox__MOT__V", 0.045177, ""],
            [5.4, "lockbox__MOT__V", 0.500000, ""],
            [5.6, "lockbox__MOT__V", 0.954823, ""],
            [5.8, "lockbox__MOT__V", 1.000000, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def tl_anchor():
    return tl._populate_timeline(
        [
            ["lockbox__MOT__V", 0.0],
            ["⚓__001", 0.0],
        ],
        time=0.0,
        context="init",
    )


@pytest.mark.parametrize(
    "args",
    [
        Munch(lockbox__MOT__V=5, duration=100e-3, context="init"),
        Munch(lockbox__MOT__V=[100e-3, 5], context="init"),
        Munch(lockbox__MOT__V=[100e-3, 5, "init"]),
        Munch(
            lockbox__MOT__V=[100e-3, 5],
            context="init",
            origin=[tl.LAST, tl.VARIABLE],
            origin2=[tl.VARIABLE],
        ),
        Munch(
            lockbox__MOT__V=[100e-3, 5],
            context="init",
            origin=[tl.LAST, tl.VARIABLE],
            origin2=[tl.VARIABLE, tl.VARIABLE],
        ),
    ],
)
def test_ramp0(args):
    timeline = tl._populate_timeline(
        [
            ["lockbox__MOT__V", 0.0, 0.0],
            ["⚓__001", 0.0, 0.0],
        ],
        context="init",
    )
    tl_ramp = tl.to_timeline(tl.ramp(**args), onto=timeline)
    tl_check = tl._populate_timeline(
        [
            ["lockbox__MOT__V", [0.0, 0.0, "init"]],
            ["⚓__001", [0.0, 0.0, "init"]],
            ["lockbox__MOT__V", [[0.0, 0.0, "init"], [100e-3, 5, "init"]]],
        ],
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox__MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


@pytest.mark.parametrize(
    "args",
    [
        Munch(
            lockbox__MOT__V=5,
            duration=0.05,
            origin=[0.05, tl.VARIABLE],
            origin2=[tl.VARIABLE],
        ),
        Munch(
            lockbox__MOT__V=[50e-3, 5],
            origin=[tl.LAST, tl.VARIABLE],
            origin2=[tl.VARIABLE],
        ),
        Munch(
            lockbox__MOT__V=[50e-3, 4.8],
            origin=[tl.LAST, tl.VARIABLE],
            origin2=[tl.VARIABLE, tl.VARIABLE],
        ),
    ],
)
def test_ramp1(args):
    timeline = tl._populate_timeline(
        [["lockbox__MOT__V", [50e-3, 0.2]], ["⚓__001", [0.0, 0.0]]], context="init"
    )

    tl_ramp = tl.to_timeline(tl.ramp(**args, context="init"), onto=timeline)
    tl_check = tl._populate_timeline(
        [
            ["lockbox__MOT__V", [50e-3, 0.2]],
            [
                "⚓__001",
                [
                    0.0,
                    0.0,
                ],
            ],
            [
                "lockbox__MOT__V",
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
        (tl_check["variable"] == "lockbox__MOT__V") & (tl_check.index != 0),
        "function",
    ] = ramp_function.tanh

    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_a_written_start_is_refused_and_a_jump_is_an_update():
    """
    #142, 2026-09-29: a ramp always starts where its variable is. The 2-D form stated a
    start -- taken as written by default, offset by a value origin the caller wrote, or
    kept literal with `origin=[0.0, 0.0]` -- and a start that differs from the current
    value is a step hidden inside the ramp. The step is now an `update`, where it shows.
    """
    timeline = tl._populate_timeline(
        [["lockbox__MOT__V", [50e-3, 0.2]], ["⚓__001", [0.0, 0.0]]], context="init"
    )
    with pytest.raises(ValueError, match="its start is not written: lockbox__MOT__V"):
        tl.to_timeline(
            tl.ramp(lockbox__MOT__V=[[0.05, 0.0], [0.05, 5]], context="init"),
            onto=timeline,
        )
    for origin in (["anchor", 0.0], [0.0, 0.0], ["anchor", "lockbox__MOT__V"]):
        with pytest.raises(ValueError, match="value slot of its `origin`"):
            tl.ramp(lockbox__MOT__V=5, time=0.05, duration=0.05, origin=origin)

    jump_then_ramp = tl.stack(
        tl.update(lockbox__MOT__V=0.0, time=0.05),
        tl.ramp(lockbox__MOT__V=5, time=0.05, duration=0.05),
        context="init",
    )
    result = tl.to_timeline(jump_then_ramp, onto=timeline)
    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.05, 0.0],
        [0.10, 5.0],
    ]


def test_ramp_inherits_context_by_default(tl_anchor):
    """
    `context` defaults to `wt_config.INFER`: a `ramp` that does not state its own
    context lands in `tl_anchor`'s "init".
    """
    result = tl.to_timeline(tl.ramp(lockbox__MOT__V=5, duration=100e-3), onto=tl_anchor)
    assert sorted(set(result["context"])) == ["init"]


def test_ramp_context_none_inherits_too(tl_anchor):
    """
    `context=None` means the same as the default, so a stage that takes `context=None`
    and passes it on to `ramp` inherits as if it had passed nothing (#142).
    """
    wt_frame.assert_equal(
        tl.to_timeline(
            tl.ramp(lockbox__MOT__V=5, duration=100e-3, context=None), onto=tl_anchor
        ),
        tl.to_timeline(tl.ramp(lockbox__MOT__V=5, duration=100e-3), onto=tl_anchor),
    )


def test_ramp_refuses_an_empty_context(tl_anchor):
    """
    #156. `context=""` used to switch inheritance off and leave the ramp's rows without a
    context. Every row has one, stated or inherited, so there is nothing to switch off.
    """
    with pytest.raises(ValueError, match="is not a context"):
        tl.to_timeline(
            tl.ramp(lockbox__MOT__V=5, duration=100e-3, context=""), onto=tl_anchor
        )


def test_ramp_combined():
    """
    Hold at the variable's current value for 5 s, then ramp to 10 over 1 s.

    This was written in 2025-03 (`2927057`) as a translation of the `wait` mechanism
    that the origin machinery replaced, using the 2-D form with a start value of 0.0 as
    an *offset* -- which worked only because the value origin was added on top of it
    (A8). The 2-D form was never needed: `t` places the start point, and the default
    origin supplies its value. All four spellings were measured equal on 2026-09-18.
    """
    tl_check = tl.to_timeline(
        tl.update(
            lockbox__MOT__V=[
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
    )
    tl_check.loc[
        (tl_check["variable"] == "lockbox__MOT__V") & (tl_check["time"] > 1.0),
        "function",
    ] = ramp_function.tanh

    tl_ramp = tl.to_timeline(
        tl.stack(
            tl.ramp(lockbox__MOT__V=10.0, time=5.0, duration=1.0),
        ),
        onto=tl._populate_timeline("lockbox__MOT__V", [[1.0, 1.0]], context="badger"),
    )
    return wt_frame.assert_equal(tl_check, tl_ramp)


def test_ramp_start(tl_anchor):
    """
    Where a ramp starts is `t`; what it starts from is where the variable is. What the
    2-D form `[[0.05, 0.0], [0.05, 5]]` said from a variable at 0.0 is said this way.
    """
    tl_ramp = tl.to_timeline(
        tl.ramp(lockbox__MOT__V=[0.05, 5], time=0.05, duration=100e-3), onto=tl_anchor
    )

    tl_check = tl._populate_timeline(
        [
            ["lockbox__MOT__V", [0.0, 0.0, "init"]],
            ["⚓__001", [0.0, 0.0, "init"]],
            [
                "lockbox__MOT__V",
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
#     tl_ramp = tl.to_timeline(tl.ramp(lockbox__MOT__V=args, duration=0.0), onto=tl_anchor)

#     tl_check = tl._populate_timeline(
#         [
#             ["lockbox__MOT__V", [0.0, 0.0, "init"]],
#             ["⚓__001", [0.0, 0.0, "init"]],
#             [
#                 "lockbox__MOT__V",
#                 [[0.00, 0.05, "init"], [0.1, 5, "init"]],
#             ],
#         ],
#     )
#     tl_check["function"] = [np.nan, np.nan, ramp_function.tanh, ramp_function.tanh]
#     return wt_frame.assert_equal(tl_ramp, tl_check)


def test_ramp_expand():
    tl_ramp = tl.to_timeline(
        tl.stack(
            tl.ramp(
                lockbox__MOT__V=[1.0, 10.0],
                origin="lockbox__MOT__V",
                origin2=[tl.VARIABLE],
            ),
            lambda tline: tl.expand(tline, time_resolution=0.2),
        ),
        onto=tl._populate_timeline("lockbox__MOT__V", [[1.0, 1.0]], context="badger"),
    )
    tl_check = wt_frame.new(
        [
            [1.0, "lockbox__MOT__V", 1.0, "badger"],
            [1.0, "lockbox__MOT__V", 1.000000, "badger"],
            [1.2, "lockbox__MOT__V", 1.218198, "badger"],
            [1.4, "lockbox__MOT__V", 3.071266, "badger"],
            [1.6, "lockbox__MOT__V", 7.928734, "badger"],
            [1.8, "lockbox__MOT__V", 9.781802, "badger"],
            [2.0, "lockbox__MOT__V", 10.000000, "badger"],
        ],
        columns=["time", "variable", "value", "context"],
    )
    return wt_frame.assert_equal(tl_ramp, tl_check)


def test_random_ramp():
    tl_ramp = tl.to_timeline(
        tl.stack(
            tl.ramp(lockbox__MOT__V=11.0, duration=1.0, origin=["blah", tl.VARIABLE]),
            context="blah",
        ),
        onto=tl._populate_timeline(
            ["device_pump", [0.0, 0.0, "ADwin_Init"]],
            ["lockbox__MOT__V", [1.0, 00.0, "ADwin_Init"]],
            ["lockbox__MOT__V", [2.0, 10.0, "blah"]],
            ["⚓__001", [2.5, 0.0, "blah"]],
            ["device_pump", [3.0, 1.0, "something_important"]],
            ["⚓__002", [3.5, 0.0, "something_important"]],
            ["lockbox__MOT__V", [6.0, 5.0, "something_important"]],
            ["device_pump", [7.0, 0.0, "ADwin_Finish"]],
            ["lockbox__MOT__V", [7.0, 0.0, "ADwin_Finish"]],
        ),
    )

    return wt_frame.assert_equal(
        tl_ramp[["variable", "time", "value", "context"]],
        wt_frame.new(
            [
                ["device_pump", 0.0, 0.0, "ADwin_Init"],
                ["lockbox__MOT__V", 1.0, 0.0, "ADwin_Init"],
                ["lockbox__MOT__V", 2.0, 10.0, "blah"],
                ["⚓__001", 2.5, 0.0, "blah"],
                ["device_pump", 3.0, 1.0, "something_important"],
                ["⚓__002", 3.5, 0.0, "something_important"],
                ["lockbox__MOT__V", 6.0, 5.0, "something_important"],
                ["device_pump", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox__MOT__V", 7.0, 0.0, "ADwin_Finish"],
                ["lockbox__MOT__V", 2.5, 10.0, "blah"],
                ["lockbox__MOT__V", 3.5, 11.0, "blah"],
            ],
            columns=["variable", "time", "value", "context"],
        ),
    )


def test_rampReal():
    timeline = tl.to_timeline(
        tl.stack(
            ex.init(),
            ex.MOT(duration=1),
            ex.MOT_detuned_growth(),
            tl.ramp(time=1, duration=0.1, lockbox__MOT__MHz=-2),
            tl.ramp(time=0.5, duration=0.1, lockbox__MOT__MHz=-1),
        )
    )
    timeline__simplified = timeline[timeline["time"] >= 0.0][
        ["variable", "time", "value"]
    ].reset_index(drop=True)

    expected = wt_frame.new(
        [
            ["shutter__MOT", 0.00, 1.00],
            ["shutter__repump", 0.00, 1.00],
            ["coil__MOT_lower__A", 0.00, -1.00],
            ["coil__MOT_upper__A", 0.00, -0.98],
            ["⚓__001", 1.00, 0.0],
            ["lockbox__MOT__MHz", 1.00, 0.00],
            ["lockbox__MOT__MHz", 1.01, -5.00],
            ["⚓__002", 1.10, 0.0],
            ["lockbox__MOT__MHz", 2.10, -5.00],
            ["lockbox__MOT__MHz", 2.20, -2.00],
            ["lockbox__MOT__MHz", 1.60, -5.00],
            ["lockbox__MOT__MHz", 1.70, -1.00],
        ],
        columns=["variable", "time", "value"],
    )

    # print(timeline__simplified)
    # print(expected)
    # display.channels(timeline, variables=["lockbox__MOT__MHz"])
    return wt_frame.assert_equal(
        timeline__simplified,
        expected,
    )


def test_rampReal2():
    timeline = tl.to_timeline(
        tl.stack(
            ex.init(),
            ex.MOT(duration=1),
            ex.MOT_detuned_growth(),
            tl.ramp(time=1, duration=0.1, lockbox__MOT__MHz=-2),
            tl.ramp(time=0.5, duration=0.1, lockbox__MOT__MHz=-1),
            tl.ramp(time=0.75, duration=0.1, lockbox__MOT__MHz=-5),
        )
    )
    timeline__simplified = timeline[timeline["context"] == "MOT"][
        ["variable", "time", "value", "context"]
    ].reset_index(drop=True)

    # print(
    #     timeline[timeline["context"] == "MOT"][["variable", "time", "value", "context"]]
    # )

    expected = wt_frame.new(
        [
            ["shutter__MOT", 0.0, 1.0, "MOT"],
            ["shutter__repump", 0.0, 1.0, "MOT"],
            ["coil__MOT_lower__A", 0.0, -1.0, "MOT"],
            ["coil__MOT_upper__A", 0.0, -0.98, "MOT"],
            ["⚓__001", 1.0, 0.0, "MOT"],
            ["lockbox__MOT__MHz", 1.0, 0.0, "MOT"],
            ["lockbox__MOT__MHz", 1.01, -5.0, "MOT"],
            ["⚓__002", 1.1, 0.0, "MOT"],
            ["lockbox__MOT__MHz", 2.1, -5.0, "MOT"],
            ["lockbox__MOT__MHz", 2.2, -2.0, "MOT"],
            ["lockbox__MOT__MHz", 1.6, -5.0, "MOT"],
            ["lockbox__MOT__MHz", 1.7000000000000002, -1.0, "MOT"],
            ["lockbox__MOT__MHz", 1.85, -1.0, "MOT"],
            ["lockbox__MOT__MHz", 1.9500000000000002, -5.0, "MOT"],
        ],
        columns=["variable", "time", "value", "context"],
    )

    return wt_frame.assert_equal(timeline__simplified, expected)


# Check that no-ops don't cause failures
def test_rampDoesNotRaise1(tl_anchor):
    tl.to_timeline(
        tl.stack(tl.ramp(lockbox__MOT__V=10.0, duration=1.0)), onto=tl_anchor
    )


def test_ramp_of_zero_duration_raises(tl_anchor):
    """
    A3, settled 2026-09-18. Both boundaries would occupy one instant, so there is no
    ramp to expand, and a `duration` that comes out as zero is almost always a slip in
    the caller's arithmetic. Until then this returned the timeline untouched, so the
    command simply was not there.
    """
    with pytest.raises(ValueError, match="must end after it begins"):
        tl.to_timeline(
            tl.stack(tl.ramp(lockbox__MOT__V=10.0, duration=0.0)), onto=tl_anchor
        )


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
        tl.to_timeline(
            tl.stack(tl.ramp(lockbox__MOT__V=10.0, duration=-1.0)), onto=tl_anchor
        )


def test_a_flat_ramp_is_kept(tl_anchor):
    """
    The other half of A3: `lockbox__MOT__V` already sits at 0.0, so this ramp changes no
    value -- but it *occupies a second*, and discarding it shortened the timeline and
    pulled everything after it forward, silently. It is kept, and
    `adwin.validate.drop_repeats` removes the resulting value redundancy before the
    hardware.
    """
    result = tl.to_timeline(
        tl.stack(tl.ramp(lockbox__MOT__V=0.0, duration=1.0)), onto=tl_anchor
    )

    assert result[result["function"].notna()][["time", "value"]].values.tolist() == [
        [0.0, 0.0],
        [1.0, 0.0],
    ]


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

    base = tl.to_timeline(
        tl.stack(
            tl.anchor(1.0, context="s"),
        ),
        onto=tl.to_timeline(tl.update(c__A=2.0, d__A=3.0, time=0.0, context="s")),
    )
    before = base.copy()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = tl.to_timeline(
            tl.ramp(c__A=9.0, d__A=[0.5, 7.0], duration=0.5), onto=base
        )

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


def test_a_list_of_points_is_refused_rather_than_discarded(tl_anchor):
    """
    A13. `ramp` read the first two points and dropped the rest in silence. Since #142 a
    ramp's start is never written, so a list of points is refused as a whole.
    """
    with pytest.raises(ValueError, match="its start is not written"):
        tl.to_timeline(
            tl.ramp(lockbox__MOT__V=[[0.0, 1.0], [0.5, 5.0], [1.0, 9.0]]),
            onto=tl_anchor,
        )


def test_a_function_of_more_than_two_points_is_refused(tl_anchor):
    """A ramp is its start, where the variable is, and its end; interior points belong
    to the function, bound as its parameters."""

    @ramp_function.with_points(3)
    def spline(origin, middle, terminus, time_resolution=1e-6):
        raise NotImplementedError

    with pytest.raises(ValueError, match="made of 3 points"):
        tl.to_timeline(
            tl.ramp(lockbox__MOT__V=5.0, duration=1.0, function=spline), onto=tl_anchor
        )


def test_expand_no_longer_takes_num__bounds(tl_anchor):
    """
    Removed rather than renamed. Left in place it would have been swallowed by
    `**function_args` and filtered out against the ramp function's signature, so a caller
    still passing it would have been ignored without a word.
    """
    timeline = tl.to_timeline(
        tl.ramp(lockbox__MOT__V=5.0, duration=1.0), onto=tl_anchor
    )
    with pytest.raises(TypeError, match="no longer takes `num__bounds`"):
        tl.expand(timeline, num__bounds=2, time_resolution=0.1)


def test_expand_names_the_variable_whose_ramp_rows_do_not_pair(tl_anchor):
    """
    B6. The old global stride meant one variable with an odd number of rows misaligned
    the pairing of every variable after it, and surfaced as a bare
    `ValueError: not enough values to unpack (expected 2, got 1)`.
    """
    timeline = tl.to_timeline(
        tl.ramp(lockbox__MOT__V=5.0, duration=1.0), onto=tl_anchor
    )
    timeline.loc[len(timeline)] = [
        2.0,
        "lockbox__MOT__V",
        3.0,
        "init",
        ramp_function.tanh,
    ]

    with pytest.raises(ValueError, match="lockbox__MOT__V has 3 ramp row"):
        tl.expand(timeline, time_resolution=0.1)


def test_two_ramps_of_one_variable_still_expand(tl_anchor):
    """Grouping per variable must still chunk that variable's rows, not merge them."""
    timeline = tl.to_timeline(
        tl.stack(
            tl.ramp(lockbox__MOT__V=5.0, duration=1.0),
            tl.ramp(lockbox__MOT__V=0.0, duration=1.0, time=2.0),
        ),
        onto=tl_anchor,
    )
    expanded = tl.expand(timeline, time_resolution=0.25)
    values = expanded[expanded["variable"] == "lockbox__MOT__V"]["value"].tolist()

    assert values[-1] == pytest.approx(0.0)
    assert max(values) == pytest.approx(5.0)


# --- #157: a variable is in at most one ramp at a time -------------------------


@pytest.fixture
def coil_at_zero():
    return tl.to_timeline(
        tl.stack(tl.anchor(5.0)),
        onto=tl.to_timeline(tl.update(coil__X__A=0.0, time=0.0, context="s")),
    )


def test_a_ramp_starting_inside_another_of_its_variable_raises(coil_at_zero):
    """
    The case #157 measured: the second ramp took the first one's *start* value, 0 A,
    where the coil stood at 5 A, and `expand` then paired the four boundaries in time
    order, so the coil held at 0 A until 6 s and jumped to 10 A.
    """
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=1.0), onto=coil_at_zero)
    with pytest.raises(ValueError, match="at most one ramp") as e:
        tl.to_timeline(tl.ramp(coil__X__A=20.0, duration=1.0, time=0.5), onto=first)
    assert (
        "coil__X__A: this ramp, 5.5..6.5 s, overlaps its ramp over 5.0..6.0 s"
        in str(e.value)
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
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=1.0), onto=coil_at_zero)
    with pytest.raises(ValueError, match="at most one ramp"):
        tl.to_timeline(
            tl.ramp(coil__X__A=20.0, duration=duration, time=t, origin=[5.0, None]),
            onto=first,
        )


def test_a_ramp_may_start_as_another_ends(coil_at_zero):
    """The ordinary sequence, as `magnetic_trapping`'s two `pull_coils` do it."""
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=1.0), onto=coil_at_zero)
    second = tl.to_timeline(
        tl.ramp(coil__X__A=20.0, duration=1.0, time=1.0), onto=first
    )
    values = tl.expand(second, time_resolution=0.25)
    assert values[values["variable"] == "coil__X__A"]["value"].iloc[-1] == 20.0


def test_meeting_by_rounding_is_refused_and_said_to_be_rounding():
    """
    The two times are reached by different sums: 0.1 + 0.2 is 0.30000000000000004, so a
    ramp placed at 0.3 in absolute time starts 4e-17 s before the first one ends. Its
    start value is looked up at 0.3, which the first one's end row does not yet precede,
    so a tolerance here would let it start from the wrong value. On this branch the
    lookup is still widened by `config.TIME_RESOLUTION`, which happens to cover it;
    `issue#94` removes that widening.
    """
    base = tl.to_timeline(
        tl.stack(tl.anchor(0.1)),
        onto=tl.to_timeline(tl.update(coil__X__A=0.0, time=0.0, context="s")),
    )
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=0.2), onto=base)
    assert first["time"].max() > 0.3
    with pytest.raises(ValueError, match="within rounding"):
        tl.to_timeline(
            tl.ramp(coil__X__A=20.0, duration=0.2, time=0.3, origin=[0.0, None]),
            onto=first,
        )


def test_placed_from_the_others_end_the_same_ramp_is_kept():
    base = tl.to_timeline(
        tl.stack(tl.anchor(0.1)),
        onto=tl.to_timeline(tl.update(coil__X__A=0.0, time=0.0, context="s")),
    )
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=0.2), onto=base)
    second = tl.to_timeline(
        tl.ramp(coil__X__A=20.0, duration=0.2, origin=tl.LAST), onto=first
    )
    rows = second[second["variable"] == "coil__X__A"]
    assert rows["value"].iloc[-2] == 10.0  # it starts where the first one ended


def test_ramps_of_different_variables_may_overlap():
    base = tl.to_timeline(
        tl.stack(tl.anchor(5.0)),
        onto=tl.to_timeline(
            tl.update(coil__X__A=0.0, coil__Y__A=0.0, time=0.0, context="s")
        ),
    )
    first = tl.to_timeline(tl.ramp(coil__X__A=10.0, duration=1.0), onto=base)
    both = tl.to_timeline(tl.ramp(coil__Y__A=10.0, duration=1.0, time=0.5), onto=first)
    assert set(both["variable"]) >= {"coil__X__A", "coil__Y__A"}


# --- a ramp's resolution belongs to the ramp (#65, C7 item 7) -----------------


def _ramp_times(function, **expand):
    """The times of a 1 s ramp of `x__A` built with `function`, expanded by `expand`."""
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(x__A=0.0, time=0.0, context="c"),
            tl.anchor(0.0),
            tl.ramp(x__A=1.0, duration=1.0, function=function),
        )
    )
    expanded = tl.expand(timeline, **expand)
    return list(expanded.loc[expanded["variable"] == "x__A", "time"])[1:]


@pytest.mark.parametrize(
    "function",
    [
        lambda o, t: ramp_function.tanh(o, t, 0.25),
        lambda o, t, time_resolution: ramp_function.tanh(o, t, 0.25),
        __import__("functools").partial(ramp_function.tanh, time_resolution=0.25),
    ],
    ids=["lambda", "lambda ignoring it", "partial"],
)
def test_a_resolution_the_ramp_binds_is_kept(function):
    """
    `expand`'s `time_resolution` is a default, never an override. The `partial` used to
    be sampled at `expand`'s 0.01, 101 points instead of 5, since it still declares the
    keyword and every function declaring it was handed `expand`'s value.
    """
    assert _ramp_times(function, time_resolution=0.01) == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_a_ramp_binding_no_resolution_takes_expands():
    assert len(_ramp_times(ramp_function.tanh, time_resolution=0.01)) == 101


@pytest.mark.parametrize(
    "function",
    [ramp_function.tanh, lambda origin, terminus, time_resolution: None],
    ids=["tanh", "lambda"],
)
def test_a_ramp_binding_no_resolution_expanded_with_none_is_refused(function):
    """
    The ramp functions defaulted to `config.TIME_RESOLUTION`, 1 us, bound at import
    (#144), which no ramp ever reached the hardware at: `convert` always gave the cycle
    period. Now nothing is assumed, and the message names the variable.
    """
    with pytest.raises(
        ValueError, match="x__A's ramp at 0.0 s binds no `time_resolution`"
    ):
        _ramp_times(function)


def test_a_ramp_function_called_without_a_resolution_says_where_one_comes_from():
    with pytest.raises(ValueError, match="`tanh` was given no `time_resolution`"):
        ramp_function.tanh([0.0, 0.0], [1.0, 1.0])
