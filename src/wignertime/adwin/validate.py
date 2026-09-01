import funcy

import wignertime.adwin as wt_adwin
from wignertime.internal import dataframe as wt_frame


def special_contexts(timeline, special_contexts=wt_adwin.CONTEXTS__SPECIAL):
    """
    Ensures that there isn't more than one entry for a given variable inside special contexts. This is necessary as there is no concept of 'time' inside the special contexts defined for ADwin.

    Similarly, the time values are adjusted to avoid automatic removal later on.
    """
    df = timeline[timeline["context"].isin(special_contexts)]
    df_N = df.groupby(["variable", "context"])["value"].count()
    duplicates = df_N[df_N > 1].reset_index()
    duplicates.columns = ["variable", "context", "variable_occurences"]

    # Replace time values with those specified in wt_adwin.CONTEXTS__SPECIAL
    timeline = wt_frame.replace_column__filtered(timeline, wt_adwin.CONTEXTS__SPECIAL)

    if duplicates.empty:
        return timeline
    else:
        raise ValueError(
            "The same variable has more than one value inside a special context. This will not work as expected on export to ADwin as these special contexts have no concept of time. For details,  see the duplicate information: "
            + str(duplicates)
        )


def types(timeline, schema=wt_adwin.SCHEMA):
    return timeline.astype(schema)


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

    return timeline[~mask__duplicates | (timeline["context"].isin(unless_context))]


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

    The first and last row of every channel are always kept. Retaining the last matters beyond making the final commanded state explicit: `adwin.core.create` takes the run length from the highest non-special cycle, and the tail of a hyperbolic-tangent ramp is flat, so dropping trailing repeats would silently shorten the experiment.
    """
    columns__needed = set(subset) | {column__value, column__order, "context"}
    if not columns__needed.issubset(timeline.columns):
        return timeline

    mask__special = timeline["context"].isin(unless_context)
    timeline__run = timeline[~mask__special]

    if timeline__run.empty:
        return timeline

    mask__changed = wt_frame.mask__changed(
        timeline__run,
        subset=subset,
        column__value=column__value,
        column__order=column__order,
    )

    mask__keep = mask__special | mask__changed.reindex(timeline.index).fillna(
        False
    ).astype(bool)

    return timeline[mask__keep]


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
    )(timeline)
