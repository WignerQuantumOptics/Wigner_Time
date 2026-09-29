"""
The two slots of an `origin` pair admit different vocabularies.

The time slot asks *when*, so anything naming an instant serves. The value slot asks
*how much, of what*, and only a variable names a quantity -- `"anchor"`, `"last"` and a
context name each resolve to whichever variable happens to hold the row at that instant,
which answers in the wrong units. Settled by the maintainer on 2026-09-18, against the
`fig:origin` caption, which is defective here (KNOWN_ISSUES A7, A9).
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import origin as wt_origin


@pytest.fixture
def tline():
    """
    `coil__A` holds 2.0 through `stage1` (anchor at t=1.0) and 5.0 from t=1.5 through
    `stage2` (anchor at t=3.5 -- an `anchor` places itself relative to the previous one). `shutter__V` changes last, so it is what "last" finds.
    """
    return tl.to_timeline(
        tl.stack(
            tl.anchor(1.0, context="stage1"),
            tl.update(coil__A=5.0, t=1.5, context="stage2", origin=0.0),
            tl.update(shutter__V=1.0, t=2.0, context="stage2", origin=0.0),
            tl.anchor(2.5, context="stage2"),
        ),
        onto=tl.to_timeline(tl.update(coil__A=2.0, t=0.0, context="stage1")),
    )


# --- the value slot is narrow ------------------------------------------------


@pytest.mark.parametrize("label", [tl.ANCHOR, tl.LAST])
def test_reserved_time_words_are_refused_as_values(tline, label):
    with pytest.raises(ValueError, match="cannot serve as a VALUE origin"):
        tl.to_timeline(tl.update(coil__A=1.0, t=1.0, origin=[0.0, label]), onto=tline)


def test_context_name_is_refused_as_a_value(tline):
    """A context's last row may belong to any variable in it -- here, a shutter."""
    with pytest.raises(ValueError, match="cannot serve as a VALUE origin"):
        tl.to_timeline(
            tl.update(coil__A=1.0, t=1.0, origin=[0.0, "stage2"]), onto=tline
        )


def test_the_refusal_offers_the_pair_form(tline):
    """
    The narrowing loses no expressiveness, so the message says what to write instead:
    the time origin bounds the lookup, the value origin names what is looked up.
    """
    with pytest.raises(ValueError) as e:
        tl.to_timeline(
            tl.update(coil__A=1.0, t=1.0, origin=[0.0, "stage1"]), onto=tline
        )
    assert "origin=['stage1', VARIABLE]" in str(e.value)


def test_one_label_for_both_slots_must_satisfy_the_value_slot(tline):
    with pytest.raises(ValueError, match="cannot serve as a VALUE origin"):
        tl.to_timeline(
            tl.update(coil__A=1.0, t=1.0, origin=[tl.LAST, tl.LAST]), onto=tline
        )


# --- what the value slot still admits ----------------------------------------


def test_a_variable_name_remains_a_value_origin(tline):
    """Named explicitly, bounded by the time origin: `coil__A` held 2.0 at stage1."""
    new = tl.to_timeline(
        tl.update(coil__A=1.0, t=0.0, origin=["stage1", "coil__A"]), onto=tline
    )
    assert new.iloc[-1]["value"] == pytest.approx(3.0)


def test_variable_remains_a_value_origin(tline):
    new = tl.to_timeline(
        tl.update(coil__A=1.0, t=0.0, origin=["stage1", tl.VARIABLE]), onto=tline
    )
    assert new.iloc[-1]["value"] == pytest.approx(3.0)


def test_a_number_remains_a_value_origin(tline):
    new = tl.to_timeline(tl.update(coil__A=1.0, t=0.0, origin=[0.0, 10.0]), onto=tline)
    assert new.iloc[-1]["value"] == pytest.approx(11.0)


# --- the time slot is unchanged ----------------------------------------------


@pytest.mark.parametrize(
    "label,time__expected",
    [(tl.ANCHOR, 3.5), (tl.LAST, 3.5), ("stage1", 1.0), ("coil__A", 1.5)],
)
def test_the_time_slot_still_admits_everything(tline, label, time__expected):
    new = tl.to_timeline(
        tl.update(coil__A=1.0, t=0.0, origin=[label, None]), onto=tline
    )
    assert new.iloc[-1]["time"] == pytest.approx(time__expected)


def test_ramp_still_chains_on_its_own_default(tline):
    """`ramp`'s `[[ANCHOR, VARIABLE]]` is precisely a legal pair under the split."""
    new = tl.to_timeline(tl.ramp(coil__A=9.0, duration=0.5), onto=tline)
    points = new[new["function"].notna()][["time", "value"]].values.tolist()
    assert points == [[3.5, 5.0], [4.0, 9.0]]


# --- the words are tags, so a string is always a name (#158) ------------------


@pytest.mark.parametrize("word", ["anchor", "last", "variable"])
def test_a_context_may_be_named_after_a_word(word):
    """
    A9 refused such a name where it was written, because the string also meant a rule and
    the rule was resolved first, leaving the name unreachable. Since #158 the rules are
    tags and a string is only ever a name.
    """
    timeline = tl.to_timeline(tl.update(coil__A=1.0, context=word))
    assert list(timeline["context"]) == [word]


def test_a_context_named_after_a_word_is_what_the_word_refers_to():
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(coil__A=1.0, t=2.0, context="last"),
            tl.update(coil__A=2.0, t=5.0, context="stage"),
        )
    )
    placed = tl.to_timeline(tl.update(coil__A=3.0, t=0.5, origin="last"), onto=timeline)
    assert placed.iloc[-1]["time"] == pytest.approx(2.5)


@pytest.mark.parametrize("word", ["anchor", "last", "variable"])
def test_a_word_that_names_nothing_says_it_is_a_tag(tline, word):
    with pytest.raises(ValueError, match="tags since #158") as e:
        tl.to_timeline(tl.update(coil__A=1.0, origin=word), onto=tline)
    assert "origin=tl.{}".format(word.upper()) in str(e.value)


def test_the_reserved_words_have_one_source():
    """`_ORIGINS` is the vocabulary of the wider slot, not a separate list to drift."""
    assert wt_origin._ORIGINS == wt_origin._ORIGINS__TIME
    assert set(wt_origin._ORIGINS__VALUE) <= set(wt_origin._ORIGINS__TIME)


def test_the_tags_are_not_strings_and_stay_themselves():
    """Recognised with `is`, so they must survive what a stored default goes through."""
    import copy
    import pickle

    for tag in (tl.ANCHOR, tl.LAST, tl.VARIABLE):
        assert not isinstance(tag, str)
        assert repr(tag) == tag.name
        assert copy.deepcopy(tag) is tag
        assert pickle.loads(pickle.dumps(tag)) is tag
