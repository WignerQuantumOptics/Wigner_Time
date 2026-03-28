# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

# Block module based on dependency
import importlib.util

if not importlib.util.find_spec("matplotlib"):
    raise ImportError("The `display` module requires `matplotlib` to be installed.")


from wigner_time.adwin import display as adwin_display


def display(
    timeline,
    variables=None,
):
    # TODO:
    # - This should be ADwin-independent
    # - Branch based on whether ADwin is installed??
    # - Allow for expansion and time-resolution.
    # suffixes__analogue is temporarily part of the API until we understand what to replace it with
    return adwin_display.channels(timeline, variables)
