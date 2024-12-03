import importlib.util


# Conditionally import `science`
if importlib.util.find_spec("matplotlib"):
    __all__ = ["timeline", "adwin", "variable", "connection", "device", "display"]
else:
    __all__ = ["timeline", "adwin", "variable", "connection", "device"]
