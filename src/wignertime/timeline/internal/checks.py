# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The refusals of `timeline.build`: arguments that cannot mean what was intended are
stopped where they are written, with the mistake named.
"""


import numpy as np

from wignertime.internal import dataframe as wt_frame
from wignertime.internal import tags as wt_tags
from wignertime.internal import util as wt_util


def refuse_timeline(name, vtvc_dict):
    """
    `timeline=` would otherwise land in the open `**vtvc_dict` namespace and be read as a
    variable named `timeline`, whose value is a table -- refused with the mistake named
    rather than as "not a numeric value".
    """
    if "timeline" in vtvc_dict:
        raise TypeError(
            "\n".join(
                [
                    "`{}` takes no timeline (#85). It returns a stage, and"
                    " `to_timeline` applies it:".format(name),
                    "",
                    "    to_timeline({}(...), onto=timeline)".format(name),
                ]
            )
        )


def refuse_infinite_ends(**times):
    """
    A ramp runs between two instants, and ±∞ is before or after the run (#154). Refused
    where written: applied, a start at −∞ failed on its value lookup instead, as though
    the variable had never been set.
    """
    infinite = sorted(
        k for k, t in times.items() if t is not None and not np.isfinite(t)
    )
    if infinite:
        raise ValueError(
            "A ramp runs between two instants, and ±∞ is before or after the run, not an"
            " instant (#154): {}.".format(
                ", ".join("{}={}".format(k, times[k]) for k in infinite)
            )
        )


def refuse_value_origin(origin):
    """
    A ramp starts where its variable is (#142), so the value slot of its `origin` has
    nothing to set: only `INFER`, `None` or `VARIABLE`, which all say the same. A value
    written there -- a number, or another variable's name -- is refused rather than
    added to the start, which is what made a stated `1.0` come out as `8.0` (A8).
    """
    if origin is None or origin is wt_tags.ORIGIN__INFER:
        return
    value = wt_util.ensure_pair(wt_util.ensure_iterable_with_None(origin))[1]
    if value is None or value is wt_tags.ORIGIN__INFER:
        return
    if value is wt_tags.VARIABLE:
        return
    raise ValueError(
        "\n".join(
            [
                "A ramp starts where its variable is (#142): the value slot of its"
                " `origin` has nothing to set, and was given {!r}.".format(value),
                "",
                "`origin` places the ramp's start in time. To start from another value,"
                " `update` the variable first, so that the jump shows in the table:",
                "",
                "    stack(update(coil__A=1.0), ramp(coil__A=3.0, duration=0.1))",
            ]
        )
    )


def ensure_stackable(f):
    """
    A `stack` constituent must be a *stage*: a function of a timeline. Not a timeline,
    and not a stage function that has yet to be called.

    A timeline is refused in any position (#85). `stack` composes stages and returns one,
    and `to_timeline` is the one way from a stage to a table. A table used to be accepted
    in front, which made `stack` return a table or a stage depending on its first
    argument, and let a `context` given to the stack skip that table's rows (#145); after
    the front it was accepted here and then failed inside the composition as
    `'DataFrame' object is not callable` (D17's correction).

    The other distinction is invisible to Python: a deferred call, a composed `stack` and
    an uncalled user stage are all plain `function` objects with unhelpfully similar
    signatures. So the deferral machinery tags what it produces, and this checks the tag.
    The mistake it exists for is writing a stage's name where its call belongs --
    `stack(MOT)` for `stack(MOT(...))` -- which would bind the timeline to the stage's
    first parameter, silently.
    """
    if isinstance(f, wt_frame.CLASS):
        raise TypeError(
            "\n".join(
                [
                    "`stack` was given a timeline. It composes stages, and returns one;"
                    " `to_timeline` applies it:",
                    "",
                    "    to_timeline(stack(update(...), ramp(...)), onto=timeline)",
                    "",
                    "`onto` is the timeline the stage starts from, and an empty one when"
                    " it is not given.",
                ]
            )
        )

    if wt_util.is_deferred(f):
        return f

    if callable(f) and wt_util.takes_one_timeline(f):
        # A hand-written `lambda tline: ...` is a legitimate constituent and carries no
        # tag. It is told apart from an uncalled stage by arity: see `takes_one_timeline`.
        return f

    if callable(f):
        name = getattr(f, "__name__", repr(f))
        raise TypeError(
            "\n".join(
                [
                    "`stack` was given the function `{}` itself, rather than the result"
                    " of calling it.".format(name),
                    "",
                    "A constituent must be a stage -- what a core function or a stage"
                    " function returns when called:",
                    "",
                    "    stack({}(...), update(...))".format(name),
                    "",
                    "If `{}` is your own timeline function, mark it with"
                    " `timeline.as_deferred`.".format(name),
                ]
            )
        )

    raise TypeError(
        "`stack` was given {} as a constituent, where a deferred timeline function was"
        " expected.".format(type(f).__name__)
    )


def ensure_cascadable(f):
    """
    Refuse a `cascade` argument that is not a stage function.

    The mirror of `ensure_stackable`. `cascade(timeline, MOT)` reads as reasonable and
    used to fail with `AttributeError: 'DataFrame' object has no attribute '__name__'`,
    from the dictionary comprehension that keys stages by name -- naming neither cascade,
    nor the timeline, nor what to write instead.
    """
    if isinstance(f, wt_frame.CLASS):
        raise TypeError(
            "\n".join(
                [
                    "`cascade` was given a timeline. It takes stage functions, calls"
                    " them, and returns a stage; `to_timeline` applies it:",
                    "",
                    "    to_timeline(cascade(MOT, molasses, MOT_duration=15),"
                    " onto=timeline)",
                ]
            )
        )

    if wt_util.is_deferred(f):
        raise TypeError(
            "\n".join(
                [
                    "`cascade` was given a stage that has already been called.",
                    "",
                    "    cascade(MOT, molasses, MOT_duration=15)     # not MOT(...)",
                    "",
                    "`cascade` supplies the arguments itself, by routing its keywords to",
                    "the stage named in each prefix; a stage that has already been",
                    "called has none left to route, and would be keyed under",
                    "`<lambda>`. Use `stack` for stages you have called yourself.",
                ]
            )
        )

    if not callable(f) or not hasattr(f, "__name__"):
        raise TypeError(
            "`cascade` takes named stage functions; {!r} is neither. Keywords are"
            " routed by the stage's `__name__`, so an anonymous callable cannot"
            " receive any.".format(f)
        )
