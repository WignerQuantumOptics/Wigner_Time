# __init__.py

import importlib


# Conditionally import `science`
if importlib.util.find_spec("matplotlib"):
    from . import display
    DISPLAY = True
else:
    DISPLAY = None  # Exclude if dependency is missing

# Exposes what's available to the user through 'import *'
# WIP
__all__ = ["timeline", "adwin", "variable", "connection", "device"]
