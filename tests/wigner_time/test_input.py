import pytest
import pandas as pd

from wigner_time import timeline as tl
from wigner_time import input


def test_ensure_time_context():
    assert input.__ensure_time_context((0.0, 0.0), 0.0, context=None) == [
        [0.0, 0.0, ""]
    ]


def test_rows_from_arguments():
    assert input.rows_from_arguments("AOM_imaging", 0.0, 0.0) == [
        [0.0, "AOM_imaging", 0.0, ""]
    ]


@pytest.mark.parametrize(
    "input",
    [
        input.convert("AOM_repump", 10.0, 0.0, "important"),
        input.convert(["AOM_repump", 10.0, 0.0, "important"]),
    ],
)
def test_convertSingle(input):
    expected = [
        ["AOM_repump", [[10.0, 0.0, "important"]]],
    ]
    assert input == expected


@pytest.mark.parametrize(
    "input",
    [
        input.convert(
            ["AOM_imaging__V", 0.0], ["AOM_imaging__A", 0.0], context="init", time=0.0
        ),
        input.convert(
            [["AOM_imaging__V", 0.0], ["AOM_imaging__A", 0.0]], context="init", time=0.0
        ),
    ],
)
def test_convert(input):
    expected = [
        ["AOM_imaging__V", [[0.0, 0.0, "init"]]],
        ["AOM_imaging__A", [[0.0, 0.0, "init"]]],
    ]
    assert input == expected


@pytest.mark.parametrize(
    "input",
    [
        input.convert(
            [
                ["AOM_imaging__V", [[2, 0.0], [3, 0.0]]],
                ["AOM_imaging__A", [[2, 0.0], [3, 0.0]]],
            ],
            context="init",
        ),
        input.convert(
            ["AOM_imaging__V", [[2, 0.0], [3, 0.0]]],
            ["AOM_imaging__A", [[2, 0.0], [3, 0.0]]],
            context="init",
        ),
        input.convert(
            AOM_imaging__V=[[2, 0.0], [3, 0.0]],
            AOM_imaging__A=[[2, 0.0], [3, 0.0]],
            context="init",
        ),
    ],
)
def test_convertMulti(input):
    expected = [
        ["AOM_imaging__V", [[2.0, 0.0, "init"], [3.0, 0.0, "init"]]],
        ["AOM_imaging__A", [[2.0, 0.0, "init"], [3.0, 0.0, "init"]]],
    ]
    assert input == expected
