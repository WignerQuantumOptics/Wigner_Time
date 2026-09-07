# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

###############################################################################
#                   Constants                                                 #
###############################################################################
LABEL__ANCHOR = "⚓"
TIME_RESOLUTION = 1.0e-6

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
