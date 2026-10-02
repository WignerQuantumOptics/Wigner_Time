# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import funcy
import numpy as np

import wignertime.adwin as wt_adwin
from wignertime.internal import dataframe as wt_frame


def cycles(timeline, special_contexts=None):
    """
    Refuses a row, outside the special contexts, at a cycle the real-time program cannot play.

    Such a row belongs in `wt_adwin.CYCLES__RUN`. Everything outside that range is the
    territory of the special contexts' sentinels, and each way of leaving it fails
    silently on the machine rather than here (D19):

    - at cycle -1 or -2, the row is played with the init or lowinit rows;
    - below -2, it sorts ahead of the lowinit rows, and since the backend plays only the
      row its index points at, and only when the count reaches it, the index never moves:
      **no row of that array is played at all** -- not the run, not the initial state,
      not the final one;
    - past the last cycle, the machine's 32-bit counter wraps negative, into the
      sentinels, so the run replays its initialisation and does not end.

    A row earlier than half a cycle before zero is therefore an error, however it came
    about, rather than something to shift or drop. Must run before `types`, which narrows
    the column to 32 bits and would wrap the late rows into plausible ones.
    """
    if special_contexts is None:
        special_contexts = wt_adwin.CONTEXTS__SPECIAL

    first, last = wt_adwin.CYCLES__RUN
    mask__run = ~np.isin(wt_frame.column(timeline, "context"), list(special_contexts))
    cycle = wt_frame.column(timeline, "cycle")
    mask__outside = mask__run & ~((cycle >= first) & (cycle <= last))

    if mask__outside.any():
        raise ValueError(
            "Rows outside the special contexts {} must fall within cycles {}..{} of the"
            " run. A row before the start stops every row of its array from being"
            " played, the initial and final states included; one past the end wraps the"
            " controller's cycle counter. Offending rows:\n{}".format(
                list(special_contexts),
                first,
                last,
                wt_frame.select(
                    wt_frame.filter(timeline, mask__outside),
                    ["variable", "time", "context", "cycle"],
                ),
            )
        )

    return timeline


def ascending(output):
    """
    Refuses converted arrays whose cycles are not in ascending order (D20).

    `output` is what `internal.to_tuples` returns, `[analogue, digital]`, each a list of
    `(cycle, module, channel, digits)`. The real-time program walks each array with an
    index that only moves forward, so a row out of order is not skipped but played
    *late*: at the cycle of the row before it. Nothing on the machine can tell.

    `to_tuples` sorts, so this holds by construction today. It is checked on the arrays
    themselves because they are the contract with the machine, and nothing between here
    and the upload would notice if it stopped holding.
    """
    for label, rows in zip(["analogue", "digital"], output):
        cycle = np.array([row[0] for row in rows], dtype=np.int64)
        backwards = np.flatnonzero(np.diff(cycle) < 0)
        if len(backwards):
            # Rows are counted from 1, as the controller's arrays are.
            i = int(backwards[0])
            raise ValueError(
                "The {} array is not in ascending cycle order: row {} is at cycle {},"
                " after one at cycle {}. The controller would play it late, at"
                " cycle {}.".format(label, i + 2, cycle[i + 1], cycle[i], cycle[i])
            )

    return output


def special_contexts(timeline, special_contexts=wt_adwin.CONTEXTS__SPECIAL):
    """
    Ensures that a variable has at most one entry **before the run**, across
    `ADwin_LowInit` and `ADwin_Init` together, and at most one after it, in
    `ADwin_Finish`. There is no concept of 'time' inside the special contexts.

    The contexts before the run are counted together (#154, (b1), settled by the
    maintainer 2026-09-29): both are at −∞, so nothing in the timeline orders them, and a
    value lookup would otherwise see two candidates there. They used to be counted per
    context. What is lost is changing a variable between `lowinit:` and `init:`, which
    nothing did. A context's side is the sign of its sentinel.

    Similarly, the time values are adjusted to avoid automatic removal later on.
    """
    contexts__by_side = {}
    for variable, context in wt_frame.rows(timeline, ["variable", "context"]):
        if context in special_contexts:
            side = (
                "before the run" if special_contexts[context] < 0 else "after the run"
            )
            contexts__by_side.setdefault((variable, side), []).append(context)
    duplicates = {
        key: contexts
        for key, contexts in sorted(contexts__by_side.items())
        if len(contexts) > 1
    }

    # Replace time values with those specified in wt_adwin.CONTEXTS__SPECIAL
    timeline = wt_frame.replace_column__filtered(timeline, wt_adwin.CONTEXTS__SPECIAL)

    if not duplicates:
        return timeline
    else:
        raise ValueError(
            "The same variable has more than one value before the run (ADwin_LowInit and"
            " ADwin_Init together) or after it (ADwin_Finish). These special contexts have"
            " no concept of time, so nothing orders the values. For details, see the"
            " duplicate information:\n"
            + "\n".join(
                "  {}, {}: {}".format(variable, side, contexts)
                for (variable, side), contexts in duplicates.items()
            )
        )


def types(timeline, schema=wt_adwin.SCHEMA):
    return wt_frame.cast(timeline, schema)


def drop_duplicates(
    timeline,
    subset=["variable", "cycle"],
    unless_context=list(wt_adwin.CONTEXTS__SPECIAL.keys()),
):
    """
    An alternative to that in timeline, to deal with ADwin-specific cases.

    Drop rows where the columns specified in `subset` are both duplicated, except for in the specific `context`s listed.

    This removes *temporal* collisions: two entries for the same variable that round to the same cycle. The later entry wins, as `wt_frame.duplicated` keeps the last occurrence.
    """
    mask__duplicates = wt_frame.duplicated(timeline, subset=subset)

    return wt_frame.filter(
        timeline,
        ~mask__duplicates
        | np.isin(wt_frame.column(timeline, "context"), unless_context),
    )


def drop_repeats(
    timeline,
    subset=["module", "channel"],
    column__value="value__digits",
    column__order="cycle",
    unless_context=list(wt_adwin.CONTEXTS__SPECIAL.keys()),
):
    """
    Drops rows that would command a channel to the value it already holds.

    Where `drop_duplicates` removes temporal collisions, this removes *value* redundancy: rows whose digitized value is unchanged from the previous row on the same physical channel. The ADwin program only acts when a value differs from the preceding one, so these rows occupy memory and transfer bandwidth without ever producing an output change.

    The effect is largest on expanded `ramp`s. A ramp sampled at the cycle period produces one row per cycle, but a device can only express as many distinct outputs as it has digits across the ramp's span; the surplus rows repeat. Since the sampling grid is the hardware's own time grid and the value grid is the converter's least significant bit, the rows that survive are exactly the transitions the hardware is capable of making. Filtering here is therefore not an approximation to bit-flip-timed expansion – on this grid it is equivalent to it, and it needs no inverse of the ramp function, which would be unavailable for interpolated calibrations in any case.

    Grouping is by physical channel rather than by `variable`, since the channel is the state the real-time program compares against.

    Rows in the special `context`s are excluded from the comparison entirely and always kept: they carry the safe-state guarantee and have no position in time.

    The first and last row of every channel are always kept. Retaining the last matters beyond making the final commanded state explicit: `adwin.core.upload` takes the run length from the highest non-special cycle, and the tail of a hyperbolic-tangent ramp is flat, so dropping trailing repeats would silently shorten the experiment.
    """
    columns__needed = set(subset) | {column__value, column__order, "context"}
    if not wt_frame.has_columns(timeline, columns__needed):
        return timeline

    mask__special = np.isin(wt_frame.column(timeline, "context"), unless_context)
    timeline__run = wt_frame.filter(timeline, ~mask__special)

    if wt_frame.is_empty(timeline__run):
        return timeline

    mask__changed = wt_frame.mask__changed(
        timeline__run,
        subset=subset,
        column__value=column__value,
        column__order=column__order,
    )

    # `mask__changed` covers only the non-special rows, so it is widened back to all of
    # them, by position. A special row is kept regardless.
    mask__keep = mask__special.copy()
    mask__keep[~mask__special] = mask__changed

    return wt_frame.filter(timeline, mask__keep)


def all(timeline, do_drop_repeats=True):
    """
    Includes ADwin-specific methods ontop of the basic timeline sanitization for removing unnecessary points and raising errors on illogical input.

    `do_drop_repeats` can be turned off for debugging, or to inspect the unfiltered cost of an expansion.
    """
    return funcy.compose(
        drop_repeats if do_drop_repeats else funcy.identity,
        drop_duplicates,
        special_contexts,
        types,
        cycles,
    )(timeline)
