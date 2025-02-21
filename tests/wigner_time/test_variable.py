import pytest

from wigner_time import timeline as tl
from wigner_time import variable


def test_variable():
    assert variable.parse("thing_deviceOfManyParts__unit") == {
        "equipment": "thing",
        "context": "deviceOfManyParts",
        "unit": "unit",
    }


def test_variable_no_unit():
    assert variable.parse("thing_deviceOfManyParts") == {
        "equipment": "thing",
        "context": "deviceOfManyParts",
        "unit": "digital",
    }


def test_is_valid():
    assert variable.is_valid("AOM_imaging__V") == True


def test_is_valid002():
    assert variable.is_valid("AOMimaging__V") == False


def test_unit():
    assert variable.unit("AOM_imaging__MHz") == "MHz"


def test_unit002():
    assert variable.unit("AOM_imaging") == "digital"


def test_unit003():
    with pytest.raises(ValueError):
        variable.unit("AOMimaging__V")


def test_units():
    assert variable.units(
        tl.create(
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
            ["coil_MOT__A", [[1.0, 10.0]]],
            ["AOM_repump__MHz", [[1.0, 10.0]]],
        ),
    ) == {"A", "MHz", "V", "digital"}


def test_units_nodigital():
    assert variable.units(
        tl.create(
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
            ["coil_MOT__A", [[1.0, 10.0]]],
            ["AOM_repump__MHz", [[1.0, 10.0]]],
        ),
        do_digital=False,
    ) == {"A", "MHz", "V"}
