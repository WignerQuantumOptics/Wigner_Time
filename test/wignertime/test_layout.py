"""
#163: `wignertime.timeline` is a package of `build`, `query` and `internal`, and nothing is
re-exported between them, so each function has one name. Users go through the user API.
"""

import importlib
import types

import pytest

import wignertime.api.v09 as wt
import wignertime.timeline as timeline
from wignertime.timeline import build, query

BUILD = {
    "update", "ramp", "anchor", "stack", "cascade", "to_timeline", "expand",
    "noop", "as_deferred",
}  # fmt: skip
QUERY = {"previous", "context_information", "units"}


def _public(module):
    return {
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and not isinstance(value, types.ModuleType)
        and getattr(value, "__module__", module.__name__) == module.__name__
    } | ({"noop", "as_deferred"} & set(vars(module)))


def test_build_holds_the_main_functions_only():
    assert _public(build) == BUILD


def test_query_holds_the_queries():
    assert _public(query) == QUERY


def test_the_package_holds_nothing_itself():
    assert {n for n in vars(timeline) if not n.startswith("_")} <= {
        "build",
        "query",
        "ramp_function",
        "variable",
        "internal",
    }


@pytest.mark.parametrize(
    "name", ["build", "query", "ramp_function", "variable", "internal"]
)
def test_the_submodules_are_reachable(name):
    assert getattr(timeline, name) is importlib.import_module(
        "wignertime.timeline." + name
    )


@pytest.mark.parametrize(
    "name, says",
    [
        ("update", "wt.update"),
        ("stack", "timeline.build.stack"),
        ("ANCHOR", "wt.ANCHOR"),
        ("previous", "timeline.query.previous"),
        ("context_info", "wt.context_information"),
        ("create", "to_timeline"),
    ],
)
def test_an_old_name_says_where_it_went(name, says):
    with pytest.raises(AttributeError, match=says.replace(".", r"\.")):
        getattr(timeline, name)


def test_the_api_names_are_the_modules_own():
    assert wt.update is build.update and wt.previous is query.previous


@pytest.mark.parametrize(
    "name, now",
    [
        ("ramp_function", "wignertime.timeline.ramp_function"),
        ("variable", "wignertime.timeline.variable"),
        ("device", "wignertime.hardware.device"),
        ("conversion", "wignertime.hardware.conversion"),
        ("file", "wignertime.io.file"),
        ("display", "wignertime.io.display"),
    ],
)
def test_a_moved_module_says_where_it_went(name, now):
    with pytest.raises(ImportError, match=now.replace(".", r"\.")):
        exec("from wignertime import {}".format(name), {})
