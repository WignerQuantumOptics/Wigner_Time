"""
What `stack` and `cascade` accept, and what they refuse.

Both forward or route keywords, and the core functions read an unrecognised keyword as a
*variable name* -- so a misspelt one does not go unused, it becomes a row. `cascade` was
made strict in 2026-09-16 (C1); `stack` follows here (A5/#103).
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import util as wt_util


@pytest.fixture
def base():
    return tl.create(a__A=0.0, t=0.0, context="init")


def stage__named(timeline=None, duration=1.0):
    """A stage function, for `cascade` to route keywords to by name."""
    return tl.update(timeline=timeline, b__A=duration)


# --- A5: stack refuses a keyword no constituent can consume -------------------


def test_an_unplaceable_keyword_raises_rather_than_becoming_a_row(base):
    """
    The defect this replaces: `typo_duration` became a variable, the parameter meant to
    be set stayed at its default, and `remove_unconnected_variables` deleted the phantom
    at export without comment -- so nothing ever complained.
    """
    with pytest.raises(TypeError, match="could not place 1 keyword"):
        tl.stack(base, tl.update(a__A=1.0), context="MOT", typo_duration=3.0)


def test_the_refusal_says_what_could_have_been_placed(base):
    with pytest.raises(TypeError) as e:
        tl.stack(base, tl.update(a__A=1.0), typo_duration=3.0)
    assert "'typo_duration'" in str(e.value)
    assert "Placeable here: context, origin, t, timeline" in str(e.value)


def test_a_placeable_keyword_still_reaches_its_constituent(base):
    """The forwarding idiom itself, which the guard exists to protect rather than end."""
    result = tl.stack(base, tl.update(a__A=1.0), context="MOT")
    assert result.iloc[-1]["context"] == "MOT"
    assert "typo_duration" not in set(result["variable"])


def test_noop_does_not_switch_the_guard_off(base):
    """
    `noop` absorbs anything, so treating it as permissive would disable the check for any
    stack containing one -- and the lab's conditional stages put one in constantly. It is
    neutral instead: it neither vouches for a keyword nor objects to it.
    """
    assert wt_util.keywords_declared(tl.noop) is None
    with pytest.raises(TypeError, match="could not place"):
        tl.stack(base, tl.update(a__A=1.0), tl.noop, typo_duration=3.0)


def test_a_nested_stage_answers_for_the_stages_inside_it():
    """
    A constituent is an opaque closure by the time `stack` sees it, so each records what
    its chain can consume: `function__lambda` from the wrapped signature, `stack` as the
    union over its own constituents.
    """
    nested = tl.stack(tl.update(a__A=1.0))
    assert "context" in wt_util.keywords_declared(nested)
    assert "duration" not in wt_util.keywords_declared(nested)

    with_ramp = tl.stack(tl.update(a__A=1.0), tl.ramp(a__A=2.0, duration=1.0))
    assert "duration" in wt_util.keywords_declared(with_ramp)


def test_a_typo_behind_a_nested_stage_is_still_caught(base):
    with pytest.raises(TypeError, match="could not place"):
        tl.stack(base, tl.stack(tl.update(a__A=1.0)), typo_duration=3.0)


def test_constituents_that_cannot_say_leave_the_guard_off(base):
    """
    Where nothing records a set there is nothing to check against, and refusing on that
    basis would reject a legitimate hand-written transformer.
    """
    assert tl.stack(base, tl.as_deferred(lambda t, **kw: t), anything=1.0) is not None


# --- cascade refuses what is not a stage function -----------------------------


def test_cascade_refuses_a_timeline(base):
    """
    The mistake the two signatures make easy, `stack` taking a leading timeline where
    `cascade` does not. It used to fail as `AttributeError: 'DataFrame' object has no
    attribute '__name__'`, from the comprehension that keys stages by name.
    """
    with pytest.raises(TypeError, match="does not take a timeline"):
        tl.cascade(base, stage__named)


def test_cascade_refuses_a_stage_that_was_already_called():
    """The mirror of D17: `stack` takes stages called, `cascade` takes them bare."""
    with pytest.raises(TypeError, match="already been called"):
        tl.cascade(stage__named(duration=1.0))


def test_cascade_still_routes_by_prefix():
    def init(timeline=None):
        return tl.create(a__A=0.0, t=0.0, context="init")

    result = tl.cascade(init, stage__named, stage__named_duration=7.0)
    assert result.iloc[-1]["value"] == pytest.approx(7.0)
