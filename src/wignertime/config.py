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


class _Infer:
    __slots__ = ()

    def __repr__(self):
        return "INFER"

    def __reduce__(self):
        # `copy`, `deepcopy` and `pickle` all return this same object, so an `is` test
        # still holds for a default captured by a deferred call.
        return "INFER"


INFER = _Infer()
"""
The default of `origin` in `update`, `anchor` and `ramp`, and of `context` in `create`,
`update`, `anchor` and `ramp` (#142). It is there so that a signature shows that the
default *does* something: the origin is inferred from the timeline being extended (see
`ORIGIN__DEFAULTS` and `ORIGIN__DEFAULTS__RAMP`), and an unstated context is inherited
from it, and `help(tl.update)` reads `origin=INFER`.

`None` means exactly the same, both as the whole argument and in either slot of an
origin pair. That is deliberate. A stage that takes `origin=None` or `context=None` and
passes it on -- the usual way of writing "no opinion of my own" -- then gets the
library's default without having to know that this object exists, and a pair such as
`[None, 0.0]` reads the same as `[INFER, 0.0]`. Absolute placement is a number:
`origin=0.0` for `update` and `anchor`, `origin=[0.0, 0.0]` for `ramp`, whose value slot
otherwise still defaults to the variable. There is no way to switch context
inheritance off: every row has a context, stated or inherited (#156).

It is an object rather than a string so that it cannot be mistaken for a name:
`context="INFER"` is an ordinary context.
"""

ORIGIN__INFER = INFER
"""`INFER`, under the name the `origin` signatures use."""

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

CONTEXT__INFER = INFER
"""`INFER`, under the name the `context` signatures use."""

###############################################################################
#                   Logging                                                 #
###############################################################################
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
wtlog = logging.getLogger("wtlog")
wtlog.setLevel(logging.WARNING)
