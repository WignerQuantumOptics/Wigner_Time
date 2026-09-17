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
#             [0.0, "AOM_imaging", 0, "init"],
#             [0.0, "AOM_imaging__V", 2.0, "init"],
#             [0.0, "AOM_repump", 1, "init"],
#             [10.0, "AOM_repump", 0, "init"],
#         ],
#         columns=["time", "variable", "value", "context"],
#     )


@pytest.fixture
def dfseq():
    return frame.new(
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


def test_stack(dfseq):
    tst = tl.stack(
        tl._populate_timeline("lockbox_MOT__V", [[0.0, 0.0], [5.0, 0.0]]),
        tl.ramp(t=5.0, lockbox_MOT__V=[0.8, 1.0]),
        lambda tline: tl.expand(tline, time_resolution=0.2),
    )
    return frame.assert_equal(tst, dfseq)


def test_stack__kws(dfseq):
    tline = tl._populate_timeline("lockbox_MOT__V", [[0.0, 0.0], [5.0, 0.0]])
    tst = tl.stack(
        tline,
        tl.ramp(t=5.0, lockbox_MOT__V=[0.8, 1.0]),
        tl.expand(time_resolution=0.2),
        #
        context="test",
    )

    return frame.assert_equal(
        tst,
        frame.new(
            [
                [0.0, "lockbox_MOT__V", 0.000000, ""],
                [5.0, "lockbox_MOT__V", 0.000000, ""],
                [5.0, "lockbox_MOT__V", 0.000000, "test"],
                [5.2, "lockbox_MOT__V", 0.045177, "test"],
                [5.4, "lockbox_MOT__V", 0.500000, "test"],
                [5.6, "lockbox_MOT__V", 0.954823, "test"],
                [5.8, "lockbox_MOT__V", 1.000000, "test"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_cascade():
    frame.assert_equal(
        tl.cascade(
            ex.init,
            ex.MOT,
            #
            MOT_duration=5.0,
            MOT_lA=-1.0,
            MOT_uA=-0.98,
        ),
        frame.new(
            [
                [-1e-06, "lockbox_MOT__MHz", 0.0, "ADwin_LowInit"],
                [-1e-06, "coil_compensationX__A", 0.25, "ADwin_LowInit"],
                [-1e-06, "coil_compensationY__A", 1.5, "ADwin_LowInit"],
                [-1e-06, "coil_MOTlowerPlus__A", 0.1, "ADwin_LowInit"],
                [-1e-06, "coil_MOTupperPlus__A", -0.1, "ADwin_LowInit"],
                [-1e-06, "AOM_MOT", 1.0, "ADwin_LowInit"],
                [-1e-06, "AOM_repump", 1.0, "ADwin_LowInit"],
                [-1e-06, "AOM_OPaux", 0.0, "ADwin_LowInit"],
                [-1e-06, "AOM_OP", 1.0, "ADwin_LowInit"],
                [-1e-06, "AOM_science", 1.0, "ADwin_LowInit"],
                [-1e-06, "shutter_MOT", 0.0, "ADwin_LowInit"],
                [-1e-06, "shutter_repump", 0.0, "ADwin_LowInit"],
                [-1e-06, "shutter_OP001", 0.0, "ADwin_LowInit"],
                [-1e-06, "shutter_OP002", 1.0, "ADwin_LowInit"],
                [-1e-06, "shutter_science", 0.0, "ADwin_LowInit"],
                [-1e-06, "shutter_transversePump", 0.0, "ADwin_LowInit"],
                [-1e-06, "AOM_science__trans", 1.0, "ADwin_LowInit"],
                [-1e-06, "trigger_TC__V", 0.0, "ADwin_LowInit"],
                [0.0, "shutter_MOT", 1.0, "MOT"],
                [0.0, "shutter_repump", 1.0, "MOT"],
                [0.0, "coil_MOTlower__A", -1.0, "MOT"],
                [0.0, "coil_MOTupper__A", -0.98, "MOT"],
                [5.0, "⚓_001", 0.0, "MOT"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


# def test_waitVariable(df_wait):
#     return frame.assert_equal(
#         tl.wait(variables=["AOM_imaging"], timeline=df_wait, context="test"),
#         frame.new(
#             {
#                 "time": {0: 0.0, 1: 0.0, 2: 0.0, 3: 10.0, 4: 10.0},
#                 "variable": {
#                     0: "AOM_imaging",
#                     1: "AOM_imaging__V",
#                     2: "AOM_repump",
#                     3: "AOM_repump",
#                     4: "AOM_imaging",
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
#                 [0.0, "AOM_imaging", 0.0, "init"],
#                 [0.0, "AOM_imaging__V", 2.0, "init"],
#                 [0.0, "AOM_repump", 1.0, "init"],
#                 [10.0, "AOM_repump", 0.0, "init"],
#                 [10.0, "AOM_imaging", 0.0, "init"],
#                 [10.0, "AOM_imaging__V", 2.0, "init"],
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
        tl.cascade(ex.init, ex.MOT, MOT_duration=5.0, molasses_duration=5.0)


def test_cascade_rejects_a_keyword_naming_no_parameter():
    """
    The stage is real but the parameter is misspelled, which is the likelier mistake.
    """
    with pytest.raises(TypeError, match="is not a parameter of"):
        tl.cascade(ex.init, ex.MOT, MOT_duratoin=5.0)


def test_cascade_matches_on_a_prefix_not_a_substring():
    """
    A2. `MOT` must not capture a keyword merely because the name occurs inside it, and
    the longer stage name must win where both anchor -- `MOT_` also begins
    `MOT__detuned_growth_duration`.
    """
    stacked = tl.cascade(
        ex.init,
        ex.MOT,
        ex.MOT__detuned_growth,
        MOT_duration=5.0,
        MOT__detuned_growth_duration=0.2,
    )
    assert isinstance(stacked, wt_frame.CLASS) or callable(stacked)


def test_cascade_stays_permissive_where_the_target_has_kwargs():
    """
    `init` forwards `**kwargs` to `default_state`, where an unrecognised keyword is
    meant to be read as a variable. Strictness is derived from the signature, so that
    path must survive it -- see `sec:forwarding`.
    """
    built = tl.cascade(ex.init, ex.MOT, init_coil_MOTlower__A=0.5, MOT_duration=1.0)
    assert 0.5 in set(
        built.loc[built["variable"] == "coil_MOTlower__A", "value"]
    ), "injection through `init` into `default_state` must still work"
