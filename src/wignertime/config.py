# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The settings a user may change, and nothing else.

    wt.config                                   # what they are, and their defaults
    wt.config.VARIABLE__REGEX = r"^...$"        # checked when it is set
    with wt.config.override(VARIABLE__REGEX=r"^...$"):
        ...                                     # changed for this block only
    wt.config.reset()                           # back to the defaults

A setting is read by the package each time it is used, so a change takes effect at once,
without reimporting. A value that cannot work is refused when it is set, and so is a name
that is not a setting, so a misspelt one does not pass unnoticed.
"""

import contextlib
import difflib
import re
import sys
import types

from wignertime.internal import tags as _tags

###############################################################################
#                   The settings                                              #
###############################################################################

VARIABLE__REGEX = re.compile(r"^([^_]+)__([^_]+(?:_[^_]+)*)(?:__([^_]+))?$")
"""
The naming convention for variables: `<device>__<UID>(__<unit>)`, as in
`coil__MOT_lower__A` and `shutter__MOT`. A name without `__<unit>` is a digital line.
`<device>` and `<unit>` contain no `_`, and `<UID>` may contain single ones.

A site that keeps a different convention may set its own, as a pattern or a string with
three groups – device, UID and unit (the last may match nothing). Connections and devices
are checked against it when they are made.
"""

ORIGIN__DEFAULTS = ((_tags.ANCHOR, None), (_tags.LAST, None))
"""
Where `update` and `anchor` place what they write when no `origin` is given: the first
of these that the timeline has, here the most recent anchor, else the latest entry. On a
timeline that has neither, absolute zero. Each entry is a (time, value) pair.
"""

ORIGIN__DEFAULTS__RAMP = ((_tags.ANCHOR, _tags.VARIABLE), (_tags.LAST, _tags.VARIABLE))
"""
The same for `ramp`. Its value slot is always `VARIABLE`: a ramp starts from where its
variable is.
"""

###############################################################################
#                   Checking, showing, resetting                              #
###############################################################################


def _check__regex(value):
    pattern = re.compile(value) if isinstance(value, str) else value
    if not isinstance(pattern, re.Pattern):
        raise TypeError(
            "VARIABLE__REGEX is a pattern or a string, not {}.".format(
                type(value).__name__
            )
        )
    if pattern.groups != 3:
        raise ValueError(
            "VARIABLE__REGEX needs three groups – device, UID and unit – and {!r} has"
            " {}.".format(pattern.pattern, pattern.groups)
        )
    return pattern


def _check__origins(name, value, value_slot=None):
    if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
        raise TypeError(
            "{} is a sequence of (time, value) pairs, not {!r}.".format(name, value)
        )
    entries = tuple(tuple(entry) for entry in value)
    if not entries:
        raise ValueError("{} needs at least one (time, value) pair.".format(name))
    for entry in entries:
        if len(entry) != 2:
            raise ValueError(
                "{} is a sequence of (time, value) pairs; {!r} is not a pair.".format(
                    name, entry
                )
            )
        if entry[0] is _tags.VARIABLE:
            raise ValueError(
                "{}: `VARIABLE` is a value reference, so it cannot be the time of"
                " {!r}.".format(name, entry)
            )
        if value_slot is not None and entry[1] is not value_slot:
            raise ValueError(
                "{}: a ramp starts from where its variable is, so every value slot is"
                " `VARIABLE`, and {!r} is not.".format(name, entry)
            )
    return entries


_SETTINGS = {
    "VARIABLE__REGEX": (VARIABLE__REGEX, _check__regex),
    "ORIGIN__DEFAULTS": (
        ORIGIN__DEFAULTS,
        lambda v: _check__origins("ORIGIN__DEFAULTS", v),
    ),
    "ORIGIN__DEFAULTS__RAMP": (
        ORIGIN__DEFAULTS__RAMP,
        lambda v: _check__origins("ORIGIN__DEFAULTS__RAMP", v, _tags.VARIABLE),
    ),
}

# Names this module answered to before it held only settings (2026-10-01). They still
# resolve, so that old code and old pickles do, but are not listed and cannot be rebound.
_FIXED = {
    "LABEL__ANCHOR": _tags.LABEL__ANCHOR,
    "INFER": _tags.INFER,
    "ORIGIN__INFER": _tags.ORIGIN__INFER,
    "CONTEXT__INFER": _tags.CONTEXT__INFER,
    "Origin": _tags.Origin,
    "ANCHOR": _tags.ANCHOR,
    "LAST": _tags.LAST,
    "VARIABLE": _tags.VARIABLE,
    "wtlog": _tags.wtlog,
}
globals().update(_FIXED)


def _shown(value):
    return value.pattern if isinstance(value, re.Pattern) else repr(value)


def show():
    """Prints the settings, and marks those that differ from their defaults."""
    print(_describe())


def _describe():
    module = sys.modules[__name__]
    width = max(map(len, _SETTINGS))
    lines = ["wignertime settings (wt.config):"]
    for name, (default, _) in _SETTINGS.items():
        value = getattr(module, name)
        lines.append(
            "  {:<{}}  {}{}".format(
                name,
                width,
                _shown(value),
                "" if value == default else "   (default {})".format(_shown(default)),
            )
        )
    return "\n".join(lines)


def reset(*names):
    """Puts the named settings, or all of them, back to their defaults."""
    module = sys.modules[__name__]
    for name in names or _SETTINGS:
        _require_setting(name)
        setattr(module, name, _SETTINGS[name][0])


@contextlib.contextmanager
def override(**settings):
    """
    Changes settings for the duration of a `with` block, and restores them after it, also
    when the block raises. Every value is checked before any is changed.
    """
    module = sys.modules[__name__]
    for name in settings:
        _require_setting(name)
    checked = {name: _SETTINGS[name][1](value) for name, value in settings.items()}
    before = {name: getattr(module, name) for name in checked}
    for name, value in checked.items():
        setattr(module, name, value)
    try:
        yield module
    finally:
        for name, value in before.items():
            setattr(module, name, value)


def _require_setting(name):
    if name in _SETTINGS:
        return
    if name in _FIXED:
        raise AttributeError(
            "`{}` is fixed by the package, not a setting. The settings are {}.".format(
                name, ", ".join(_SETTINGS)
            )
        )
    close = difflib.get_close_matches(name, _SETTINGS, n=1)
    raise AttributeError(
        "`{}` is not a setting.{} The settings are {}.".format(
            name,
            " Did you mean `{}`?".format(close[0]) if close else "",
            ", ".join(_SETTINGS),
        )
    )


__all__ = [*_SETTINGS, "show", "reset", "override"]


class _Config(types.ModuleType):
    """This module, with its settings checked when they are set."""

    def __setattr__(self, name, value):
        if not name.startswith("_"):
            _require_setting(name)
            value = _SETTINGS[name][1](value)
        super().__setattr__(name, value)

    def __dir__(self):
        return sorted(__all__)

    def __repr__(self):
        return _describe()


sys.modules[__name__].__class__ = _Config
