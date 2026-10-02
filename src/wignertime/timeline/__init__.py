# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Timelines: building them (`timeline.build`), reading them back (`timeline.query`), and
what those share (`timeline.internal`, private).

Users reach all of it through the user API, `import wignertime.api.v0_9 as wt`; this
package re-exports nothing, so there is one name for each function.
"""

import importlib as _importlib

_SUBMODULES = ("build", "query", "ramp_function", "variable", "internal")

_BUILD = ("update", "ramp", "anchor", "stack", "cascade", "to_timeline", "expand")
_QUERY = {"previous": "previous", "context_info": "context_information"}


def __getattr__(name):
    """
    The submodules, imported when first asked for; and, for a name this module used to
    hold, where it is now.
    """
    if name in _SUBMODULES:
        return _importlib.import_module("{}.{}".format(__name__, name))
    if name in _BUILD or name in ("noop", "as_deferred", "create"):
        where = "the user API, `wt.{0}`, or `wignertime.timeline.build.{0}`".format(
            name
        )
        if name == "create":
            where = "`wt.to_timeline(wt.update(...))` (#85)"
        raise AttributeError(
            "`wignertime.timeline.{}` is gone: `timeline` is a package now (#163). Use"
            " {}.".format(name, where)
        )
    if name in ("ANCHOR", "LAST", "VARIABLE"):
        raise AttributeError(
            "`wignertime.timeline.{0}` is gone (#163). Use the user API, `wt.{0}`.".format(
                name
            )
        )
    if name in _QUERY:
        raise AttributeError(
            "`wignertime.timeline.{}` is gone (#163). Use the user API, `wt.{}`, or"
            " `wignertime.timeline.query.{}`.".format(name, _QUERY[name], _QUERY[name])
        )
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
