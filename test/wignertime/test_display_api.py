"""
`wt.display` is a function of the main import, so the import needs no matplotlib, and the
missing package is named, with what to install, when a timeline is drawn.
"""

import inspect

import pytest

import wignertime.api.v09 as wt
from wignertime.io import display as wt_display


def _timeline():
    return wt.to_timeline(wt.update(shutter__MOT=1, time=0.0, context="init"))


def test_without_matplotlib_it_says_what_to_install(monkeypatch):
    real = wt_display.importlib.util.find_spec
    monkeypatch.setattr(
        wt_display.importlib.util,
        "find_spec",
        lambda name, *a: None if name == "matplotlib" else real(name, *a),
    )
    with pytest.raises(ModuleNotFoundError, match=r"wigner-time\[display\]") as caught:
        wt.display(_timeline())
    assert caught.value.name == "matplotlib"


def test_an_unknown_option_is_refused_before_drawing():
    with pytest.raises(TypeError, match="do_show"):
        wt.display(_timeline(), do_shw=False)


def test_it_draws_with_quantities(monkeypatch):
    pytest.importorskip("matplotlib")
    from wignertime.io.internal import drawing as drawing

    calls = []
    monkeypatch.setattr(drawing, "quantities", lambda *a, **k: calls.append((a, k)))
    timeline = _timeline()
    wt.display(timeline, ["shutter__MOT"], do_show=False)
    assert calls == [((timeline, ["shutter__MOT"]), {"do_show": False})]


def test_its_options_are_those_of_the_drawing():
    pytest.importorskip("matplotlib")
    from wignertime.io.internal import drawing as drawing

    names = list(inspect.signature(drawing.quantities).parameters)
    assert names[:2] == ["timeline", "variables"]
    assert tuple(names[2:]) == wt_display.OPTIONS__QUANTITIES
