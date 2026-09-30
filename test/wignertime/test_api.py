"""
#163: `wignertime.api.v1` is the user API, a designed list rather than whatever happens to
be public in the package. These tests pin that list, so that changing it is a decision
someone makes on purpose, in this file, and not a side effect of work elsewhere.
"""

import importlib
import os
import subprocess
import sys

import pytest

import wignertime.api.v1 as wt

# The API of version 1. Adding a name is a new promise; removing or renaming one breaks
# every user of v1 and belongs in a new version instead.
V1 = {
    "wignertime.api.v1": {
        "update", "ramp", "anchor", "stack", "cascade", "to_timeline", "expand",
        "INFER", "ANCHOR", "LAST", "VARIABLE",
        "tanh", "linear", "with_points",
        "devices", "function_from_file",
        "save", "load",
        "config",
    },
    "wignertime.api.v1.adwin": {
        "connections", "link_device", "read_cycle_period", "convert", "upload",
        "run", "start", "wait", "running", "Upload", "Run", "LostEvents", "PeriodRefused",
    },
    "wignertime.api.v1.adwin.console": {
        "panel", "configure", "create_UI", "set_value", "readback", "final_state",
        "jumps", "health", "Console", "Jump", "Health", "OutputsOwned",
    },
    "wignertime.api.v1.adwin.adc": {"run", "arm", "read", "Window", "Samples"},
    "wignertime.api.v1.display": {"quantities"},
}  # fmt: skip

_NEEDS = {
    "wignertime.api.v1.adwin": "ADwin",
    "wignertime.api.v1.adwin.console": "ipywidgets",
    "wignertime.api.v1.adwin.adc": "ADwin",
    "wignertime.api.v1.display": "matplotlib",
}


def _module(name):
    if name in _NEEDS:
        pytest.importorskip(_NEEDS[name])
    return importlib.import_module(name)


@pytest.mark.parametrize("name", sorted(V1))
def test_the_api_is_exactly_the_list(name):
    assert set(_module(name).__all__) == V1[name]


@pytest.mark.parametrize("name", sorted(V1))
def test_nothing_else_is_in_view(name):
    """
    Nothing the module imported for itself is reachable under a public name: the module's
    own namespace holds the API, and the optional namespaces below it once loaded.
    `dir`, which tab completion reads, shows the API and those namespaces.
    """
    module = _module(name)
    optional = set(getattr(module, "_OPTIONAL", ()))
    public = {n for n in vars(module) if not n.startswith("_")}
    assert V1[name] <= public <= V1[name] | optional
    assert {n for n in dir(module) if not n.startswith("_")} == V1[name] | optional


@pytest.mark.parametrize("name", sorted(V1))
def test_every_name_is_the_packages_own(name):
    """The API adds no behaviour: `wt.update` is `wignertime.timeline.update`."""
    module = _module(name)
    for attribute in V1[name]:
        value = getattr(module, attribute)
        home = getattr(value, "__module__", None)
        if home is not None and not isinstance(value, type(sys)):
            assert home.startswith("wignertime.") and not home.startswith(
                "wignertime.api"
            ), f"{name}.{attribute} is defined in {home}"


def test_the_main_import_needs_no_optional_package():
    code = (
        "import sys, wignertime.api.v1 as wt\n"
        "print(sorted(m for m in ('ADwin', 'matplotlib', 'ipywidgets') if m in sys.modules))\n"
    )
    env = dict(os.environ)
    env.pop("WIGNERTIME_STRICT_LOG", None)
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_config_is_the_module_the_package_reads(monkeypatch):
    """
    A setting changed through `wt.config` must be the one the package reads, so the API
    hands out the module, not copies of its values.
    """
    from wignertime import config, variable

    assert wt.config is config
    assert variable.is_valid("coil__MOT__A")
    monkeypatch.setattr(wt.config, "VARIABLE__REGEX", r"^nothing$")
    assert not variable.is_valid("coil__MOT__A")


# What the paper, the README and the demo use, and where v1 has it.
_PAPER = [
    ("wignertime.timeline", "update", "wignertime.api.v1", "update"),
    ("wignertime.timeline", "ramp", "wignertime.api.v1", "ramp"),
    ("wignertime.timeline", "stack", "wignertime.api.v1", "stack"),
    ("wignertime.timeline", "anchor", "wignertime.api.v1", "anchor"),
    ("wignertime.timeline", "to_timeline", "wignertime.api.v1", "to_timeline"),
    ("wignertime.timeline", "cascade", "wignertime.api.v1", "cascade"),
    ("wignertime.timeline", "ANCHOR", "wignertime.api.v1", "ANCHOR"),
    ("wignertime.timeline", "LAST", "wignertime.api.v1", "LAST"),
    ("wignertime.timeline", "VARIABLE", "wignertime.api.v1", "VARIABLE"),
    ("wignertime.device", "new", "wignertime.api.v1", "devices"),
    ("wignertime.conversion", "function_from_file", "wignertime.api.v1", "function_from_file"),
    ("wignertime.ramp_function", "tanh", "wignertime.api.v1", "tanh"),
    ("wignertime.file", "save", "wignertime.api.v1", "save"),
    ("wignertime.adwin.connection", "new", "wignertime.api.v1.adwin", "connections"),
    ("wignertime.adwin.core", "link_device", "wignertime.api.v1.adwin", "link_device"),
    ("wignertime.adwin.core", "convert", "wignertime.api.v1.adwin", "convert"),
    ("wignertime.adwin.core", "upload", "wignertime.api.v1.adwin", "upload"),
    ("wignertime.adwin.core", "run", "wignertime.api.v1.adwin", "run"),
    ("wignertime.adwin.display", "quantities", "wignertime.api.v1.display", "quantities"),
]  # fmt: skip


@pytest.mark.parametrize("home, name, api, alias", _PAPER, ids=lambda x: str(x))
def test_what_the_paper_uses_is_in_v1(home, name, api, alias):
    assert getattr(_module(api), alias) is getattr(importlib.import_module(home), name)


def test_the_docstring_example_builds_a_timeline():
    initial = wt.update(shutter__MOT=0, coil__MOT__A=0.0, time=0.0, context="init")
    MOT = wt.stack(
        wt.anchor(1e-3, context="MOT"),
        wt.update(shutter__MOT=1),
        wt.ramp(coil__MOT__A=-1.0, duration=10e-3, function=wt.tanh),
    )
    timeline = wt.to_timeline(wt.stack(initial, MOT))
    assert list(timeline["context"]) == ["init", "init", "MOT", "MOT", "MOT", "MOT"]
    assert list(timeline["time"]) == pytest.approx([0.0, 0.0, 1e-3, 1e-3, 1e-3, 11e-3])
