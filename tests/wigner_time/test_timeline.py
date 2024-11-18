import pytest
import pandas as pd

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as frame


@pytest.fixture
def df_simple():
    return frame.new(
        [
            [0.0, "AOM_imaging", 0.0, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


df_previous1 = frame.new(
    [
        ["thing2", 7.0, 5.0, "init"],
        ["thing", 0.0, 5.0, "init"],
        ["thing3", 3.0, 5.0, "blah"],
    ],
    columns=["variable", "time", "value", "context"],
)
df_previous2 = frame.new(
    [
        ["thing2", 7.0, 5, "init"],
        ["thing", 0.0, 5, "init"],
        ["thing3", 3.0, 5, "blah"],
        ["thing4", 7.0, 5, "init"],
    ],
    columns=["variable", "time", "value", "context"],
)


@pytest.mark.parametrize("input_value", [df_previous1, df_previous2])
def test_previous(input_value):
    row = df_previous2.loc[0]

    return pd.testing.assert_series_equal(tl.previous(input_value), row)


@pytest.mark.parametrize("input_value", [df_previous1, df_previous2])
def test_previousSort(input_value, sort_by="time"):
    row = df_previous2.loc[0]
    return pd.testing.assert_series_equal(tl.previous(input_value), row)


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


def test_createSimple(df_simple):
    tst = tl.create("AOM_imaging", 0.0, 0.0)
    return frame.assert_equal(tst, df_simple)


def test_createSingle(df_simple):
    tst = tl.create("AOM_imaging", [[0.0, 0.0]])
    return frame.assert_equal(tst, df_simple)


def test_createOriginal(df):
    tst = tl.create(
        [
            ["AOM_imaging", [[0.0, 0.0]]],
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[0.0, 1.0]]],
        ],
        context="init",
    )
    return frame.assert_equal(tst, df)


def test_createManyListPairs(df):
    tst = tl.create(
        [
            ["AOM_imaging", 0.0],
            ["AOM_imaging__V", 2],
            ["AOM_repump", 1.0],
        ],
        context="init",
        t=0.0,
    )
    return frame.assert_equal(tst, df)


def test_createManyArgs(df):
    tst = tl.create(
        ["AOM_imaging", 0.0],
        ["AOM_imaging__V", 2],
        ["AOM_repump", 1.0],
        context="init",
        t=0.0,
    )
    return frame.assert_equal(tst, df)


def test_createManyKWargs(df):
    tst = tl.create(
        context="init",
        t=0.0,
        AOM_imaging=0.0,
        AOM_imaging__V=2,
        AOM_repump=1.0,
    )
    return frame.assert_equal(tst, df)


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


devices001 = frame.new(
    [
        ["coil_compensationX__A", (-3, 3), (-3, 3)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)
devices002 = frame.new(
    [
        ["coil_compensationX__A", (-5, 5), (-3, 3)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)
devices003 = frame.new(
    [
        ["coil_compensationX__A", (-5, 5), (-5, 5)],
    ],
    columns=["variable", "unit_range", "safety_range"],
)

df_sanitize001 = frame.new(
    [
        [0.0, "AOM_imaging", 0.0, ""],
        [0.0, "AOM_imaging", 0.0, ""],
        [0.0, "coil_compensationX__A", 0.0, "coil"],
        [0.0, "coil_compensationX__A", 10.0, "coil"],
        [10.0, "coil_compensationX__A", 5.0, "coil"],
    ],
    columns=["time", "variable", "value", "context"],
)


@pytest.mark.parametrize(
    "input_value", [[df_sanitize001, devices001], [df_sanitize001, devices002]]
)
def test_sanitize_raises(input_value):
    df, dev = input_value
    with pytest.raises(ValueError):
        tl.sanitize(frame.join(df, dev))


@pytest.mark.parametrize(
    "input_value",
    [
        [df_sanitize001, devices003],
    ],
)
def test_sanitize_success(input_value):
    df, dev = input_value
    return frame.assert_equal(
        tl.sanitize(df),
        frame.new(
            [
                [0.0, "AOM_imaging", 0.0, ""],
                [0.0, "coil_compensationX__A", 10.0, "coil"],
                [10.0, "coil_compensationX__A", 5.0, "coil"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


###########################################################################
#                               scratch                                   #
###########################################################################
if __name__ == "__main__":
    import importlib
