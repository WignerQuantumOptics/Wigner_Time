"""
`wignertime.timeline.query`, reading a timeline back. `previous` is the lookup `origin` resolves
with, and the user's: one function, so they cannot disagree, ties included.
"""

import math
import re

import pytest

import wignertime.api.v09 as wt
from wignertime.timeline import query
import wignertime.timeline as tl
from wignertime.timeline import variable
from wignertime.timeline.internal import origin as wt_origin


def _timeline():
    return wt.to_timeline(
        wt.stack(
            wt.update(shutter__MOT=0, coil__MOT__A=0.0, time=0.0, context="init"),
            wt.update(shutter__MOT=1, time=1e-3, context="MOT"),
            wt.ramp(coil__MOT__A=-1.0, duration=10e-3),
            wt.update(shutter__MOT=0, time=20e-3, origin=0.0),
        )
    )


def test_the_last_entry_of_a_variable():
    row = wt.previous(_timeline(), "shutter__MOT")
    assert (row.time, row.value) == (pytest.approx(20e-3), 0.0)
    assert row["context"] == row.context == "MOT"


def test_bounded_in_time():
    row = wt.previous(_timeline(), "shutter__MOT", time__max=15e-3)
    assert (row.time, row.value) == (pytest.approx(1e-3), 1.0)


def test_the_last_entry_of_all():
    assert wt.previous(_timeline()).time == pytest.approx(20e-3)


def test_ties_go_to_the_row_written_last():
    timeline = wt.to_timeline(
        wt.update(coil__X__A=[[0.0, 1.0], [0.0, 2.0]], context="init")
    )
    assert wt.previous(timeline, "coil__X__A").value == 2.0


def test_it_is_where_a_ramp_would_start():
    timeline = _timeline()
    start = wt.previous(timeline, "coil__MOT__A").value
    after = wt.to_timeline(wt.ramp(coil__MOT__A=0.5, duration=1e-3), onto=timeline)
    added = after.iloc[len(timeline) :]
    assert added[added["variable"] == "coil__MOT__A"]["value"].iloc[0] == start


def test_the_final_state_counts_unless_bounded():
    timeline = wt.to_timeline(
        wt.stack(
            wt.update(shutter__MOT=1, time=0.0, context="init"),
            wt.update(shutter__MOT=0, time=math.inf, context="ADwin_Finish"),
        )
    )
    assert wt.previous(timeline, "shutter__MOT").time == math.inf
    assert wt.previous(timeline, "shutter__MOT", time__max=1.0).value == 1.0


def test_by_context():
    assert wt.previous(_timeline(), "init", column="context").time == 0.0


@pytest.mark.parametrize(
    "variable, time__max, message",
    [
        ("coil__Y__A", None, "No row with variable 'coil__Y__A' in this timeline"),
        (
            "shutter__MOT",
            -1.0,
            "No row with variable 'shutter__MOT' at or before time -1.0",
        ),
        (None, -1.0, "No row at or before time -1.0"),
    ],
)
def test_says_what_is_missing(variable, time__max, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        wt.previous(_timeline(), variable, time__max=time__max)


def test_refuses_an_empty_timeline():
    with pytest.raises(ValueError, match="the timeline is empty"):
        wt.previous(_timeline().iloc[:0])


def test_context_information_and_units():
    info = wt.context_information(_timeline())
    assert info["MOT"]["variables"] == {"shutter__MOT", "coil__MOT__A"}
    assert query.units(_timeline()) == {"A", "digital"}


@pytest.mark.parametrize(
    "module, name, new",
    [
        (tl, "previous", "previous"),
        (tl, "context_info", "context_information"),
        (variable, "units", "units"),
    ],
)
def test_the_old_names_say_where_they_went(module, name, new):
    with pytest.raises(AttributeError, match=r"timeline\.query\.{}`".format(new)):
        getattr(module, name)


def test_the_api_previous_is_the_one_the_origins_use():
    assert wt.previous is query.previous is wt_origin.wt_query.previous
