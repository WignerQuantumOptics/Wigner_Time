import pytest

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame


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


# def test_stack(dfseq):
#     tst = tl.stack(
#         tl.create("lockbox_MOT__V", [[0.0, 0.0]]),
#         tl.wait(5.0, "lockbox_MOT__V"),
#         tl.ramp0(
#             "lockbox_MOT__V", 1.0, 1.0, fargs={"time_resolution": 0.2}, duration=1.0
#         ),
#         # tl.wait(),  # This shouldn't do anything for a timeline of a single variable.
#     )
#     return frame.assert_equal(tst, dfseq)


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
