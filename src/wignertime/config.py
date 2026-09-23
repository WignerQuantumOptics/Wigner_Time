# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re

###############################################################################
#                   Constants                                                 #
###############################################################################
LABEL__ANCHOR = "⚓"
TIME_RESOLUTION = 1.0e-6

VARIABLE__REGEX = re.compile(r"^([^_]+)_([^_]+(?:_[^_]+)*)(?:__([^_]+))?$")
"""
The naming convention for a `variable`, as `<device>_<UID>(__<unit>)`; the three
groups are what `variable.parse` returns. A missing `__<unit>` is what marks a line
as digital, so the unit separator is `__` and may appear at most once, at the end.
The `<UID>` may itself contain single underscores, so both `coil_MOTlower__A` and
`coil_MOT_lower__A` are admissible.

This lives here, rather than in `variable`, because the convention is a *default*
rather than a law: a site that consistently applies a different one can rebind this
name before building its `connection`s. `variable.parse` and
`adwin.connection.is_valid_name` read it at call time, so an override takes effect
without reimporting.
"""

ORIGIN__INFER = "INFER"
"""
The signature default for `origin` in `update`, `anchor` and `ramp`, replacing a bare
`None` (2026-09-23, A8's final form). Before this, `None` meant two different things at
once depending on who supplied it -- the parameter default, or a caller writing it
explicitly -- and the two were indistinguishable once inside the function, so there was
no way to *ask* for one rather than the other. That collided directly with the reason
this constant exists: a caller who wants no origin resolution at all, for a 2-D `ramp`
start stated explicitly or for any `update`/`anchor` row, needs a way to say so that is
visible in `origin=` itself, not implied by which input shape they happened to use.

Splitting the sentinel from the parameter default frees `None` for exactly that. A
caller who writes `origin=None` explicitly gets *no* resolution: `origin__defaults` is
never consulted, and `internal.origin.update`'s existing no-op on an unresolved
`[None, None]` pair returns the stated coordinates exactly as given. A caller who writes
nothing -- the default is this constant, not `None` -- or who writes
`origin=ORIGIN__INFER` explicitly, gets what has always happened: the same
default-chase `internal.origin.auto` has always run. See `internal.origin.auto_or_off`,
the wrapper that reads this sentinel; `auto` itself is unchanged and keeps its own
long-standing contract, where a bare `None` still means "run the defaults" (its own
direct callers, including its tests, rely on that).
"""

# Time references in order of priority, each paired with the value reference that goes
# with it. `origin.auto` walks the list and takes the first entry whose time reference
# this timeline can satisfy, then completes whichever slots the caller left as `None`.
# The chain is terminal: if nothing is satisfiable the time origin is 0.0, with a
# warning.
ORIGIN__DEFAULTS = [["anchor", None], ["last", None]]
"""For `update` and `anchor`, whose values are absolute -- hence `None` in every value slot."""

ORIGIN__DEFAULTS__RAMP = [["anchor", "variable"], ["last", "variable"]]
"""
For `ramp`, which is the one core function that *needs* a value origin: a ramp runs from
wherever the variable currently sits to the target, so its start value has to be looked
up. Hence `"variable"` in the value slot -- the variable's own previous value, bounded by
the time origin.

The `"last"` step is not decoration. Without it (this was a single-entry list until
2026-09-18) a `ramp` onto a timeline holding no anchor fell off the end of the chain and
landed in absolute time, so it could be placed *before* the rows it was appended to, with
no warning. See KNOWN_ISSUES A4.
"""

ORIGIN__INFER_BY_SHAPE = True
"""
A sitewide policy switch for `ramp` (A8/#106, 2026-09-23). `True` by default, for
humility's sake: it keeps `ramp`'s long-standing convention as the convention a caller
gets unless a site deliberately asks otherwise, rather than making today's refinement
the default behaviour for everyone on day one.

With the default `True`, any `origin` that is not an explicit `None` resolves through
the pre-refinement two-table split: `df_1` (a 2-D stated start) resolves against
`ORIGIN__DEFAULTS` (value slot `None`, so it is left untouched unless the caller's own
`origin` names a value origin explicitly), and `df__no_start_points` (an inferred
start) resolves against `ORIGIN__DEFAULTS__RAMP` (value slot `"variable"`). This is
`ramp`'s original behaviour, restored as the default rather than reached only by
setting this switch: a bare call, and an explicit time-only `origin` such as
`origin="stage1"`, both protect a stated 2-D value the same way, which is what keeps a
caller from having to notice or care that this switch exists.

Setting this `False` is what asks for this session's refinement instead: every start
row, 2-D or 1-D, resolves uniformly against `ORIGIN__DEFAULTS__RAMP`, so a stated 2-D
value is offset by the variable's current value exactly like an inferred one, and
nothing about a row's resolution depends on which of the two input shapes produced it.
This is read at call time, for every `ramp` call in the running process -- it is a
site's standing convention, not a per-call choice.

`origin=None`, regardless of this switch either way, always means the same thing: no
origin resolution at all, for every variable in the call, stated coordinates returned
exactly as given. That is the one way to protect a value that does not depend on this
switch, and it is the only way while the switch is `True` to get the fully uniform
reading for one particular call without changing the switch itself.
"""

CONTEXT__INFER = "INFER"
"""
The signature default for `context` in `create`, `update`, `anchor` and `ramp`,
replacing a bare `None` (A8, 2026-09-24) -- the same split as `ORIGIN__INFER`, for the
same reason, applied to context inheritance instead of origin resolution.

Before this, `context=None` was overloaded exactly like `origin=None` used to be: it
was the parameter default, meaning "inherit an unstated row's context from wherever the
timeline it is being added to last left off" (see `internal.timeline.inherit.context`'s
first branch), and there was no other way to write "no, don't do that" -- a caller who
wanted an added row to sit in the plain default context, the empty string, with no
inheritance, had no spelling for that request at all.

Splitting the sentinel from the parameter default frees `None` for exactly that
request. A caller who writes `context=None` explicitly gets *no* inheritance: the new
rows keep the empty-string context construction already gives an unstated row, and nothing
is copied from the timeline they are joining. A caller who writes nothing -- the
default is this constant, not `None` -- or who writes `context=CONTEXT__INFER`
explicitly, gets what has always happened: unstated rows inherit the previous
timeline's context, exactly as `internal.timeline.inherit.context` has always done. See
`internal.timeline.inherit.resolve`, the single point (mirroring `origin.auto_or_off`)
where this sentinel is translated before reaching that function.
"""

###############################################################################
#                   Logging                                                 #
###############################################################################
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
wtlog = logging.getLogger("wtlog")
wtlog.setLevel(logging.WARNING)
