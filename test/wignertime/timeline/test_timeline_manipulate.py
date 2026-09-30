import math
import pathlib as pl
import sys
import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as frame
from wignertime.internal import dataframe as wt_frame

from wignertime.demo import full_experiment as ex

# @pytest.fixture
# def df_wait():
#     return frame.new(
#         [
#             [0.0, "AOM__imaging", 0, "init"],
#             [0.0, "AOM__imaging__V", 2.0, "init"],
#             [0.0, "AOM__repump", 1, "init"],
#             [10.0, "AOM__repump", 0, "init"],
#         ],
#         columns=["time", "variable", "value", "context"],
#     )


@pytest.fixture
def dfseq():
    """
    The ramp starts at t=10.0: the timeline holds no anchor, so `ramp` falls to the
    `"last"` step of its default chain and `t=5.0` is a displacement from the last
    entry, at t=5.0.

    Until 2026-09-18 the chain had no `"last"` step, so it fell off the end and the rows
    landed in *absolute* time -- here at t=5.0, which coincided with the last entry only
    by arithmetic accident. That is A4: the same call on a timeline whose last entry sat
    at t=7.0 would have placed the ramp before it, silently.
    """
    return frame.new(
        [
            [0.0, "lockbox__MOT__V", 0.000000, "init"],
            [5.0, "lockbox__MOT__V", 0.000000, "init"],
            [10.0, "lockbox__MOT__V", 0.000000, "init"],
            [10.2, "lockbox__MOT__V", 0.045177, "init"],
            [10.4, "lockbox__MOT__V", 0.500000, "init"],
            [10.6, "lockbox__MOT__V", 0.954823, "init"],
            [10.8, "lockbox__MOT__V", 1.000000, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


def test_stack(dfseq):
    tst = tl.to_timeline(
        tl.stack(
            tl.ramp(time=5.0, lockbox__MOT__V=[0.8, 1.0]),
            lambda tline: tl.expand(tline, time_resolution=0.2),
        ),
        onto=tl._populate_timeline(
            "lockbox__MOT__V", [[0.0, 0.0], [5.0, 0.0]], context="init"
        ),
    )
    return frame.assert_equal(tst, dfseq)


def test_stack__kws(dfseq):
    tline = tl._populate_timeline(
        "lockbox__MOT__V", [[0.0, 0.0], [5.0, 0.0]], context="init"
    )
    tst = tl.expand(
        tl.to_timeline(
            tl.stack(tl.ramp(time=5.0, lockbox__MOT__V=[0.8, 1.0]), context="test"),
            onto=tline,
        ),
        time_resolution=0.2,
    )

    return frame.assert_equal(
        tst,
        frame.new(
            [
                [0.0, "lockbox__MOT__V", 0.000000, "init"],
                [5.0, "lockbox__MOT__V", 0.000000, "init"],
                [10.0, "lockbox__MOT__V", 0.000000, "test"],
                [10.2, "lockbox__MOT__V", 0.045177, "test"],
                [10.4, "lockbox__MOT__V", 0.500000, "test"],
                [10.6, "lockbox__MOT__V", 0.954823, "test"],
                [10.8, "lockbox__MOT__V", 1.000000, "test"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_cascade():
    frame.assert_equal(
        tl.to_timeline(
            tl.cascade(
                ex.init,
                ex.MOT,
                #
                MOT_duration=5.0,
                MOT_lower_current=-1.0,
                MOT_upper_current=-0.98,
            )
        ),
        frame.new(
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
                [0.0, "shutter__MOT", 1.0, "MOT"],
                [0.0, "shutter__repump", 1.0, "MOT"],
                [0.0, "coil__MOT_lower__A", -1.0, "MOT"],
                [0.0, "coil__MOT_upper__A", -0.98, "MOT"],
                [5.0, "⚓__001", 0.0, "MOT"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


# def test_waitVariable(df_wait):
#     return frame.assert_equal(
#         tl.wait(variables=["AOM__imaging"], timeline=df_wait, context="test"),
#         frame.new(
#             {
#                 "time": {0: 0.0, 1: 0.0, 2: 0.0, 3: 10.0, 4: 10.0},
#                 "variable": {
#                     0: "AOM__imaging",
#                     1: "AOM__imaging__V",
#                     2: "AOM__repump",
#                     3: "AOM__repump",
#                     4: "AOM__imaging",
#                 },
#                 "value": {0: 0.0, 1: 2.0, 2: 1.0, 3: 0.0, 4: 0.0},
#                 "context": {0: "init", 1: "init", 2: "init", 3: "init", 4: "test"},
#             }
#         ),
#     )


# def test_waitAll(df_wait):
#     return frame.assert_equal(
#         tl.wait(timeline=df_wait),
#         frame.new(
#             [
#                 [0.0, "AOM__imaging", 0.0, "init"],
#                 [0.0, "AOM__imaging__V", 2.0, "init"],
#                 [0.0, "AOM__repump", 1.0, "init"],
#                 [10.0, "AOM__repump", 0.0, "init"],
#                 [10.0, "AOM__imaging", 0.0, "init"],
#                 [10.0, "AOM__imaging__V", 2.0, "init"],
#             ],
#             columns=["time", "variable", "value", "context"],
#         ),
#     )


def test_cascade_rejects_a_keyword_naming_no_stage():
    """
    `molasses` is not among the stages, so `molasses_duration` reaches nothing.

    This used to be dropped in silence, leaving every stage on its defaults -- a
    physically different sequence that still runs. The test previously asserted that
    behaviour; it now asserts the error.
    """
    with pytest.raises(TypeError, match="matches no stage name"):
        tl.to_timeline(
            tl.cascade(ex.init, ex.MOT, MOT_duration=5.0, molasses_duration=5.0)
        )


def test_cascade_rejects_a_keyword_naming_no_parameter():
    """
    The stage is real but the parameter is misspelled, which is the likelier mistake.
    """
    with pytest.raises(TypeError, match="is not a parameter of"):
        tl.to_timeline(tl.cascade(ex.init, ex.MOT, MOT_duratoin=5.0))


def test_cascade_matches_on_a_prefix_not_a_substring():
    """
    A2. `MOT` must not capture a keyword merely because the name occurs inside it, and
    the longer stage name must win where both anchor -- `MOT_` also begins
    `MOT_detuned_growth_duration`.
    """
    stacked = tl.to_timeline(
        tl.cascade(
            ex.init,
            ex.MOT,
            ex.MOT_detuned_growth,
            MOT_duration=5.0,
            MOT_detuned_growth_duration=0.2,
        )
    )
    assert isinstance(stacked, wt_frame.CLASS) or callable(stacked)


def test_cascade_stays_permissive_where_the_target_has_kwargs():
    """
    `init` forwards `**kwargs` to `default_state`, where an unrecognised keyword is
    meant to be read as a variable. Strictness is derived from the signature, so that
    path must survive it -- see `sec:forwarding`.
    """
    built = tl.to_timeline(
        tl.cascade(ex.init, ex.MOT, init_coil__MOT_lower__A=0.5, MOT_duration=1.0)
    )
    assert 0.5 in set(
        wt_frame.column(built, "value")[
            wt_frame.column(built, "variable") == "coil__MOT_lower__A"
        ]
    ), "injection through `init` into `default_state` must still work"


def test_expand_leaves_the_timeline_it_was_given_alone():
    """
    B5/#112. `expand` dropped the ramp rows and the `function` column from its *argument*,
    in place -- the one core function that did not leave its input alone. The "description
    is data" story depends on a frame not changing under whoever is holding it.

    `demo.timeline_demo` is a module-level object imported by tests, so a single
    `expand` on it used to strip it for every later user in the process: 99 rows to 57,
    and no `function` column.
    """
    timeline = tl.to_timeline(
        tl.stack(
            tl.anchor(1.0, context="s"),
            tl.ramp(c__A=9.0, duration=0.5),
        ),
        onto=tl.to_timeline(tl.update(c__A=2.0, time=0.0, context="s")),
    )
    before = wt_frame.copy(timeline)

    expanded = tl.expand(timeline, time_resolution=0.1)

    wt_frame.assert_equal(timeline, before)
    assert "function" in wt_frame.columns(timeline)
    assert len(expanded) > len(timeline)

    # And so expanding twice gives the same answer, rather than the second call silently
    # returning a frame whose ramps have already been stripped out of it.
    wt_frame.assert_equal(expanded, tl.expand(timeline, time_resolution=0.1))


def test_convert_leaves_the_timeline_it_was_given_alone():
    """
    `adwin.core.convert` expands internally. It was unharmed by B5 only by accident of
    pipeline order -- `remove_unconnected_variables` runs first and hands `expand` a fresh
    frame -- so it is worth pinning rather than assuming.
    """
    from wignertime.adwin import core

    before = wt_frame.copy(ex.timeline_demo)
    core.convert(ex.timeline_demo, ex.connections, ex.devices, 5e-6)
    wt_frame.assert_equal(ex.timeline_demo, before)


def test_expand_puts_each_ramp_where_it_was_written():
    """
    A18. Among a variable's rows at one instant the last written is in effect, so the
    expanded rows of a ramp must stay before the rows written after it. They were put
    back by position arithmetic that shifted every insertion after the first, so the
    second ramp here landed after both updates written after it, and at t = 2 its end
    (2.0) came after the update (-2.0) written to supersede it.
    """
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(x__A=0.0, y=0, time=0.0, context="c"),
            tl.ramp(x__A=1.0, time=0.0, duration=1.0, origin=0.0),
            tl.update(y=1, time=0.5, origin=0.0),
            tl.ramp(x__A=2.0, time=1.0, duration=1.0, origin=0.0),
            tl.update(x__A=-2.0, time=2.0, origin=0.0),
            tl.update(y=0, time=2.5, origin=0.0),
        )
    )
    expanded = tl.expand(timeline, time_resolution=0.5)
    assert wt_frame.rows(expanded, ["time", "variable", "value"]) == [
        (0.0, "x__A", 0.0),
        (0.0, "y", 0.0),
        (0.0, "x__A", 0.0),
        (0.5, "x__A", 0.5),
        (1.0, "x__A", 1.0),
        (0.5, "y", 1.0),
        (1.0, "x__A", 1.0),
        (1.5, "x__A", 1.5),
        (2.0, "x__A", 2.0),
        (2.0, "x__A", -2.0),
        (2.5, "y", 0.0),
    ]
