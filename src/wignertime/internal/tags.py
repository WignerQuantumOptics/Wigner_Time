# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The package's fixed words: the `INFER` default, the origin tags and the anchor label.

These are not settings. They lived in `config` until 2026-10-01, which put them beside
what a user may change; `config` still answers to their names, so old code and old
pickles resolve, but does not list them and refuses to rebind them.
"""

import enum
import logging

LABEL__ANCHOR = "⚓"
"""
What an anchor's variable name starts with, as `⚓__001`. Fixed: a timeline saved with
one label has to be read with the same one, and the label was read at import in some
places and at call time in others, so rebinding it numbered every anchor `__001`.
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
`[None, 0.0]` reads the same as `[INFER, 0.0]`. Absolute placement is a number,
`origin=0.0`, and reads the same in `update`, `anchor` and `ramp`: a ramp always starts
where its variable is (#142), so its value slot is never an origin question. There is
no way to switch context inheritance off: every row has a context, stated or inherited
(#156).

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
class Origin(enum.Enum):
    """
    The reserved origin words, as tags rather than strings (#158, 2026-09-29).

    A string in an `origin` is always a *name* -- of a variable or of a context -- and a
    tag is always a *rule*. While the rules were the strings `"anchor"`, `"last"` and
    `"variable"`, a string was sometimes one and sometimes the other, so a context or a
    variable named after one of the words could not be referred to, and had to be refused
    where it was written (A9). Tags are compared with `is`, print as their bare names, as
    `INFER` does, and never reach the data, since an origin is resolved while the
    timeline is built.

    - `ANCHOR`: the most recent anchor;
    - `LAST`: the latest entry of the timeline;
    - `VARIABLE`: each variable relative to its own most recent entry, in time or in
      value -- the one tag admissible in either slot.
    """

    ANCHOR = "anchor"
    LAST = "last"
    VARIABLE = "variable"

    def __repr__(self):
        return self.name

    __str__ = __repr__


ANCHOR = Origin.ANCHOR
LAST = Origin.LAST
VARIABLE = Origin.VARIABLE

CONTEXT__INFER = INFER
"""`INFER`, under the name the `context` signatures use."""


wtlog = logging.getLogger("wignertime")
"""
The package's logger. It configures nothing: what is shown, and where, is the user's
choice (`logging.getLogger("wignertime").setLevel(logging.DEBUG)`). With no logging
configured, Python prints its warnings to stderr.
"""
