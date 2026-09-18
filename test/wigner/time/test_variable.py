import pytest

from wignertime import timeline as tl
from wignertime import variable


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


def test_variable_underscored_UID():
    """
    The UID may contain single underscores, so that a site preferring
    `coil_MOT_lower__A` to `coil_MOTlower__A` is not forced onto the latter.
    """
    assert variable.parse("coil_MOT_lower_plus__A") == {
        "equipment": "coil",
        "context": "MOT_lower_plus",
        "unit": "A",
    }


def test_variable_underscored_UID_no_unit():
    assert variable.parse("shutter_transverse_pump") == {
        "equipment": "shutter",
        "context": "transverse_pump",
        "unit": "digital",
    }


def test_is_valid():
    assert variable.is_valid("AOM_imaging__V") == True


def test_is_valid002():
    assert variable.is_valid("AOMimaging__V") == False


def test_is_valid003():
    """
    `__` is the unit separator, so it delimits the end of the name and can occur
    only once. Neither a missing UID nor a second separator is admissible.
    """
    assert variable.is_valid("dispenser__A") == False
    assert variable.is_valid("coil_MOT__lower__A") == False


def test_unit():
    assert variable.unit("AOM_imaging__MHz") == "MHz"


def test_unit002():
    assert variable.unit("AOM_imaging") == "digital"


def test_unit003():
    with pytest.raises(ValueError):
        variable.unit("AOMimaging__V")


def test_units():
    assert variable.units(
        tl._populate_timeline(
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
            ["coil_MOT__A", [[1.0, 10.0]]],
            ["AOM_repump__MHz", [[1.0, 10.0]]],
        ),
    ) == {"A", "MHz", "V", "digital"}


def test_units_nodigital():
    assert variable.units(
        tl._populate_timeline(
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
            ["coil_MOT__A", [[1.0, 10.0]]],
            ["AOM_repump__MHz", [[1.0, 10.0]]],
        ),
        do_digital=False,
    ) == {"A", "MHz", "V"}
