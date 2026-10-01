"""
Without the ADwin driver, everything that needs no machine still works – the user API's
`wt.adwin` namespace, the connections, the conversion – and `link_device`, the one way to
a machine, says what to install.

Run in a fresh interpreter in which the driver cannot be found, so that the result does
not depend on whether this environment has the `adwin` extra.
"""

import subprocess
import sys

_WITHOUT_DRIVER = """
import importlib.util, sys
_find = importlib.util.find_spec
importlib.util.find_spec = lambda name, *a: None if name == "ADwin" else _find(name, *a)
class _Refuse:
    def find_spec(self, name, *a):
        if name == "ADwin":
            raise ModuleNotFoundError("blocked for the test", name="ADwin")
sys.meta_path.insert(0, _Refuse())
"""


def _run(code):
    return subprocess.run(
        [sys.executable, "-c", _WITHOUT_DRIVER + code], capture_output=True, text=True
    )


def test_connections_and_conversion_need_no_driver():
    result = _run(
        """
import sys
import wignertime.api.v09 as wt
from wignertime.demo import full_experiment as ex
arrays = wt.adwin.convert(ex.timeline_demo, ex.connections, ex.devices, cycle_period=5e-6)
print("ADwin" in sys.modules, len(arrays) > 0)
"""
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["False", "True"]


def test_reaching_a_machine_says_what_to_install():
    result = _run(
        """
import wignertime.api.v09 as wt
try:
    wt.adwin.link_device()
except ModuleNotFoundError as e:
    print(e.name)
    print(e)
"""
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "ADwin"
    assert "wigner-time[adwin]" in result.stdout
