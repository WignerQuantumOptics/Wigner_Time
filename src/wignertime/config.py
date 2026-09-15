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

# List of origins according to priority: first is most important
ORIGIN__DEFAULTS = [["anchor", None], ["last", None]]

###############################################################################
#                   Logging                                                 #
###############################################################################
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
wtlog = logging.getLogger("wtlog")
wtlog.setLevel(logging.WARNING)
