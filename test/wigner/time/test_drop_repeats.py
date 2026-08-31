"""
Regression tests for `wignertime.adwin.validate.drop_repeats`.

Run with `pytest test_drop_repeats.py` from this directory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "shim"))

import numpy as np
import pandas as pd
import pytest

import wignertime.adwin as wt_adwin
from wignertime.adwin import validate


COLUMNS = list(wt_adwin.SCHEMA.keys())


def frame(rows):
    """
    Rows are (time, variable, value, context, module, channel, cycle, value__digits).
    """
    return pd.DataFrame(rows, columns=COLUMNS).astype(wt_adwin.SCHEMA)


def row(cycle, digits, variable="coil__A", context="MOT", module=2, channel=1):
    return (
        cycle * 1e-6,
        variable,
        float(digits),
        context,
        module,
        channel,
        cycle,
        digits,
    )


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


def test_repeated_digits_are_dropped():
    tl = frame([row(c, d) for c, d in [(0, 100), (1, 100), (2, 100), (3, 101)]])
    result = validate.drop_repeats(tl)
    assert list(result["cycle"]) == [0, 3]


def test_a_value_that_returns_is_kept():
    """A → B → A is three genuine transitions, not a repeat."""
    tl = frame([row(c, d) for c, d in [(0, 100), (1, 200), (2, 100)]])
    assert len(validate.drop_repeats(tl)) == 3


def test_channels_are_independent():
    tl = frame(
        [
            row(0, 100, variable="a", channel=1),
            row(1, 100, variable="b", channel=2),
            row(2, 100, variable="a", channel=1),
            row(3, 100, variable="b", channel=2),
        ]
    )
    result = validate.drop_repeats(tl)
    # first and last of each channel survive; nothing in between to drop
    assert len(result) == 4


def test_same_channel_different_variables_share_state():
    """Grouping is by physical channel, so an aliased connection is still deduplicated."""
    tl = frame(
        [
            row(0, 100, variable="a", channel=1),
            row(1, 100, variable="b", channel=1),
            row(2, 100, variable="a", channel=1),
            row(3, 101, variable="b", channel=1),
        ]
    )
    assert list(validate.drop_repeats(tl)["cycle"]) == [0, 3]


def test_module_is_part_of_the_key():
    """Channel 1 on module 2 is not channel 1 on module 3."""
    tl = frame(
        [
            row(0, 100, variable="a", module=2, channel=1),
            row(1, 100, variable="b", module=3, channel=1),
        ]
    )
    assert len(validate.drop_repeats(tl)) == 2


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def test_first_row_of_a_channel_is_always_kept():
    tl = frame([row(c, 100) for c in range(5)])
    assert list(validate.drop_repeats(tl)["cycle"]) == [0, 4]


def test_last_row_of_a_channel_is_always_kept():
    """
    The run length is taken from the highest non-special cycle, and the tail of a
    tanh ramp is flat. Dropping trailing repeats would shorten the experiment.
    """
    tl = frame([row(c, d) for c, d in [(0, 0), (1, 50), (2, 100), (3, 100), (4, 100)]])
    result = validate.drop_repeats(tl)
    assert result["cycle"].max() == 4
    assert list(result["cycle"]) == [0, 1, 2, 4]


def test_run_length_is_preserved_across_channels():
    tl = frame(
        [row(c, 100, variable="a", channel=1) for c in range(3)]
        + [row(c, 7, variable="b", channel=2) for c in range(3)]
    )
    before = tl["cycle"].max()
    assert validate.drop_repeats(tl)["cycle"].max() == before


def test_single_row_channel_survives():
    tl = frame([row(0, 100)])
    assert len(validate.drop_repeats(tl)) == 1


# ---------------------------------------------------------------------------
# Special contexts
# ---------------------------------------------------------------------------


def test_special_context_rows_are_never_dropped():
    tl = frame(
        [
            row(-2, 100, context="ADwin_LowInit"),
            row(0, 100),
            row(1, 100),
            row(2**31 - 1, 100, context="ADwin_Finish"),
        ]
    )
    result = validate.drop_repeats(tl)
    assert set(result["context"]) >= {"ADwin_LowInit", "ADwin_Finish"}


def test_special_context_does_not_suppress_the_first_run_row():
    """
    Whether a LowInit assignment persists into the run is a property of the ADbasic
    program, not of the timeline, so it must not participate in the comparison.
    """
    tl = frame(
        [
            row(-2, 100, context="ADwin_LowInit"),
            row(0, 100),
            row(1, 100),
        ]
    )
    result = validate.drop_repeats(tl)
    assert 0 in list(result["cycle"])


def test_finish_context_does_not_absorb_the_last_run_row():
    tl = frame(
        [
            row(0, 100),
            row(1, 101),
            row(2**31 - 1, 101, context="ADwin_Finish"),
        ]
    )
    result = validate.drop_repeats(tl)
    assert list(result["cycle"]) == [0, 1, 2**31 - 1]


# ---------------------------------------------------------------------------
# Frame hygiene
# ---------------------------------------------------------------------------


def test_row_order_and_columns_are_unchanged():
    tl = frame([row(c, d) for c, d in [(0, 1), (1, 1), (2, 2), (3, 2), (4, 3)]])
    result = validate.drop_repeats(tl)
    assert list(result.columns) == COLUMNS
    assert result["cycle"].is_monotonic_increasing
    assert result.dtypes.to_dict() == tl.dtypes.to_dict()


def test_input_is_not_mutated():
    tl = frame([row(c, 100) for c in range(4)])
    before = tl.copy()
    validate.drop_repeats(tl)
    pd.testing.assert_frame_equal(tl, before)


def test_unordered_input_is_handled():
    """`special_contexts` rewrites the time column, so cycle order is not guaranteed."""
    tl = frame([row(c, d) for c, d in [(3, 101), (0, 100), (2, 100), (1, 100)]])
    assert sorted(validate.drop_repeats(tl)["cycle"]) == [0, 3]


def test_passthrough_when_not_digitized():
    tl = frame([row(c, 100) for c in range(4)]).drop(columns=["value__digits"])
    pd.testing.assert_frame_equal(validate.drop_repeats(tl), tl)


# ---------------------------------------------------------------------------
# Interaction with the rest of the chain
# ---------------------------------------------------------------------------


def test_temporal_collision_resolves_before_value_comparison():
    """
    Two entries rounding to the same cycle: the later wins (`keep='last'`), and the
    repeat filter must compare against that survivor, not the discarded one.
    """
    tl = frame(
        [
            row(0, 100),
            row(1, 100),  # same cycle as the next row, superseded by it
            row(1, 200),
            row(2, 200),
            row(3, 300),
        ]
    )
    result = validate.drop_repeats(validate.drop_duplicates(tl))
    assert list(result["cycle"]) == [1, 3] or list(result["cycle"]) == [0, 1, 3]
    # the survivor at the collided cycle is the later entry
    assert result.loc[result["cycle"] == 1, "value__digits"].item() == 200
    # and cycle 2, a genuine repeat that is not a channel edge, is gone
    assert 2 not in list(result["cycle"])


def test_all_is_equivalent_to_the_chain():
    tl = frame([row(c, d) for c, d in [(0, 1), (1, 1), (2, 2), (3, 2)]])
    assert len(validate.all(tl)) == 3


def test_all_can_be_switched_off():
    tl = frame([row(c, d) for c, d in [(0, 1), (1, 1), (2, 2), (3, 2)]])
    assert len(validate.all(tl, do_drop_repeats=False)) == 4


def test_digital_channels_are_filtered_too():
    tl = frame(
        [
            row(c, d, variable="shutter_MOT", module=1, channel=11)
            for c, d in [(0, 1), (1, 1), (2, 0), (3, 0), (4, 1)]
        ]
    )
    assert list(validate.all(tl)["cycle"]) == [0, 2, 4]
