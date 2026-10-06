# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Reading a timeline back: what is in it, rather than adding to it.

    previous(timeline, "shutter__MOT")      # the latest row of a variable
    context_information(timeline)["MOT"]    # the variables and time span of a context
    units(timeline)                         # the units in use

A timeline is a table, so anything else can be asked of it with the library that holds
it. These go through `wt_frame`, like every operation of the package, so they do not
depend on which library that is.
"""

from munch import Munch

from wignertime.timeline import variable as wt_variable
from wignertime.internal import dataframe as wt_frame
from wignertime.internal import tags as wt_tags


def previous(
    timeline: wt_frame.CLASS,
    variable=None,
    column="variable",
    time__max=None,
):
    """
    The latest row of `timeline`, as a `Munch` (read it as `row.time` or `row["time"]`):
    optionally only rows whose `column` equals `variable`, and only rows at or before
    `time__max`. Among rows at the same latest time, the one written last is returned.

        previous(timeline)                                   # the last entry of all
        previous(timeline, "shutter__MOT").time              # when the shutter was last set
        previous(timeline, "shutter__MOT", time__max=t)      # ... at or before `t`
        previous(timeline, "MOT", column="context").time     # the MOT stage's last entry

    This is the lookup the origin machinery resolves with, so it agrees with it:
    `previous(timeline, "coil__MOT__A").value` is where a `ramp` of that coil added at the
    end would start. The state before the run (`time=-math.inf`) and after it
    (`time=math.inf`) are entries like any other, so on a finished timeline the final
    state is the latest; bound `time__max` to ask about the run itself.

    An anchor may be asked for by the anchor symbol alone, meaning the latest of them.

    Raises `ValueError` when the timeline is empty, or nothing matches.
    """
    if timeline is None or wt_frame.is_empty(timeline):
        raise ValueError(
            "\n".join(
                [
                    "Nothing to look {}up in: the timeline is empty.".format(
                        "`{}` ".format(variable) if variable is not None else ""
                    ),
                    "",
                    "In an origin, which refers to something already written, give a"
                    " number instead: `origin=0.0` places the rows in absolute time.",
                ]
            )
        )

    if time__max is not None:
        tline = wt_frame.filter(
            timeline, wt_frame.column(timeline, "time") <= time__max
        )
    else:
        tline = timeline

    if variable is not None:
        names = wt_frame.column(tline, column)
        tl__filtered = wt_frame.filter(tline, names == variable)
        if wt_frame.is_empty(tl__filtered) and (variable == wt_tags.LABEL__ANCHOR):
            tl__filtered = wt_frame.filter(
                tline, [isinstance(n, str) and n.startswith(variable) for n in names]
            )
    else:
        tl__filtered = tline

    if wt_frame.is_empty(tl__filtered):
        raise ValueError(
            "No row{}{} in this timeline.".format(
                "" if variable is None else " with {} {!r}".format(column, variable),
                "" if time__max is None else " at or before time {}".format(time__max),
            )
        )

    return Munch(wt_frame.row_from_max_column(tl__filtered))


def context_information(timeline):
    """
    Useful data (currently 'variables' and 'times') concerning every context. The result is a dictionary, indexed by context.

    e.g. To get the start and end times of the 'MOT' context, call `context_information(timeline)['MOT']['times']`.
    """
    if wt_frame.has_columns(timeline, ["context", "time", "variable"]):
        info = {}
        for k, rows in sorted(
            wt_frame.group_by(timeline, "context"), key=lambda pair: pair[0]
        ):
            times = wt_frame.column(rows, "time")
            info[k] = {
                "variables": set(wt_frame.column(rows, "variable")),
                "times": [times[0], times[-1]],
            }
        return info

    else:
        return None


def units(timeline: wt_frame.CLASS, do_digital: bool = True):
    """
    Returns a set of different timeline units (strs).
    """
    us = set(map(wt_variable.unit, wt_frame.unique(timeline, "variable")))
    if do_digital:
        return us
    else:
        us.discard("digital")
        return us
