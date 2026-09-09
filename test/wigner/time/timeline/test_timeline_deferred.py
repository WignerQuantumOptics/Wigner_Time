"""
The deferred-function protocol: core functions return a timeline when given one and a callable otherwise, and those callables compose as siblings of a `stack` rather than by nesting.

The nesting mistake used to surface as an `AttributeError` about a missing dataframe attribute, far from its cause.
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame


def deferred():
    """
    A representative deferred function, as returned by a core call with no `timeline`.
    """
    return tl.update(AOM_MOT=1)


@pytest.mark.parametrize(
    "name,call",
    [
        ("create", lambda f: tl.create(AOM_MOT=1, timeline=f)),
        ("update", lambda f: tl.update(f)),
        ("ramp", lambda f: tl.ramp(f, coil__A=2.0, duration=1.0)),
        ("anchor", lambda f: tl.anchor(1.0, timeline=f)),
        ("expand", lambda f: tl.expand(f, time_resolution=1e-4)),
    ],
)
def test_deferred_function_as_timeline_raises(name, call):
    """
    Nesting one core call inside another names the mistake, rather than failing downstream.
    """
    with pytest.raises(TypeError, match="deferred function"):
        call(deferred())


@pytest.mark.parametrize(
    "f",
    [
        tl.update(AOM_MOT=1),
        tl.ramp(coil__A=2.0, duration=1.0),
        tl.anchor(1.0),
        tl.expand(time_resolution=1e-4),
    ],
)
def test_deferral_still_returns_a_callable(f):
    assert callable(f)


def test_expand_is_stackable():
    """
    `expand` belongs in a `stack` as its own element, after the `ramp` it expands.
    """
    timeline = tl.stack(
        tl.create(coil__A=0.0, t=0.0, context="init"),
        tl.anchor(0.0),
        tl.ramp(coil__A=1.0, duration=1e-3, context="finalize"),
        tl.expand(time_resolution=1e-4),
    )

    assert isinstance(timeline, wt_frame.CLASS)
    # Expansion is one-way: the marker column is consumed.
    assert "function" not in timeline.columns
    assert len(timeline[timeline["variable"] == "coil__A"]) > 2


def test_stack_still_accepts_a_leading_callable():
    """
    The guard must not catch `stack`/`cascade`, whose first argument is legitimately a function.
    """
    assert callable(tl.stack(tl.update(AOM_MOT=1), tl.anchor(1.0)))
