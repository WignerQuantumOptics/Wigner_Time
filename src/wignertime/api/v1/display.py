# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Plotting a timeline, version 1 of the user API. Needs the `display` extra.

    wt.display.quantities(timeline)

One panel per physical quantity (by the variables' units), and one for the digital lines.
"""

from wignertime.adwin.display import quantities

__all__ = ["quantities"]
