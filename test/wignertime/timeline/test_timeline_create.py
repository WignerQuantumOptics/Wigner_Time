import pytest

from wignertime import config as wt_config
from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import origin


@pytest.fixture
def df_simple():
    return wt_frame.new(
        [
            [0.0, "AOM__imaging", 0.0, "s"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return wt_frame.new(
        [
            [0.0, "AOM__imaging", 0, "init"],
            [0.0, "AOM__imaging__V", 2.0, "init"],
            [0.0, "AOM__repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df__mixed():
    return wt_frame.new(
        [
            [0.0, "AOM__imaging", 0, "init"],
            [2.0, "AOM__imaging__V", 2.0, "blah"],
            [10.0, "AOM__repump", 1, "stuff"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline("AOM__imaging", 0.0, 0.0, context="s"),
        tl._populate_timeline("AOM__imaging", [[0.0, 0.0]], context="s"),
    ],
)
def test_createSimple(input, df_simple):
    return wt_frame.assert_equal(input, df_simple)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            [
                ["AOM__imaging", [[0.0, 0.0]]],
                ["AOM__imaging__V", [[0.0, 2]]],
                ["AOM__repump", [[0.0, 1.0]]],
            ],
            context="init",
        ),
        tl._populate_timeline(
            [
                ["AOM__imaging", 0.0],
                ["AOM__imaging__V", 2],
                ["AOM__repump", 1.0],
            ],
            context="init",
            time=0.0,
        ),
        tl._populate_timeline(
            ["AOM__imaging", 0.0],
            ["AOM__imaging__V", 2],
            ["AOM__repump", 1.0],
            context="init",
            time=0.0,
        ),
        tl.to_timeline(
            tl.update(
                context="init",
                time=0.0,
                AOM__imaging=0.0,
                AOM__imaging__V=2,
                AOM__repump=1.0,
            )
        ),
    ],
)
def test_createDifferent(input, df):
    return wt_frame.assert_equal(input, df)


df_previous = wt_frame.new(
    [
        [0.0, "AOM__imaging", 0, "init"],
        [0.0, "AOM__imaging__V", 2.0, "init"],
        [0.0, "AOM__repump", 1, "init"],
    ],
    columns=["time", "variable", "value", "context"],
)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            AOM__repump=[10.0, 0.0, "important"], timeline=df_previous
        ),
        tl._populate_timeline(
            "AOM__repump", 10.0, 0.0, "important", timeline=df_previous
        ),
        # tl._populate_timeline(["AOM__repump", 10.0, 0.0, "important"], timeline=df_previous),
        tl._populate_timeline(
            ["AOM__repump", [10.0, 0.0, "important"]], timeline=df_previous
        ),
    ],
)
def test_createPrevious(input, df):
    df_check = wt_frame.new(
        [
            [0.0, "AOM__imaging", 0, "init"],
            [0.0, "AOM__imaging__V", 2.0, "init"],
            [0.0, "AOM__repump", 1, "init"],
            [10.0, "AOM__repump", 0, "important"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return wt_frame.assert_equal(input, df_check)


@pytest.mark.parametrize(
    "input",
    [
        tl.to_timeline(
            tl.update(
                AOM__imaging=[0.0, 0, "init"],
                AOM__imaging__V=[0.0, 2.0, "init"],
                AOM__repump=[0.0, 1, "init"],
            )
        ),
        tl._populate_timeline(
            ["AOM__imaging", [0.0, 0, "init"]],
            ["AOM__imaging__V", [0.0, 2.0, "init"]],
            ["AOM__repump", [0.0, 1, "init"]],
        ),
        tl._populate_timeline(
            ["AOM__imaging__V", [0.0, 2.0]],
            ["AOM__repump", [0.0, 1]],
            timeline=tl._populate_timeline(
                ["AOM__imaging", [0.0, 0, "init"]],
            ),
        ),
        # tl._populate_timeline(
        #     ["AOM__imaging", 0.0, 0, "init"],
        #     ["AOM__imaging__V", 0.0, 2.0, "init"],
        #     ["AOM__repump", 0.0, 1, "init"],
        # ),
    ],
)
def test_createContext(input, df):
    return wt_frame.assert_equal(input, df)


def test_createInheritContext(df__mixed):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            ["AOM__imaging__V", [2.2, 3.0]],
            ["EOM_imaging__V", [2.3, 5.0]],
            timeline=df__mixed,
        ),
        wt_frame.new(
            [
                [0.0, "AOM__imaging", 0, "init"],
                [2.0, "AOM__imaging__V", 2.0, "blah"],
                [10.0, "AOM__repump", 1, "stuff"],
                [2.2, "AOM__imaging__V", 3.0, "stuff"],
                [2.3, "EOM_imaging__V", 5.0, "stuff"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_update_inherits_context_by_default(df__mixed):
    """
    `update`'s default for `context` is `wt_config.INFER`: an unstated row inherits the
    latest context of the timeline it joins. `origin=0.0` keeps the times as written.
    """
    return wt_frame.assert_equal(
        tl.to_timeline(
            tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0), onto=df__mixed
        ),
        wt_frame.new(
            [
                [0.0, "AOM__imaging", 0, "init"],
                [2.0, "AOM__imaging__V", 2.0, "blah"],
                [10.0, "AOM__repump", 1, "stuff"],
                [2.2, "AOM__imaging__V", 3.0, "stuff"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


@pytest.mark.parametrize("context", [None, wt_config.INFER])
def test_update_context_none_and_infer_match_the_default(df__mixed, context):
    """
    Writing `None` or the marker is indistinguishable from leaving `context` unstated,
    so a stage that takes `context=None` and passes it on inherits as if it had passed
    nothing (#142).
    """
    return wt_frame.assert_equal(
        tl.to_timeline(
            tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0, context=context),
            onto=df__mixed,
        ),
        tl.to_timeline(
            tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0), onto=df__mixed
        ),
    )


def test_update_refuses_an_empty_context(df__mixed):
    """
    #156. `context=""` used to switch inheritance off, leaving the row without a context.
    Every row has one, stated or inherited, so there is nothing to switch off.
    """
    with pytest.raises(ValueError, match="is not a context"):
        tl.to_timeline(
            tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0, context=""),
            onto=df__mixed,
        )


# --- #156: every row has a context ------------------------------------------


def test_the_first_rows_of_a_timeline_must_name_a_context():
    """
    Nothing precedes them to inherit a context from. This is #145's option 2, which
    now holds for every row rather than for `create` alone.
    """
    with pytest.raises(ValueError, match="Every row needs a context.*AOM__MOT"):
        tl.to_timeline(tl.update(AOM__MOT=1, time=0.0))


def test_a_row_stating_its_own_context_needs_none_from_the_call():
    frame = tl.to_timeline(
        tl.update(AOM__MOT=[0.0, 1, "init"], shutter__MOT=[0.0, 0, "init"])
    )
    assert set(wt_frame.column(frame, "context")) == {"init"}


def test_one_row_without_a_context_is_enough_to_refuse():
    with pytest.raises(ValueError, match="none: shutter__MOT"):
        tl.to_timeline(tl.update(AOM__MOT=[0.0, 1, "init"], shutter__MOT=0))


def test_onto_an_empty_table_the_refusal_is_about_the_context():
    """
    N4 (#145). `update` onto an empty table used to fail in the *origin* lookup, with the
    advice to give `origin=0.0` -- which gave the same error again, because what was
    missing was the context.
    """
    empty = wt_frame.cast(wt_frame.new([], columns=list(tl._SCHEMA.keys())), tl._SCHEMA)
    for origin in (wt_config.INFER, 0.0):
        with pytest.raises(ValueError, match="Every row needs a context") as e:
            tl.to_timeline(tl.update(AOM__MOT=1, origin=origin), onto=empty)
        assert "origin=0.0" not in str(e.value)

    named = tl.to_timeline(
        tl.update(AOM__MOT=1, context="init", origin=0.0), onto=empty
    )
    assert list(wt_frame.column(named, "context")) == ["init"]


def test_update_real_context_is_taken_as_written(df__mixed):
    return wt_frame.assert_equal(
        tl.to_timeline(
            tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0, context="named"),
            onto=df__mixed,
        ),
        wt_frame.new(
            [
                [0.0, "AOM__imaging", 0, "init"],
                [2.0, "AOM__imaging__V", 2.0, "blah"],
                [10.0, "AOM__repump", 1, "stuff"],
                [2.2, "AOM__imaging__V", 3.0, "named"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_a_context_named_INFER_is_an_ordinary_context(df__mixed):
    """
    The default is an object, not the string, so the word itself is free as a name
    (#142).
    """
    new = tl.to_timeline(
        tl.update(AOM__imaging__V=[2.2, 3.0], origin=0.0, context="INFER"),
        onto=df__mixed,
    )
    assert wt_frame.column(new, "context")[-1] == "INFER"


###############################################################################
#                             Playing with origin                             #
###############################################################################


tline = tl._populate_timeline(
    [
        ["AOM__imaging", [[0.0, 0.0]]],
        ["other_thing", [[0.0, 0.0]]],
        ["AOM__imaging__V", [[0.0, 2]]],
        ["AOM__repump", [[1.0, 1.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            [
                ["AOM__imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM__imaging__V", [[0.0, 2]]],
                ["AOM__repump", [[1.0, 1.0]]],
                ["AOM__imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
            # `origin=[0.0, 0.0]` was a no-op here (no timeline to be relative to);
            # `create` no longer takes the argument at all.
        ),
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=[0.0],
        ),
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=0.0,
        ),
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM__imaging",
        ),
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM__imaging", "AOM__imaging"],
        ),
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM__imaging", "other_thing"],
        ),
    ],
)
def test_createOrigin0(input):
    return wt_frame.assert_equal(
        input,
        tl._populate_timeline(
            [
                ["AOM__imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM__imaging__V", [[0.0, 2]]],
                ["AOM__repump", [[1.0, 1.0]]],
                ["AOM__imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
        ),
    )


tline2 = tl._populate_timeline(
    [
        ["AOM__imaging", [[1.0, 1.0]]],
        ["AOM__imaging__V", [[0.0, 2]]],
    ],
    context="init",
)

expected = tl._populate_timeline(
    [
        ["AOM__imaging", [[1.0, 1]]],
        ["AOM__imaging__V", [[0.0, 2]]],
        ["AOM__imaging", [[2.0, 10.0]]],
        ["AOM__imaging__V", [[1.4, 5.0]]],
    ],
    context="init",
)
expected2 = tl._populate_timeline(
    [
        ["AOM__imaging", [[1.0, 1]]],
        ["AOM__imaging__V", [[0.0, 2]]],
        ["AOM__imaging", [[2.0, 11.0]]],
        ["AOM__imaging__V", [[1.4, 7.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        [
            tl.VARIABLE,
            expected,
        ],
        [
            [tl.VARIABLE],
            expected,
        ],
    ],
)
def test_createOriginVariable(input):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            AOM__imaging=[1.0, 10.0],
            AOM__imaging__V=[1.4, 5.0],
            timeline=tline2,
            origin=input[0],
        ),
        input[1],
    )


@pytest.mark.parametrize(
    "input",
    [
        [
            [tl.VARIABLE, tl.VARIABLE],
            expected2,
        ],
    ],
)
def test_createOriginVariableVariable(input):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            AOM__imaging=[1.0, 10.0],
            AOM__imaging__V=[1.4, 5.0],
            timeline=tline2,
            origin=input[0],
        ),
        input[1],
    )


if __name__ == "__main__":
    import importlib as lib

    lib.reload(tl)
    lib.reload(origin)

    tline = tl._populate_timeline(
        [
            ["AOM__imaging", [[0.0, 0.0]]],
            ["AOM__imaging__V", [[0.0, 2]]],
            ["AOM__repump", [[1.0, 1.0]]],
        ],
        context="init",
    )
    print(
        tl._populate_timeline(
            AOM__imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM__imaging",
        )
    )


def test_create_is_gone_and_says_what_replaced_it():
    """
    #85. A `stack` composes stages only, so the one core function that could only begin
    one has nothing left to do: the first rows are an `update` on an empty timeline.
    """
    with pytest.raises(AttributeError, match=r"to_timeline\(update"):
        tl.create


def test_the_first_rows_are_placed_in_absolute_time():
    """
    On an empty timeline there is nothing to be relative to, so an `update` places its
    rows where `create` did, and the origin chain falls to zero without a warning.
    """
    return wt_frame.assert_equal(
        tl.to_timeline(tl.update(AOM__repump=0, time=10.0, context="init")),
        tl._populate_timeline(AOM__repump=0, time=10.0, context="init"),
    )
