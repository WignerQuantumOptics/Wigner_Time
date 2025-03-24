import pytest

from wigner_time import timeline as tl
from wigner_time.internal import dataframe as wt_frame
from wigner_time.internal import origin


@pytest.fixture
def df_simple():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0.0, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "input",
    [
        tl.create("AOM_imaging", 0.0, 0.0),
        tl.create("AOM_imaging", [[0.0, 0.0]]),
    ],
)
def test_createSimple(input, df_simple):
    return wt_frame.assert_equal(input, df_simple)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[0.0, 1.0]]],
            ],
            context="init",
        ),
        tl.create(
            [
                ["AOM_imaging", 0.0],
                ["AOM_imaging__V", 2],
                ["AOM_repump", 1.0],
            ],
            context="init",
            t=0.0,
        ),
        tl.create(
            ["AOM_imaging", 0.0],
            ["AOM_imaging__V", 2],
            ["AOM_repump", 1.0],
            context="init",
            t=0.0,
        ),
        tl.create(
            context="init",
            t=0.0,
            AOM_imaging=0.0,
            AOM_imaging__V=2,
            AOM_repump=1.0,
        ),
    ],
)
def test_createDifferent(input, df):
    return wt_frame.assert_equal(input, df)


df_previous = wt_frame.new(
    [
        [0.0, "AOM_imaging", 0, "init"],
        [0.0, "AOM_imaging__V", 2.0, "init"],
        [0.0, "AOM_repump", 1, "init"],
    ],
    columns=["time", "variable", "value", "context"],
)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(AOM_repump=[10.0, 0.0, "important"], timeline=df_previous),
        tl.create("AOM_repump", 10.0, 0.0, "important", timeline=df_previous),
        tl.create(["AOM_repump", 10.0, 0.0, "important"], timeline=df_previous),
        tl.create(["AOM_repump", [10.0, 0.0, "important"]], timeline=df_previous),
    ],
)
def test_createPrevious(input, df):
    print(input)
    df_check = wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
            [10.0, "AOM_repump", 0, "important"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return wt_frame.assert_equal(input, df_check)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            AOM_imaging=[0.0, 0, "init"],
            AOM_imaging__V=[0.0, 2.0, "init"],
            AOM_repump=[0.0, 1, "init"],
        ),
        tl.create(
            ["AOM_imaging", [0.0, 0, "init"]],
            ["AOM_imaging__V", [0.0, 2.0, "init"]],
            ["AOM_repump", [0.0, 1, "init"]],
        ),
        tl.create(
            ["AOM_imaging", 0.0, 0, "init"],
            ["AOM_imaging__V", 0.0, 2.0, "init"],
            ["AOM_repump", 0.0, 1, "init"],
        ),
    ],
)
def test_createContext(input, df):
    print(input)
    print(df)
    return wt_frame.assert_equal(input, df)


###############################################################################
#                             Playing with origin                             #
###############################################################################


tline = tl.create(
    [
        ["AOM_imaging", [[0.0, 0.0]]],
        ["other_thing", [[0.0, 0.0]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_repump", [[1.0, 1.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[1.0, 1.0]]],
                ["AOM_imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
            origin=[0.0, 0.0],
        ),
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=[0.0],
        ),
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=0.0,
        ),
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM_imaging",
        ),
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM_imaging", "AOM_imaging"],
        ),
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM_imaging", "other_thing"],
        ),
    ],
)
def test_createOrigin0(input):
    return wt_frame.assert_equal(
        input,
        tl.create(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[1.0, 1.0]]],
                ["AOM_imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
        ),
    )


tline2 = tl.create(
    [
        ["AOM_imaging", [[1.0, 1.0]]],
        ["AOM_imaging__V", [[0.0, 2]]],
    ],
    context="init",
)

expected = tl.create(
    [
        ["AOM_imaging", [[1.0, 1]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_imaging", [[2.0, 10.0]]],
        ["AOM_imaging__V", [[1.4, 5.0]]],
    ],
    context="init",
)
expected2 = tl.create(
    [
        ["AOM_imaging", [[1.0, 1]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_imaging", [[2.0, 11.0]]],
        ["AOM_imaging__V", [[1.4, 7.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        [
            "variable",
            expected,
        ],
        [
            ["variable"],
            expected,
        ],
    ],
)
def test_createOriginVariable(input):
    return wt_frame.assert_equal(
        tl.create(
            AOM_imaging=[1.0, 10.0],
            AOM_imaging__V=[1.4, 5.0],
            timeline=tline2,
            origin=input[0],
        ),
        input[1],
    )


@pytest.mark.parametrize(
    "input",
    [
        [
            ["variable", "variable"],
            expected2,
        ],
    ],
)
def test_createOriginVariableVariable(input):
    return wt_frame.assert_equal(
        tl.create(
            AOM_imaging=[1.0, 10.0],
            AOM_imaging__V=[1.4, 5.0],
            timeline=tline2,
            origin=input[0],
        ),
        input[1],
    )


if __name__ == "__main__":
    import importlib as lib

    lib.reload(tl)
    lib.reload(origin)

    tline = tl.create(
        [
            ["AOM_imaging", [[0.0, 0.0]]],
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
        ],
        context="init",
    )
    print(
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM_imaging",
        )
    )
