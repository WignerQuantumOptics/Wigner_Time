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


# TODO: Move examples to proper tests
# __convert_input(
#     [
#         ["AOM_imaging__V", [[2, 0.0], [3, 0.0]]],
#         ["AOM_imaging__A", [[2, 0.0], [3, 0.0]]],
#     ],
#     context="init",
# )

# __convert_input(
#     ["AOM_imaging__V", [[2, 0.0], [3, 0.0]]],
#     ["AOM_imaging__A", [[2, 0.0], [3, 0.0]]],
#     context="init",
# )

# __convert_input(
#     ["AOM_imaging__V", 0.0],
#     ["AOM_imaging__A", 0.0],
#     context="init",
#     t=0.0,
# )

# __convert_input(
#     ["AOM_imaging__V", 2],
#     context="init",
#     t=0.0,
# )


# __convert_input(
#     "AOM_imaging__V",
#     2,
#     context="init",
#     t=0.0,
# )

# __convert_input(
#     context="init",
#     AOM_imaging__V=[[2, 0.0], [3, 0.0]],
#     AOM_imaging__A=[[2, 0.0], [3, 0.0]],
# )
