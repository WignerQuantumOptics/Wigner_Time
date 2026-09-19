"""
The National Instruments backend is a placeholder, and has to stay an importable one.

D6/#120: a missing comma between the message and `UserWarning` made
`warnings.warn(...)` a call on the string's `__call__`, so the module did not parse at
all. Nothing imported it, so nothing noticed -- which is the argument for this file
existing rather than for the fix being large.
"""

import importlib
import warnings


def test_the_placeholder_warns_rather_than_failing_to_parse():
    module = importlib.import_module("wignertime.national_instruments")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(module)

    assert [w.category for w in caught] == [UserWarning]
    assert "not implemented" in str(caught[0].message)
