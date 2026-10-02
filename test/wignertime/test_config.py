"""
`config` holds the settings a user may change and nothing else; it checks a value when it
is set, refuses a name that is not a setting, and configures no logging on import.
"""

import pickle
import re
import subprocess
import sys

import pytest

import wignertime.api.v0_9 as wt
from wignertime.internal import dataframe as wt_frame
from wignertime import config
from wignertime.timeline import variable
from wignertime.internal import tags

SETTINGS = ["ORIGIN__DEFAULTS", "ORIGIN__DEFAULTS__RAMP", "VARIABLE__REGEX"]


@pytest.fixture(autouse=True)
def _defaults():
    yield
    config.reset()


def test_only_the_settings_are_listed():
    assert dir(wt.config) == sorted([*SETTINGS, "override", "reset", "show"])


def test_it_shows_the_settings_and_what_differs():
    wt.config.ORIGIN__DEFAULTS = [[wt.LAST, None]]
    shown = repr(wt.config)
    assert all(name in shown for name in SETTINGS)
    assert shown.count("(default") == 1


def test_a_misspelt_setting_is_refused_with_the_right_one():
    with pytest.raises(AttributeError, match="Did you mean `VARIABLE__REGEX`"):
        wt.config.VARIABLE_REGEX = r"^(a)__(b)(?:__(c))?$"
    assert not hasattr(config, "VARIABLE_REGEX")


@pytest.mark.parametrize("name", ["LABEL__ANCHOR", "INFER", "ANCHOR", "Origin"])
def test_fixed_names_still_resolve_but_cannot_be_rebound(name):
    assert getattr(wt.config, name) is getattr(tags, name)
    with pytest.raises(AttributeError, match="fixed by the package"):
        setattr(wt.config, name, "x")


def test_the_regex_is_compiled_and_checked_when_set():
    wt.config.VARIABLE__REGEX = r"^(nothing)__(x)(?:__(y))?$"
    assert isinstance(config.VARIABLE__REGEX, re.Pattern)
    assert not variable.is_valid("coil__MOT__A")
    with pytest.raises(ValueError, match="three groups"):
        wt.config.VARIABLE__REGEX = r"^nothing$"
    with pytest.raises(re.error):
        wt.config.VARIABLE__REGEX = r"^(unclosed"
    with pytest.raises(TypeError):
        wt.config.VARIABLE__REGEX = 3


@pytest.mark.parametrize(
    "name, value, message",
    [
        ("ORIGIN__DEFAULTS", [], "at least one"),
        ("ORIGIN__DEFAULTS", "anchor", "sequence of"),
        ("ORIGIN__DEFAULTS", [[wt.ANCHOR]], "not a pair"),
        ("ORIGIN__DEFAULTS", [[wt.VARIABLE, None]], "value reference"),
        ("ORIGIN__DEFAULTS__RAMP", [[wt.LAST, None]], "every value slot"),
    ],
)
def test_origin_defaults_are_checked_when_set(name, value, message):
    before = getattr(config, name)
    with pytest.raises((TypeError, ValueError), match=message):
        setattr(wt.config, name, value)
    assert getattr(config, name) == before


def test_origin_defaults_cannot_be_changed_in_place():
    wt.config.ORIGIN__DEFAULTS = [[wt.LAST, None]]
    assert config.ORIGIN__DEFAULTS == ((wt.LAST, None),)
    with pytest.raises(AttributeError):
        config.ORIGIN__DEFAULTS.append((wt.ANCHOR, None))


def test_a_changed_default_is_the_one_used():
    stage = wt.stack(
        wt.update(x__y=0, time=0.0, context="init"),
        wt.anchor(1.0, context="MOT"),
        wt.update(x__y=1, time=5.0, origin=0.0),
        wt.update(x__y=2, time=0.5),
    )
    assert wt_frame.column(wt.to_timeline(stage), "time")[-1] == 1.5
    with wt.config.override(ORIGIN__DEFAULTS=[[wt.LAST, None]]):
        assert wt_frame.column(wt.to_timeline(stage), "time")[-1] == 5.5


def test_override_restores_also_when_the_block_raises():
    before = config.VARIABLE__REGEX
    with pytest.raises(RuntimeError):
        with wt.config.override(VARIABLE__REGEX=r"^(a)__(b)(?:__(c))?$"):
            assert config.VARIABLE__REGEX != before
            raise RuntimeError
    assert config.VARIABLE__REGEX is before


def test_override_checks_everything_before_changing_anything():
    before = config.VARIABLE__REGEX
    with pytest.raises(ValueError):
        with wt.config.override(
            VARIABLE__REGEX=r"^(a)__(b)(?:__(c))?$", ORIGIN__DEFAULTS=[]
        ):
            pass
    assert config.VARIABLE__REGEX is before


def test_reset():
    wt.config.ORIGIN__DEFAULTS = [[wt.LAST, None]]
    wt.config.reset("ORIGIN__DEFAULTS")
    assert config.ORIGIN__DEFAULTS == ((wt.ANCHOR, None), (wt.LAST, None))
    with pytest.raises(AttributeError, match="not a setting"):
        wt.config.reset("TIME_RESOLUTION")


def test_an_old_pickle_of_infer_still_loads():
    old = b"cwignertime.config\nINFER\n."  # as pickled before 2026-10-01
    assert pickle.loads(old) is wt.INFER
    assert pickle.loads(pickle.dumps(wt.INFER)) is wt.INFER


def _run(code):
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    return result


def test_importing_configures_no_logging():
    out = _run(
        "import logging, wignertime.api.v0_9\n"
        "root = logging.getLogger()\n"
        "print(len(root.handlers), root.level)\n"
    ).stdout.split()
    assert out == ["0", str(30)]


def test_warnings_are_still_seen_without_any_logging_configured():
    err = _run(
        "from wignertime.internal.tags import wtlog\n"
        "wtlog.warning('heard')\n"
        "wtlog.info('not heard')\n"
    ).stderr
    assert "heard" in err and "not heard" not in err
