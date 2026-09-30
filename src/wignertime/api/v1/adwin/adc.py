# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Recording with the ADC during a run, version 1 of the user API. Needs the `adwin` extra.

    samples = wt.adwin.adc.run(upload, t=0.1, duration=0.02)

or `arm` a `Window` before a run and `read` its `Samples` after it.
"""

from wignertime.adwin.adc import Samples, Window, arm, read, run

__all__ = ["run", "arm", "read", "Window", "Samples"]
