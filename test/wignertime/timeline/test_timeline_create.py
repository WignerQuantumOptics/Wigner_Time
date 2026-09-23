import pytest

from wignertime import timeline as tl
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import origin


@pytest.fixture
def df_simple():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0.0, ""],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def df__mixed():
    return wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [2.0, "AOM_imaging__V", 2.0, "blah"],
            [10.0, "AOM_repump", 1, "stuff"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline("AOM_imaging", 0.0, 0.0),
        tl._populate_timeline("AOM_imaging", [[0.0, 0.0]]),
    ],
)
def test_createSimple(input, df_simple):
    return wt_frame.assert_equal(input, df_simple)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[0.0, 1.0]]],
            ],
            context="init",
        ),
        tl._populate_timeline(
            [
                ["AOM_imaging", 0.0],
                ["AOM_imaging__V", 2],
                ["AOM_repump", 1.0],
            ],
            context="init",
            t=0.0,
        ),
        tl._populate_timeline(
            ["AOM_imaging", 0.0],
            ["AOM_imaging__V", 2],
            ["AOM_repump", 1.0],
            context="init",
            t=0.0,
        ),
        tl.create(
            context="init",
            t=0.0,
            AOM_imaging=0.0,
            AOM_imaging__V=2,
            AOM_repump=1.0,
        ),
    ],
)
def test_createDifferent(input, df):
    return wt_frame.assert_equal(input, df)


df_previous = wt_frame.new(
    [
        [0.0, "AOM_imaging", 0, "init"],
        [0.0, "AOM_imaging__V", 2.0, "init"],
        [0.0, "AOM_repump", 1, "init"],
    ],
    columns=["time", "variable", "value", "context"],
)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            AOM_repump=[10.0, 0.0, "important"], timeline=df_previous
        ),
        tl._populate_timeline(
            "AOM_repump", 10.0, 0.0, "important", timeline=df_previous
        ),
        # tl._populate_timeline(["AOM_repump", 10.0, 0.0, "important"], timeline=df_previous),
        tl._populate_timeline(
            ["AOM_repump", [10.0, 0.0, "important"]], timeline=df_previous
        ),
    ],
)
def test_createPrevious(input, df):
    df_check = wt_frame.new(
        [
            [0.0, "AOM_imaging", 0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1, "init"],
            [10.0, "AOM_repump", 0, "important"],
        ],
        columns=["time", "variable", "value", "context"],
    )

    return wt_frame.assert_equal(input, df_check)


@pytest.mark.parametrize(
    "input",
    [
        tl.create(
            AOM_imaging=[0.0, 0, "init"],
            AOM_imaging__V=[0.0, 2.0, "init"],
            AOM_repump=[0.0, 1, "init"],
        ),
        tl._populate_timeline(
            ["AOM_imaging", [0.0, 0, "init"]],
            ["AOM_imaging__V", [0.0, 2.0, "init"]],
            ["AOM_repump", [0.0, 1, "init"]],
        ),
        tl._populate_timeline(
            ["AOM_imaging__V", [0.0, 2.0]],
            ["AOM_repump", [0.0, 1]],
            timeline=tl._populate_timeline(
                ["AOM_imaging", [0.0, 0, "init"]],
            ),
        ),
        # tl._populate_timeline(
        #     ["AOM_imaging", 0.0, 0, "init"],
        #     ["AOM_imaging__V", 0.0, 2.0, "init"],
        #     ["AOM_repump", 0.0, 1, "init"],
        # ),
    ],
)
def test_createContext(input, df):
    return wt_frame.assert_equal(input, df)


def test_createInheritContext(df__mixed):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            ["AOM_imaging__V", [2.2, 3.0]],
            ["EOM_imaging__V", [2.3, 5.0]],
            timeline=df__mixed,
        ),
        wt_frame.new(
            [
                [0.0, "AOM_imaging", 0, "init"],
                [2.0, "AOM_imaging__V", 2.0, "blah"],
                [10.0, "AOM_repump", 1, "stuff"],
                [2.2, "AOM_imaging__V", 3.0, "stuff"],
                [2.3, "EOM_imaging__V", 5.0, "stuff"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_update_inherits_context_by_default(df__mixed):
    """
    `update`'s public default is `wt_config.CONTEXT__INFER`, not a bare `None` -- but
    it has to still *mean* the same thing a bare `None` always did: an unstated row
    inherits the previous timeline's context. A caller who writes nothing sees no
    change from before this sentinel existed (A8, 2026-09-24).
    """
    return wt_frame.assert_equal(
        tl.update(timeline=df__mixed, AOM_imaging__V=[2.2, 3.0], origin=None),
        wt_frame.new(
            [
                [0.0, "AOM_imaging", 0, "init"],
                [2.0, "AOM_imaging__V", 2.0, "blah"],
                [10.0, "AOM_repump", 1, "stuff"],
                [2.2, "AOM_imaging__V", 3.0, "stuff"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_update_context_none_turns_off_inheritance(df__mixed):
    """
    `context=None`, written explicitly, is the new "off" state (A8, 2026-09-24): the
    new row is left in the plain default context, the empty string, rather than
    inheriting `df__mixed`'s trailing "stuff" -- mirroring `origin=None`'s own "no
    resolution at all" meaning.
    """
    return wt_frame.assert_equal(
        tl.update(
            timeline=df__mixed, AOM_imaging__V=[2.2, 3.0], origin=None, context=None
        ),
        wt_frame.new(
            [
                [0.0, "AOM_imaging", 0, "init"],
                [2.0, "AOM_imaging__V", 2.0, "blah"],
                [10.0, "AOM_repump", 1, "stuff"],
                [2.2, "AOM_imaging__V", 3.0, ""],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


def test_update_context_infer_matches_the_default(df__mixed):
    """
    Writing the sentinel explicitly is indistinguishable from leaving `context`
    unstated -- both are `wt_config.CONTEXT__INFER`.
    """
    from wignertime import config as wt_config

    return wt_frame.assert_equal(
        tl.update(
            timeline=df__mixed,
            AOM_imaging__V=[2.2, 3.0],
            origin=None,
            context=wt_config.CONTEXT__INFER,
        ),
        tl.update(timeline=df__mixed, AOM_imaging__V=[2.2, 3.0], origin=None),
    )


def test_update_real_context_is_unaffected_by_the_sentinel_split(df__mixed):
    """
    A caller who states a real context directly is untouched by any of this -- exactly
    as today.
    """
    return wt_frame.assert_equal(
        tl.update(
            timeline=df__mixed,
            AOM_imaging__V=[2.2, 3.0],
            origin=None,
            context="named",
        ),
        wt_frame.new(
            [
                [0.0, "AOM_imaging", 0, "init"],
                [2.0, "AOM_imaging__V", 2.0, "blah"],
                [10.0, "AOM_repump", 1, "stuff"],
                [2.2, "AOM_imaging__V", 3.0, "named"],
            ],
            columns=["time", "variable", "value", "context"],
        ),
    )


###############################################################################
#                             Playing with origin                             #
###############################################################################


tline = tl._populate_timeline(
    [
        ["AOM_imaging", [[0.0, 0.0]]],
        ["other_thing", [[0.0, 0.0]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_repump", [[1.0, 1.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        tl._populate_timeline(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[1.0, 1.0]]],
                ["AOM_imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
            # `origin=[0.0, 0.0]` was a no-op here (no timeline to be relative to);
            # `create` no longer takes the argument at all.
        ),
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=[0.0],
        ),
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=0.0,
        ),
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM_imaging",
        ),
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM_imaging", "AOM_imaging"],
        ),
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin=["AOM_imaging", "other_thing"],
        ),
    ],
)
def test_createOrigin0(input):
    return wt_frame.assert_equal(
        input,
        tl._populate_timeline(
            [
                ["AOM_imaging", [[0.0, 0.0]]],
                ["other_thing", [[0.0, 0.0]]],
                ["AOM_imaging__V", [[0.0, 2]]],
                ["AOM_repump", [[1.0, 1.0]]],
                ["AOM_imaging__V", [[1.0, 10.0]]],
            ],
            context="init",
        ),
    )


tline2 = tl._populate_timeline(
    [
        ["AOM_imaging", [[1.0, 1.0]]],
        ["AOM_imaging__V", [[0.0, 2]]],
    ],
    context="init",
)

expected = tl._populate_timeline(
    [
        ["AOM_imaging", [[1.0, 1]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_imaging", [[2.0, 10.0]]],
        ["AOM_imaging__V", [[1.4, 5.0]]],
    ],
    context="init",
)
expected2 = tl._populate_timeline(
    [
        ["AOM_imaging", [[1.0, 1]]],
        ["AOM_imaging__V", [[0.0, 2]]],
        ["AOM_imaging", [[2.0, 11.0]]],
        ["AOM_imaging__V", [[1.4, 7.0]]],
    ],
    context="init",
)


@pytest.mark.parametrize(
    "input",
    [
        [
            "variable",
            expected,
        ],
        [
            ["variable"],
            expected,
        ],
    ],
)
def test_createOriginVariable(input):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            AOM_imaging=[1.0, 10.0],
            AOM_imaging__V=[1.4, 5.0],
            timeline=tline2,
            origin=input[0],
        ),
        input[1],
    )


@pytest.mark.parametrize(
    "input",
    [
        [
            ["variable", "variable"],
            expected2,
        ],
    ],
)
def test_createOriginVariableVariable(input):
    return wt_frame.assert_equal(
        tl._populate_timeline(
            AOM_imaging=[1.0, 10.0],
            AOM_imaging__V=[1.4, 5.0],
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
            ["AOM_imaging", [[0.0, 0.0]]],
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[1.0, 1.0]]],
        ],
        context="init",
    )
    print(
        tl._populate_timeline(
            AOM_imaging__V=[1.0, 10.0],
            timeline=tline,
            origin="AOM_imaging",
        )
    )


@pytest.mark.parametrize(
    "kwargs,instead",
    [
        ({"timeline": "anything"}, "update"),
        ({"origin": 0.0}, "update"),
    ],
)
def test_create_rejects_timeline_and_origin(kwargs, instead):
    """
    `create` starts a timeline from scratch, so neither argument means anything to it.

    Both would otherwise be swallowed by the open `**vtvc_dict` namespace and then
    re-bound by `_populate_timeline`, which does declare them -- reinstating silently
    the very arguments the signature exists to withhold.
    """
    with pytest.raises(TypeError, match=instead):
        tl.create(AOM_MOT=1, **kwargs)


def test_create_with_timeline_is_expressible_through_update():
    """
    Removing `timeline=` from `create` costs no capability: `update(origin=0.0)` places
    rows at absolute time, which is what passing a timeline to `create` always did.
    """
    previous = tl.create(AOM_MOT=1, t=0.0, context="init")

    return wt_frame.assert_equal(
        tl._populate_timeline(AOM_repump=0, t=10.0, timeline=previous),
        tl.update(AOM_repump=0, t=10.0, origin=0.0, timeline=previous),
    )
