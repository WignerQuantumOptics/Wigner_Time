import pytest

import wignertime.adwin as wt_adwin
from wignertime import conversion
from wignertime import device
from wignertime import timeline as tl
from wignertime.adwin import connection as adcon
from wignertime.adwin import console


class _Machine:
    """
    Stands in for `ADwin.ADwin` with `WignerTimeConsole.bas` loaded as process 10, serving a
    request the moment it is written, as its `event:` does, unless a sequence owns the
    outputs or `serving` is off. `running` is what `Process_Status(10)` answers.
    """

    def __init__(self, running=1, serving=True):
        self.par, self.data, self.written = {}, {}, []
        self.running, self.serving = running, serving

    def Get_Par(self, number):
        return self.par.get(number, 0)

    def Set_Par(self, number, value):
        self.par[number] = value
        owner = self.par.get(wt_adwin.PAR__SEQUENCE__OWNER, 0)
        if number == console.PAR__REQUEST and value and self.serving and not owner:
            self.written.append(tuple(self.par[n] for n in (70, 71, 72)))
            self.par[console.PAR__REQUEST] = 0
            self.par[console.PAR__SERVED] = self.par.get(console.PAR__SERVED, 0) + 1

    def Process_Status(self, process):
        return self.running

    def GetData_Long(self, number, startindex, count):
        return self.data[number][startindex - 1 : startindex - 1 + count]

    def Workload(self):
        return 3


def _tables(to_V=2.0):
    connections = adcon.new(
        ["shutter_MOT", 1, 11], ["coil_MOT__A", 4, 1], ["lockbox_MOT__MHz", 3, 8]
    )
    devices = device.new(
        ["coil_MOT__A", to_V, -5, 5], ["lockbox_MOT__MHz", 0.05, -200, 200]
    )
    defaults = tl.create(shutter_MOT=1, coil_MOT__A=1.5, t=0.0, context="init")
    return connections, devices, defaults


def _panel(**kw):
    return console.panel(*_tables(**kw))


def test_the_panel_takes_its_defaults_from_the_timeline(capsys):
    table = _panel()
    values = dict(zip(table["variable"], table["default_value"]))
    assert values == {"shutter_MOT": 1.0, "coil_MOT__A": 1.5, "lockbox_MOT__MHz": 0.0}
    assert "lockbox_MOT__MHz" in capsys.readouterr().out, "the missing one is reported"


def test_an_analogue_channel_without_a_device_is_refused():
    """It would be taken for a digital line, and switched between digits 0 and 1: -10 V."""
    connections, devices, defaults = _tables()
    devices = device.new(["coil_MOT__A", 2.0, -5, 5])  # the lockbox's entry is missing
    with pytest.raises(ValueError, match="do not describe the same apparatus"):
        console.panel(connections, devices, defaults)


def test_an_unbounded_analogue_channel_is_refused():
    connections, _, defaults = _tables()
    devices = device.new(["coil_MOT__A", 2.0], ["lockbox_MOT__MHz", 0.05, -200, 200])
    with pytest.raises(
        ValueError, match=r"none, or an infinite one: \['coil_MOT__A'\]"
    ):
        console.panel(connections, devices, defaults)


@pytest.mark.parametrize("to_V", [2.0, lambda amps: 2.0 * amps])
def test_a_value_is_converted_as_the_sequencer_converts_it(to_V):
    machine = _Machine()
    console.set_value(machine, _panel(to_V=to_V), "coil_MOT__A", 1.25)
    assert machine.written == [(4, 1, conversion.to_digits(2.5))]


def test_a_value_outside_the_devices_range_is_refused_and_not_written():
    machine = _Machine()
    with pytest.raises(ValueError, match="outside their device safety range"):
        console.set_value(machine, _panel(), "coil_MOT__A", 6.0)
    assert machine.written == []


def test_a_digital_line_takes_0_or_1():
    machine = _Machine()
    table = _panel()
    console.set_value(machine, table, "shutter_MOT", True)
    assert machine.written == [(1, 11, 1)]
    with pytest.raises(ValueError, match="takes 0 or 1"):
        console.set_value(machine, table, "shutter_MOT", 0.5)


def test_an_unknown_name_lists_the_panels():
    with pytest.raises(ValueError, match="no variable 'coil_MOT__B'"):
        console.set_value(_Machine(), _panel(), "coil_MOT__B", 1.0)


def test_a_request_while_a_sequence_owns_the_outputs_is_discarded():
    """The policy (maintainer, 2026-09-27): after a run the final state is what holds."""
    machine = _Machine()
    machine.par[wt_adwin.PAR__SEQUENCE__OWNER] = 1
    with pytest.raises(console.OutputsOwned, match="process 1, owns the outputs"):
        console.set_value(machine, _panel(), "coil_MOT__A", 1.0)
    assert console.PAR__REQUEST not in machine.par, "nothing was written"


def test_a_request_is_refused_when_the_console_is_not_running():
    """It would wait unserved; the old handshake then hung the notebook on the next one."""
    with pytest.raises(RuntimeError, match="is not running"):
        console.actuate(_Machine(running=0), 4, 1, 100)


def test_a_request_waits_for_the_previous_one_and_gives_up(monkeypatch):
    monkeypatch.setattr(console, "WAIT__MAX", 0.05)
    monkeypatch.setattr(console, "POLL__PERIOD", 0.01)
    machine = _Machine(serving=False)
    console.actuate(machine, 4, 1, 100)
    with pytest.raises(TimeoutError, match="previous request"):
        console.actuate(machine, 4, 2, 200)
    assert machine.par[console.PAR__CHANNEL] == 1, "the waiting request is intact"


@pytest.mark.parametrize("to_V", [2.0, lambda amps: 2.0 * amps])
def test_the_final_state_is_read_back_in_the_devices_units(to_V):
    machine = _Machine()
    machine.par[wt_adwin.PAR__FINISH__ANALOGUE] = 2
    machine.par[wt_adwin.PAR__FINISH__DIGITAL] = 1
    first = wt_adwin.DATA__FINISH__ANALOGUE
    machine.data[first] = [4, 3]
    machine.data[first + 1] = [1, 8]
    machine.data[first + 2] = [
        conversion.to_digits(-1.2 * 2.0),
        conversion.to_digits(120.0 * 0.05),
    ]
    machine.data[wt_adwin.DATA__FINISH__DIGITAL] = [11]
    machine.data[wt_adwin.DATA__FINISH__DIGITAL + 1] = [0]

    state = console.final_state(machine, _panel(to_V=to_V))

    assert state["coil_MOT__A"] == pytest.approx(-1.2, abs=1e-3)
    assert state["lockbox_MOT__MHz"] == pytest.approx(120.0, abs=0.01)
    assert state["shutter_MOT"] == 0


def test_health():
    machine = _Machine()
    machine.par[console.PAR__SERVED] = 5
    assert console.health(machine) == console.Health(
        workload=3, console=1, owner=0, served=5, pending=False
    )


def test_the_UI_writes_the_defaults_and_puts_a_refused_move_back():
    widgets = pytest.importorskip("ipywidgets")
    machine = _Machine()
    ui = console.create_UI(machine, _panel())

    assert sorted(machine.written) == sorted(
        [
            (1, 11, 1),
            (4, 1, conversion.to_digits(3.0)),
            (3, 8, conversion.to_digits(0.0)),
        ]
    )

    slider = next(
        w for w in ui.children[0].children if isinstance(w, widgets.FloatSlider)
    )
    assert slider.continuous_update is False, "one request per release, not per pixel"

    machine.par[wt_adwin.PAR__SEQUENCE__OWNER] = 1
    slider.value = 2.0
    assert slider.value == 1.5, "put back, since nothing was written"
    messages = ui.children[-1]
    assert "owns the outputs" in "".join(o["text"] for o in messages.outputs)
