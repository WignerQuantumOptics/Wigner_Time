"""
Stages: the core functions return one, stages compose as siblings of a `stack` rather
than by nesting, and `to_timeline` is what makes a timeline of one (#85).

The nesting mistake used to surface as an `AttributeError` about a missing dataframe
attribute, far from its cause.
"""

import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import util as wt_util
from wignertime.demo import full_experiment as demo


def deferred():
    """
    A representative deferred function, as returned by a core call with no `timeline`.
    """
    return tl.update(AOM_MOT=1)


@pytest.mark.parametrize(
    "name,call",
    [
        ("update", lambda f: tl.to_timeline(tl.update(), onto=f)),
        ("ramp", lambda f: tl.to_timeline(tl.ramp(coil__A=2.0, duration=1.0), onto=f)),
        ("anchor", lambda f: tl.to_timeline(tl.anchor(1.0), onto=f)),
        ("expand", lambda f: tl.expand(f, time_resolution=1e-4)),
    ],
)
def test_a_stage_where_a_timeline_belongs_is_named(name, call):
    """
    Nesting one call inside another names the mistake, rather than failing downstream.
    """
    with pytest.raises(TypeError, match="was given a stage where a timeline"):
        call(deferred())


@pytest.mark.parametrize(
    "f",
    [
        tl.update(AOM_MOT=1),
        tl.ramp(coil__A=2.0, duration=1.0),
        tl.anchor(1.0),
    ],
)
def test_every_core_function_returns_a_stage(f):
    assert wt_util.is_deferred(f)


def test_expand_takes_a_timeline_and_is_not_a_stage():
    """
    #85, C7 item 6. Unlike the functions that add rows, `expand` transforms the whole
    timeline it is given, so inside a `stack` it expanded every ramp built so far and the
    `expand` in `adwin.core.convert` then did nothing. It takes a table and returns one.
    """
    with pytest.raises(TypeError):
        tl.expand(time_resolution=1e-4)

    timeline = tl.expand(
        tl.to_timeline(
            tl.stack(
                tl.anchor(0.0),
                tl.ramp(coil__A=1.0, duration=1e-3, context="finalize"),
            ),
            onto=tl.to_timeline(tl.update(coil__A=0.0, t=0.0, context="init")),
        ),
        time_resolution=1e-4,
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
    with pytest.raises(TypeError, match="where a timeline was expected"):
        tl.to_timeline(tl.update(AOM_MOT=1), onto=bad)


@pytest.mark.parametrize("stage", [demo.MOT, demo.pull_coils])
def test_stack_rejects_an_uncalled_stage(stage):
    """
    D17. `stack(timeline, MOT)` for `stack(timeline, MOT(...))` used to compose silently,
    binding the timeline to the stage's first parameter and returning a function. It was
    caught only when something followed it in the chain.
    """
    with pytest.raises(TypeError, match="rather than the result of calling it"):
        tl.to_timeline(tl.stack(demo.init(), stage))


def test_stack_accepts_a_hand_written_transformer():
    """
    A plain `lambda tline: ...` carries no deferred tag, and must still compose. It is
    told apart from an uncalled stage by arity -- a transformer takes exactly one
    required positional argument, a stage written to convention takes none.
    """
    base = tl.to_timeline(demo.init())
    assert len(tl.to_timeline(tl.stack(lambda tline: tline), onto=base)) == len(base)


def test_noop_survives_a_stack_that_forwards_keywords():
    """
    `noop` was `funcy.identity`, which raised on any keyword `stack` forwarded.
    """
    base = tl.to_timeline(demo.init())
    assert len(tl.to_timeline(tl.stack(tl.noop, context="anything"), onto=base)) == len(
        base
    )


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
        tl.to_timeline(f(**args) if args else f(1.0), onto=incomplete)


@pytest.mark.parametrize("missing", [None, ""])
def test_a_table_with_a_row_lacking_a_context_is_refused(missing):
    """
    #156. Every row has a context. A hand-built frame carrying `None` or the empty string
    used to be normalised to the empty string as the minimum (#28), which every row
    appended after it then inherited. It is refused where it enters instead.
    """
    import pandas as pd

    hand = pd.DataFrame(
        [[0.0, "coil__A", 1.0, missing]],
        columns=["time", "variable", "value", "context"],
    )
    with pytest.raises(ValueError, match=r"1 row\(s\) have no context: coil__A"):
        tl.to_timeline(tl.update(coil__A=2.0), onto=hand)
