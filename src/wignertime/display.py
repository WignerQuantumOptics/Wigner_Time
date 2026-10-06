# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

# Block module based on dependency
import importlib.util

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")


from wignertime.adwin import display as adwin_display


def display(
    timeline,
    variables=None,
):
    return adwin_display.quantities(timeline, variables)
