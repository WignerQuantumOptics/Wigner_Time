"""
Regression tests for `wignertime.device.check_within_range`.

Run with `pytest test_check_within_range.py` from this directory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "shim"))

import numpy as np
import pandas as pd
import pytest

from wignertime import device


def frame(rows):
    """rows are (variable, value, value__min, value__max)."""
    return pd.DataFrame(
        [
            dict(variable=v, value=float(val), value__min=lo, value__max=hi)
            for v, val, lo, hi in rows
        ]
    )


NAN = np.nan

# a realistic post-join frame: digital lines carry no device entry
MIXED = frame(
    [
        ("AOM_MOT", 1.0, NAN, NAN),
        ("shutter_MOT", 1.0, NAN, NAN),
        ("AOM_science__trans", 1.0, 0.0, 1.0),
        ("coil_MOTlower__A", -1.0, -5.0, 5.0),
        ("coil_MOTupper__A", -0.98, -5.0, 5.0),
        ("lockbox_MOT__MHz", -5.0, -200.0, 200.0),
    ]
)


# --- the reported failure -------------------------------------------------


def test_digital_variables_without_a_device_entry_do_not_raise():
    assert device.check_within_range(MIXED) is True


def test_alphabetically_first_variable_being_digital_is_harmless():
    """`groupby` visits AOM_MOT first; NaN bounds must not be read as 'column absent'."""
    assert device.check_within_range(MIXED.sort_values("variable")) is True


# --- the bug behind it ----------------------------------------------------


def test_every_variable_is_checked_not_just_the_first():
    tl = MIXED.copy()
    tl.loc[tl["variable"] == "coil_MOTlower__A", "value"] = 99.0
    with pytest.raises(ValueError, match="coil_MOTlower__A"):
        device.check_within_range(tl)


def test_a_late_variable_is_caught_after_early_ones_pass():
    tl = frame(
        [
            ("aaa__A", 0.0, -1.0, 1.0),
            ("bbb__A", 0.0, -1.0, 1.0),
            ("zzz__A", 500.0, -1.0, 1.0),
        ]
    )
    with pytest.raises(ValueError, match="zzz__A"):
        device.check_within_range(tl)


def test_all_violations_are_reported_together():
    tl = frame(
        [
            ("aaa__A", 9.0, -1.0, 1.0),
            ("zzz__A", -9.0, -1.0, 1.0),
        ]
    )
    with pytest.raises(ValueError) as excinfo:
        device.check_within_range(tl)
    assert "aaa__A" in str(excinfo.value)
    assert "zzz__A" in str(excinfo.value)


def test_both_directions_are_detected():
    with pytest.raises(ValueError, match="above"):
        device.check_within_range(frame([("a__A", 2.0, -1.0, 1.0)]))
    with pytest.raises(ValueError, match="below"):
        device.check_within_range(frame([("a__A", -2.0, -1.0, 1.0)]))


def test_extremes_within_a_group_are_used_not_the_first_row():
    tl = frame(
        [
            ("a__A", 0.0, -1.0, 1.0),
            ("a__A", 5.0, -1.0, 1.0),
        ]
    )
    with pytest.raises(ValueError, match="a__A"):
        device.check_within_range(tl)


# --- the `.any()` idiom ---------------------------------------------------


def test_a_zero_upper_bound_is_a_real_bound():
    """A device restricted to non-positive values: `.any()` would have read 0.0 as absent."""
    with pytest.raises(ValueError, match="above"):
        device.check_within_range(frame([("a__A", 1.0, -5.0, 0.0)]))
    assert device.check_within_range(frame([("a__A", -1.0, -5.0, 0.0)])) is True


def test_infinite_bounds_pass():
    tl = frame([("a__A", 1e9, -np.inf, np.inf)])
    assert device.check_within_range(tl) is True


def test_one_sided_bound_is_still_checked():
    with pytest.raises(ValueError, match="below"):
        device.check_within_range(frame([("a__A", -9.0, -1.0, NAN)]))
    assert device.check_within_range(frame([("a__A", 9.0, -1.0, NAN)])) is True


# --- guards ---------------------------------------------------------------


def test_missing_bound_columns_raise_accurately():
    tl = MIXED.drop(columns=["value__max"])
    with pytest.raises(ValueError, match="value__max"):
        device.check_within_range(tl)


def test_the_message_no_longer_lies():
    """The old message named a column that was present. Confirm it fires only when absent."""
    with pytest.raises(ValueError) as excinfo:
        device.check_within_range(MIXED.drop(columns=["value__min", "value__max"]))
    assert "absent" in str(excinfo.value)


def test_non_float_values_raise():
    tl = MIXED.copy()
    tl["value"] = tl["value"].astype(str)
    with pytest.raises(ValueError, match="floats"):
        device.check_within_range(tl)


def test_empty_timeline_passes():
    empty = MIXED.iloc[0:0]
    assert device.check_within_range(empty) is True


def test_input_is_not_mutated():
    before = MIXED.copy()
    device.check_within_range(MIXED)
    pd.testing.assert_frame_equal(MIXED, before)