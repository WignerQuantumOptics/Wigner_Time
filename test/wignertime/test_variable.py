import pytest

from wignertime import timeline as tl
from wignertime import variable


def test_variable():
    """`<device>__<UID>__<unit>` (D7, #121)."""
    assert variable.parse("coil__MOT_lower__A") == {
        "device": "coil",
        "uid": "MOT_lower",
        "unit": "A",
    }


def test_variable_no_unit():
    assert variable.parse("shutter__MOT") == {
        "device": "shutter",
        "uid": "MOT",
        "unit": "digital",
    }


def test_variable_underscored_UID():
    """The UID may contain single underscores; the device and the unit may not."""
    assert variable.parse("coil__MOT_lower_plus__A") == {
        "device": "coil",
        "uid": "MOT_lower_plus",
        "unit": "A",
    }
    assert variable.parse("shutter__transverse_pump")["uid"] == "transverse_pump"


def test_the_anchor_label_parses_as_an_anchor():
    assert variable.parse("⚓__001") == {"device": "⚓", "uid": "001", "unit": "⚓"}


def test_is_valid():
    assert variable.is_valid("AOM__imaging__V") == True


@pytest.mark.parametrize(
    "name",
    [
        "AOM",  # no UID
        "coil__MOT__lower__A",  # a `__` inside the UID
        "power_supply__X__V",  # a device of two words
        "coil__MOT_lower__A_x",  # a unit with `_`
    ],
)
def test_is_valid002(name):
    assert variable.is_valid(name) == False


def test_a_device_and_a_UID_alone_is_a_digital_line():
    """`AOMimaging__V` is not an analog name without a UID: it was never a valid name."""
    assert variable.unit("AOMimaging__V") == "digital"


@pytest.mark.parametrize(
    "old",
    [
        "coil_MOT_lower__A",
        "coil_MOTlower__A",
        "shutter_MOT",
        "shutter_transverse_pump",
        "lockbox_MOT__MHz",
        "trigger_TC__V",
        "dispenser_Rb__A",
    ],
)
def test_every_name_of_the_old_grammar_is_refused(old):
    """
    The migration is safe because of this: an old analog name has a `_` before its
    first `__`, which a device may not contain, so it is refused rather than read with
    its unit as a UID, i.e. as digital.
    """
    assert variable.is_valid(old) == False


def test_unit():
    assert variable.unit("AOM__imaging__MHz") == "MHz"


def test_unit002():
    assert variable.unit("AOM__imaging") == "digital"


def test_unit003():
    with pytest.raises(ValueError):
        variable.unit("AOM_imaging__V")


def test_units():
    assert variable.units(
        tl._populate_timeline(
            ["AOM__imaging__V", [[0.0, 2]]],
            ["AOM__repump", [[1.0, 1.0]]],
            ["coil__MOT__A", [[1.0, 10.0]]],
            ["AOM__repump__MHz", [[1.0, 10.0]]],
            context="s",
        ),
    ) == {"A", "MHz", "V", "digital"}


def test_units_nodigital():
    assert variable.units(
        tl._populate_timeline(
            ["AOM__imaging__V", [[0.0, 2]]],
            ["AOM__repump", [[1.0, 1.0]]],
            ["coil__MOT__A", [[1.0, 10.0]]],
            ["AOM__repump__MHz", [[1.0, 10.0]]],
            context="s",
        ),
        do_digital=False,
    ) == {"A", "MHz", "V"}
