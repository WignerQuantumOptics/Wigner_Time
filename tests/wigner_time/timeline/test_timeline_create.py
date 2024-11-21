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


tline = tl.create(
    [
        ["AOM_imaging", [[0.0, 0.0]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_repump", [[1.0, 1.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM_imaging",
        )
    ],
)
def test_createOrigin():
    return wt_frame.assert_equal(
        input,
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
