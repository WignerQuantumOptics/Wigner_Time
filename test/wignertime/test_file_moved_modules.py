"""
#163 moved modules of the package. A pickle names every function it holds by its module, so
a timeline archived with a ramp function from before the move must still load, and with
the function it was archived with.
"""

import pickle
import sys
import types

import wignertime.api.v09 as wt
from wignertime.io import file
from wignertime.timeline import ramp_function


def test_a_timeline_pickled_before_the_move_still_loads(tmp_path, monkeypatch):
    timeline = wt.to_timeline(
        wt.stack(
            wt.update(coil__MOT__A=0.0, time=0.0, context="init"),
            wt.ramp(coil__MOT__A=1.0, duration=1e-3),
        )
    )
    # Pickle it as the old layout would have: `tanh` living in `wignertime.ramp_function`.
    old = types.ModuleType("wignertime.ramp_function")
    old.tanh = ramp_function.tanh
    monkeypatch.setitem(sys.modules, "wignertime.ramp_function", old)
    monkeypatch.setattr(ramp_function.tanh, "__module__", "wignertime.ramp_function")
    path = tmp_path / "archived.pickle"
    path.write_bytes(pickle.dumps(timeline))
    monkeypatch.undo()
    assert b"wignertime.ramp_function" in path.read_bytes()
    assert "wignertime.ramp_function" not in sys.modules

    loaded = file.load(path)
    assert set(loaded["function"].dropna()) == {ramp_function.tanh}
    assert loaded.drop(columns="function").equals(timeline.drop(columns="function"))
