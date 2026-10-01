# SPDX-FileCopyrightText: 2026 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The user API of Wigner Time, by version (#163).

    import wignertime.api.v0_9 as wt

A version is a designed, managed list of what a user works with day to day. What it
lists keeps its name and meaning for as long as that version exists; a change that
would break it goes into the next version instead, and the old one stays importable.
Everything else in `wignertime` remains reachable, for whoever needs it, but carries no
such promise and may change between releases.

Versions: `v0_9` (named after the package version, 0.9).
"""
