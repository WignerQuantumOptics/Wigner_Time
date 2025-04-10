import funcy

import wigner_time.adwin as wt_adwin
from wigner_time.internal import dataframe as wt_frame


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
    """
    mask__duplicates = wt_frame.duplicated(timeline, subset=subset)

    return timeline[~mask__duplicates | (timeline["context"].isin(unless_context))]


def all(timeline):
    """
    Includes ADwin-specific methods ontop of the basic timeline sanitization for removing unnecessary points and raising errors on illogical input.
    """
    return funcy.compose(
        drop_duplicates,
        special_contexts,
        types,
    )(timeline)
