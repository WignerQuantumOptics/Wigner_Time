# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
How `stack` and `cascade` place keywords on their constituents, and say so when they
cannot. Private to `timeline.build`.
"""


from wignertime.internal import util as wt_util


def keywords_available(constituents):
    """
    The keywords this stack's constituents can between them consume, or `None` if none of
    them says.

    A constituent that does not record a set is **neutral** -- it neither vouches for a
    keyword nor objects to one. `noop` and a hand-written `lambda tline: ...` are of that
    kind, and treating them as permissive instead would switch the guard off for any
    stack containing one, which the lab's conditional stages make common.
    """
    sets = [
        declared
        for declared in (wt_util.keywords_declared(f) for f in constituents)
        if declared is not None
    ]
    return set().union(*sets) if sets else None


def message__unplaced(unplaced, keywords__available):
    """
    Say that a forwarded keyword reached no constituent, and why that is not harmless.
    """
    return "\n".join(
        [
            "`stack` could not place {} keyword(s): {}.".format(
                len(unplaced), ", ".join(repr(k) for k in unplaced)
            ),
            "",
            "A keyword given to `stack` is forwarded to every constituent, and the core",
            "functions read an unrecognised keyword as a *variable name*. So an unplaced",
            "keyword does not merely go unused: the parameter you meant to set stays at",
            "its default, and a variable of that name enters the timeline, to be dropped",
            "again without comment at export for having no connection.",
            "",
            "Placeable here: {}.".format(
                ", ".join(sorted(keywords__available)) or "nothing"
            ),
            "",
            "To set a parameter of one stage rather than all of them, call that stage",
            "with it -- `stack(MOT(duration=15))` -- or use `cascade`, which",
            "routes `MOT_duration=15` by prefix.",
        ]
    )


def route_keyword(key, names__by_length, stages__by_name):
    """
    Resolve one `cascade` keyword to a `(stage name, parameter name)` pair, or to
    `None` with the reason it could not be resolved.

    Matching is anchored to the start of the key and to a `_` boundary, so a parameter
    that merely *contains* a stage name is not captured by it. Candidates are tried
    longest first, because a shorter stage name can be a prefix of a longer one
    (`MOT_` also begins `MOT_detuned_growth_duration`).

    Longest-first alone is not enough to settle the genuine collision, though: if
    `MOT_detuned_growth` does not take the remainder but `MOT` does, the key belongs to
    `MOT`. So a split is accepted only when the target actually takes the parameter --
    or has `**kwargs`, which is how `init` and `finish` stay open for the injection
    idiom of `sec:forwarding`.
    """
    near_misses = []

    for name in names__by_length:
        if not key.startswith(name + "_"):
            continue
        parameter = key[len(name) + 1 :]
        if wt_util.accepts_keyword(stages__by_name[name], parameter):
            return (name, parameter), None
        near_misses.append((name, parameter))

    return None, near_misses


def message__unroutable(unroutable, names__by_length):
    """
    Say which keywords could not be routed and why, rather than only that some could not.

    A keyword that named a stage but not one of its parameters is the more interesting
    case -- usually a misspelled parameter rather than a misspelled stage -- so it is
    reported against the stage it nearly reached.
    """
    lines = []
    for key, near_misses in unroutable.items():
        if near_misses:
            name, parameter = near_misses[0]
            lines.append(
                "  {} -> `{}` is not a parameter of `{}`".format(key, parameter, name)
            )
        else:
            lines.append("  {} -> matches no stage name".format(key))

    return "\n".join(
        [
            "`cascade` could not route {} keyword(s):".format(len(unroutable)),
            *lines,
            "",
            "Keywords are routed by stage-name prefix, e.g. `MOT_duration=1.0` reaches",
            "`MOT`'s `duration`. The stages given were: {}.".format(
                ", ".join("`{}`".format(n) for n in sorted(names__by_length))
            ),
            "",
            "An unroutable keyword is an error rather than a default, because silently",
            "dropping it would run the stage with its default value -- a physically",
            "different sequence that still executes.",
        ]
    )
