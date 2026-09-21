"""
The deferred-function protocol: core functions return a timeline when given one and a callable otherwise, and those callables compose as siblings of a `stack` rather than by nesting.

The nesting mistake used to surface as an `AttributeError` about a missing dataframe attribute, far from its cause.
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.demo import full_experiment as demo


def deferred():
    """
    A representative deferred function, as returned by a core call with no `timeline`.
    """
    return tl.update(AOM_MOT=1)


@pytest.mark.parametrize(
    "name,call",
    [
        # `create` is absent on purpose: it has no `timeline` argument, so a deferred
        # function cannot reach it. See `test_create_rejects_timeline_and_origin`.
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


@pytest.mark.parametrize("bad", [[1, 2, 3], "yesterday", 7, {"a": 1}])
def test_non_timeline_argument_names_the_type(bad):
    """
    C4. A non-frame, non-callable used to fail far downstream on whatever dataframe
    attribute was touched first, naming neither the function nor the argument.
    """
    with pytest.raises(TypeError, match="where a timeline or `None` was expected"):
        tl.update(AOM_MOT=1, timeline=bad)


@pytest.mark.parametrize("stage", [demo.MOT, demo.pull_coils])
def test_stack_rejects_an_uncalled_stage(stage):
    """
    D17. `stack(timeline, MOT)` for `stack(timeline, MOT(...))` used to compose silently,
    binding the timeline to the stage's first parameter and returning a function. It was
    caught only when something followed it in the chain.
    """
    with pytest.raises(TypeError, match="rather than the result of calling it"):
        tl.stack(demo.init(), stage)


def test_stack_accepts_a_hand_written_transformer():
    """
    A plain `lambda tline: ...` carries no deferred tag, and must still compose. It is
    told apart from an uncalled stage by arity -- a transformer takes exactly one
    required positional argument, a stage written to convention takes none.
    """
    base = demo.init()
    assert len(tl.stack(base, lambda tline: tline)) == len(base)


def test_noop_survives_a_stack_that_forwards_keywords():
    """
    `noop` was `funcy.identity`, which raised on any keyword `stack` forwarded.
    """
    base = demo.init()
    assert len(tl.stack(base, tl.noop, context="anything")) == len(base)


@pytest.mark.parametrize(
    "f,args",
    [
        (tl.update, {"AOM_MOT": 1}),
        (tl.anchor, {}),
        (tl.ramp, {"coil__A": 2.0, "duration": 1.0}),
    ],
)
def test_a_frame_without_context_is_refused(f, args):
    """
    #28. `context` is a required column, and a frame lacking it used to raise a bare
    `KeyError: 'context'` from four frames down, naming neither function nor column.
    """
    import pandas as pd

    incomplete = pd.DataFrame(
        [[0.0, "coil__A", 1.0]], columns=["time", "variable", "value"]
    )
    with pytest.raises(TypeError, match="missing the column"):
        f(timeline=incomplete, **args) if args else f(1.0, timeline=incomplete)


def test_a_null_context_is_normalised_to_the_empty_string():
    """
    #28. The empty string is the minimum context. A hand-built frame carrying `None`
    used to propagate a real `None` into every row that inherited from it.
    """
    import pandas as pd

    hand = pd.DataFrame(
        [[0.0, "coil__A", 1.0, None]],
        columns=["time", "variable", "value", "context"],
    )
    out = tl.update(coil__A=2.0, timeline=hand)
    assert list(out["context"]) == ["", ""]
