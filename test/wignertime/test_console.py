import numpy as np
import pytest

import wignertime.adwin as wt_adwin
from wignertime import conversion
from wignertime import device
from wignertime import timeline as tl
from wignertime.adwin import connection as adcon
from wignertime.adwin import console

OWNER = wt_adwin.PAR__SEQUENCE__OWNER
FINISHED = wt_adwin.PAR__SEQUENCES__FINISHED


class _Machine:
    """
    Stands in for `ADwin.ADwin` with `WignerTimeConsole.bas` loaded as process 10, and plays
    the program line for line: `start` is its `init:`, `sweep` one `event:`, and `sequence` a
    run of a sequencer, from its `lowinit:` to its `finish:`. `hardware` records what reached
    the outputs, as (module, channel, digits).
    """

    MAX_WRITES_PER_SWEEP = 8  # maxWritesPerSweep

    def __init__(self):
        self.par, self.data, self.hardware = {}, {}, []
        self.running = 0

    # the driver
    def Get_Par(self, number):
        return self.par.get(number, 0)

    def Set_Par(self, number, value):
        self.par[number] = value

    def SetData_Long(self, values, number, startindex, count):
        array = self.data.setdefault(number, [0] * console.ENTRIES__MAX)
        array[startindex - 1 : startindex - 1 + count] = list(values)[:count]

    def GetData_Long(self, number, startindex, count):
        return self.data.get(number, [0] * console.ENTRIES__MAX)[
            startindex - 1 : startindex - 1 + count
        ]

    def Process_Status(self, process):
        return self.running

    def Workload(self):
        return 3

    # the program
    def _array(self, number):
        return self.data.setdefault(number, [0] * console.ENTRIES__MAX)

    def start(self):
        self.running = 1
        wanted, written = self._array(51), self._array(52)
        modules, channels = self._array(53), self._array(54)
        par = self.par
        for i in range(par.get(75, 0)):
            self._array(55)[i] = 0
        if par.get(FINISHED, 0) != par.get(76, 0):
            analogue = [self._array(31 + k) for k in range(3)]
            digital = [self._array(42 + k) for k in range(2)]
            for i in range(par.get(75, 0)):
                wanted[i] = written[i] = -2
                if modules[i] == 1:
                    for f in range(par.get(16, 0)):
                        if digital[0][f] == channels[i]:
                            wanted[i] = written[i] = digital[1][f]
                else:
                    for f in range(par.get(15, 0)):
                        if (analogue[0][f], analogue[1][f]) == (
                            modules[i],
                            channels[i],
                        ):
                            wanted[i] = written[i] = analogue[2][f]
            par[76] = par.get(FINISHED, 0)
        else:
            for i in range(par.get(75, 0)):
                written[i] = -1

    def sweep(self):
        if not self.running or self.par.get(OWNER, 0):
            return
        wanted, written = self._array(51), self._array(52)
        modules, channels = self._array(53), self._array(54)
        writes = 0
        for i in range(self.par.get(75, 0)):
            digits = wanted[i]
            if (
                digits >= 0
                and digits != written[i]
                and writes < self.MAX_WRITES_PER_SWEEP
            ):
                self.hardware.append((modules[i], channels[i], digits))
                written[i] = digits
                self._array(55)[i] = 1
                writes += 1

    def sequence(self, analogue__finish=(), digital__finish=(), during=None):
        """A run whose final state is these rows, as `upload` writes them."""
        was = self.running
        self.par[OWNER] = 1
        self.running = 0
        for k in range(3):
            self.SetData_Long([r[k] for r in analogue__finish], 31 + k, 1, 256)
        for k in range(2):
            self.SetData_Long([r[k] for r in digital__finish], 42 + k, 1, 256)
        self.par[15], self.par[16] = len(analogue__finish), len(digital__finish)
        if during:
            during(self)
        self.hardware += [r for r in analogue__finish]
        self.hardware += [(1, c, v) for c, v in digital__finish]
        self.par[FINISHED] = self.par.get(FINISHED, 0) + 1
        self.par[OWNER] = 0
        if was:
            self.start()


def _tables(to_V=2.0):
    connections = adcon.new(
        ["shutter__MOT", 1, 11], ["coil__MOT__A", 4, 1], ["lockbox__MOT__MHz", 3, 8]
    )
    devices = device.new(
        ["coil__MOT__A", to_V, -5, 5], ["lockbox__MOT__MHz", 0.05, -200, 200]
    )
    defaults = tl.to_timeline(
        tl.update(shutter__MOT=1, coil__MOT__A=1.5, time=0.0, context="init")
    )
    return connections, devices, defaults


def _panel(**kw):
    return console.panel(*_tables(**kw))


def _configured(**kw):
    machine = _Machine()
    machine.start()
    return machine, console.configure(machine, _panel(**kw))


DEFAULTS = [(1, 11, 1), (4, 1, conversion.to_digits(3.0))]  # the lockbox has none


# The panel


def test_the_panel_takes_its_defaults_from_the_timeline(capsys):
    table = _panel()
    values = dict(zip(table["variable"], table["default_value"]))
    assert values["shutter__MOT"] == 1.0 and values["coil__MOT__A"] == 1.5
    assert np.isnan(values["lockbox__MOT__MHz"]), "no default: left as it is"
    assert "lockbox__MOT__MHz" in capsys.readouterr().out, "the missing one is reported"


def test_a_variable_without_a_default_is_left_alone_and_unknown():
    """
    The lab leaves the MOT coils out of its initial state, so that the MOT stays in its steady
    state between runs, and building the console should not set them to 0.
    """
    machine, panel = _configured()
    machine.sweep()
    assert (3, 8) not in [(m, c) for m, c, _ in machine.hardware]
    assert np.isnan(console.readback(panel)["value"][2])


def test_an_analogue_channel_without_a_device_is_refused():
    """It would be taken for a digital line, and switched between digits 0 and 1: -10 V."""
    connections, devices, defaults = _tables()
    devices = device.new(["coil__MOT__A", 2.0, -5, 5])  # the lockbox's entry is missing
    with pytest.raises(ValueError, match="do not describe the same apparatus"):
        console.panel(connections, devices, defaults)


def test_a_digital_line_on_an_analogue_module_is_refused():
    """The program would write it to the DAC as the digits 0 or 1: -10 V (A16)."""
    connections, devices, defaults = _tables()
    connections = adcon.new(
        ["shutter__MOT", 3, 11], ["coil__MOT__A", 4, 1], ["lockbox__MOT__MHz", 3, 8]
    )
    with pytest.raises(
        ValueError, match="shutter__MOT on module 3: digital by its name"
    ):
        console.panel(connections, devices, defaults)


def test_an_unbounded_analogue_channel_is_refused():
    connections, _, defaults = _tables()
    devices = device.new(["coil__MOT__A", 2.0], ["lockbox__MOT__MHz", 0.05, -200, 200])
    with pytest.raises(
        ValueError, match=r"none, or an infinite one: \['coil__MOT__A'\]"
    ):
        console.panel(connections, devices, defaults)


# Configuring, and the sweep


def test_configuring_writes_the_entries_with_their_count_last():
    machine = _Machine()
    calls = []
    set_par = machine.Set_Par
    machine.Set_Par = lambda n, v: (calls.append((n, v)), set_par(n, v))
    console.configure(machine, _panel())

    assert calls[0] == (
        console.PAR__ENTRIES,
        0,
    ), "nothing is swept while it is rewritten"
    assert calls[-1] == (console.PAR__ENTRIES, 3)
    assert machine.data[console.DATA__MODULE][:3] == [1, 4, 3]
    assert machine.data[console.DATA__WRITTEN][:3] == [-1, -1, -1]


def test_the_sweep_writes_the_defaults_then_nothing():
    machine, _ = _configured()
    machine.sweep()
    assert machine.hardware == DEFAULTS
    machine.sweep()
    assert machine.hardware == DEFAULTS, "written once"


def test_a_sweep_writes_at_most_eight():
    connections = adcon.new(*[["shutter__{}".format(i), 1, i] for i in range(1, 11)])
    defaults = tl.to_timeline(
        tl.update(
            **{"shutter__{}".format(i): 0 for i in range(1, 11)},
            time=0.0,
            context="init"
        )
    )
    table = console.panel(connections, device.new(), defaults)
    machine = _Machine()
    machine.start()
    console.configure(machine, table)
    machine.sweep()
    assert len(machine.hardware) == 8
    machine.sweep()
    assert len(machine.hardware) == 10


# Setting values


@pytest.mark.parametrize("to_V", [2.0, lambda amps: 2.0 * amps])
def test_a_value_is_converted_as_the_sequencer_converts_it(to_V):
    machine, panel = _configured(to_V=to_V)
    console.set_value(panel, "coil__MOT__A", 1.25)
    assert machine.data[console.DATA__WANTED][1] == conversion.to_digits(2.5)


def test_values_coalesce_and_nothing_waits():
    """Two values before a sweep are one write: intermediate slider positions never reach it."""
    machine, panel = _configured()
    machine.sweep()
    console.set_value(panel, "coil__MOT__A", 1.0)
    console.set_value(panel, "coil__MOT__A", 2.0)
    machine.sweep()
    assert machine.hardware[len(DEFAULTS) :] == [(4, 1, conversion.to_digits(4.0))]


def test_a_value_outside_the_devices_range_is_refused_and_not_written():
    machine, panel = _configured()
    with pytest.raises(ValueError, match="outside their device safety range"):
        console.set_value(panel, "coil__MOT__A", 6.0)
    assert machine.data[console.DATA__WANTED][1] == conversion.to_digits(3.0)


def test_a_digital_line_takes_0_or_1():
    machine, panel = _configured()
    console.set_value(panel, "shutter__MOT", False)
    assert machine.data[console.DATA__WANTED][0] == 0
    with pytest.raises(ValueError, match="takes 0 or 1"):
        console.set_value(panel, "shutter__MOT", 0.5)


def test_an_unknown_name_lists_the_panels():
    _, panel = _configured()
    with pytest.raises(ValueError, match="no variable 'coil__MOT__B'"):
        console.set_value(panel, "coil__MOT__B", 1.0)


def test_a_value_while_a_sequence_owns_the_outputs_is_refused():
    machine, panel = _configured()
    machine.par[OWNER] = 1
    with pytest.raises(console.OutputsOwned, match="process 1, owns the outputs"):
        console.set_value(panel, "coil__MOT__A", 1.0)


def test_a_value_is_refused_when_the_console_is_not_running():
    machine, panel = _configured()
    machine.running = 0
    with pytest.raises(RuntimeError, match="is not running"):
        console.set_value(panel, "coil__MOT__A", 1.0)


def test_a_panel_configured_again_elsewhere_refuses():
    """Its entries are then another panel's, and its values would land on other channels."""
    machine, panel = _configured()
    console.configure(machine, _panel())
    with pytest.raises(RuntimeError, match="configured again"):
        console.set_value(panel, "coil__MOT__A", 1.0)


# After a run


FINAL = dict(
    analogue__finish=[(4, 1, conversion.to_digits(-1.2 * 2.0))],  # the coil
    digital__finish=[(11, 0)],  # the shutter
)


def test_after_a_run_the_console_adopts_the_final_state_and_writes_nothing():
    machine, panel = _configured()
    machine.sweep()
    hardware = list(machine.hardware)

    machine.sequence(**FINAL)
    machine.sweep()

    assert machine.hardware == hardware + [
        (4, 1, FINAL["analogue__finish"][0][2]),
        (1, 11, 0),
    ]
    held = console.readback(panel)
    values = dict(zip(held["variable"], held["value"]))
    assert values["coil__MOT__A"] == pytest.approx(-1.2, abs=1e-3)
    assert values["shutter__MOT"] == 0
    assert np.isnan(
        values["lockbox__MOT__MHz"]
    ), "not named by the final state: unknown"
    assert not held["pending"].any()


def test_a_value_wanted_just_before_the_run_is_discarded():
    """Written, then the sequence took the outputs before a sweep: the final state holds."""
    machine, panel = _configured()
    machine.sweep()
    console.set_value(panel, "coil__MOT__A", 4.0)
    machine.sequence(**FINAL)
    machine.sweep()
    assert (4, 1, conversion.to_digits(8.0)) not in machine.hardware


def test_a_start_by_hand_writes_every_entry_again():
    """The students' habit of restarting the console keeps working: it repairs the outputs."""
    machine, _ = _configured()
    machine.sweep()
    machine.start()
    machine.sweep()
    assert machine.hardware == DEFAULTS + DEFAULTS


def test_an_unknown_entry_is_never_written_as_digits():
    """After an adoption, a start by hand writes the known entries again, and not -2."""
    machine, _ = _configured()
    machine.sequence(**FINAL)
    machine.start()
    machine.sweep()
    assert all(digits >= 0 for _, _, digits in machine.hardware)


def test_a_console_closed_during_the_run_adopts_when_it_is_started():
    machine, panel = _configured()
    machine.running = 0
    machine.sequence(**FINAL)
    machine.start()
    held = console.readback(panel)
    assert np.isnan(held["value"][2])
    assert held["value"][1] == pytest.approx(-1.2, abs=1e-3)


@pytest.mark.parametrize("to_V", [2.0, lambda amps: 2.0 * amps])
def test_the_final_state_is_read_back_in_the_devices_units(to_V):
    machine = _Machine()
    machine.sequence(
        analogue__finish=[
            (4, 1, conversion.to_digits(-1.2 * 2.0)),
            (3, 8, conversion.to_digits(120.0 * 0.05)),
        ],
        digital__finish=[(11, 0)],
    )
    state = console.final_state(machine, _panel(to_V=to_V))
    assert state["coil__MOT__A"] == pytest.approx(-1.2, abs=1e-3)
    assert state["lockbox__MOT__MHz"] == pytest.approx(120.0, abs=0.01)
    assert state["shutter__MOT"] == 0


# Jumps, before a run


def _run(coil, lockbox=None):
    """The analogue rows of a run: the coil first set at t = 0, the lockbox in the initial state."""
    rows = [(0, 4, 1, conversion.to_digits(coil * 2.0))]
    if lockbox is not None:
        rows.insert(0, (-2, 3, 8, conversion.to_digits(lockbox * 0.05)))
    return rows + [(wt_adwin.CONTEXTS__SPECIAL["ADwin_Finish"], 4, 1, 0)]


def test_a_value_set_on_the_console_that_the_run_jumps_is_found():
    machine, panel = _configured()
    machine.sweep()  # the coil at its default, 1.5 A
    console.set_value(panel, "coil__MOT__A", 2.0)
    machine.sweep()

    (jump,) = console.jumps(machine, _run(coil=-1.5), *_tables()[:2])
    assert jump.variable == "coil__MOT__A" and jump.cycle == 0
    assert (jump.held, jump.commanded) == (
        pytest.approx(2.0, abs=1e-3),
        pytest.approx(-1.5, abs=1e-3),
    )


def test_a_run_that_starts_where_the_console_left_a_channel_jumps_nothing():
    machine, panel = _configured()
    machine.sweep()
    assert console.jumps(machine, _run(coil=1.5), *_tables()[:2]) == []


def test_after_a_run_the_adopted_state_is_not_a_jump():
    """In a scan, each shot starting from the last one's final state would otherwise warn."""
    machine, panel = _configured()
    machine.sweep()
    machine.sequence(analogue__finish=[(4, 1, conversion.to_digits(-1.2 * 2.0))])
    assert console.jumps(machine, _run(coil=-1.5), *_tables()[:2]) == []


def test_a_jump_in_the_initial_state_is_found_too():
    machine, panel = _configured()
    machine.sweep()
    console.set_value(panel, "lockbox__MOT__MHz", 50.0)
    machine.sweep()
    (jump,) = console.jumps(machine, _run(coil=1.5, lockbox=0.0), *_tables()[:2])
    assert jump.variable == "lockbox__MOT__MHz" and jump.cycle < 0


def test_a_console_that_has_not_seen_the_last_run_reports_nothing():
    """Closed during a run, its record is older than what the apparatus holds."""
    machine, panel = _configured()
    machine.sweep()
    console.set_value(panel, "coil__MOT__A", 2.0)
    machine.sweep()
    machine.running = 0
    machine.sequence()
    assert console.jumps(machine, _run(coil=-1.5), *_tables()[:2]) == []


def test_health():
    machine, _ = _configured()
    machine.par[console.PAR__SWEEPS], machine.par[console.PAR__WRITES] = 40, 3
    assert console.health(machine) == console.Health(
        workload=3, console=1, owner=0, entries=3, sweeps=40, writes=3
    )


# The widgets


def _ui(machine):
    widgets = pytest.importorskip("ipywidgets")
    ui = console.create_UI(machine, _panel())
    sliders = [w for w in ui.children[0].children if isinstance(w, widgets.FloatSlider)]
    toggles = [w for box in ui.children[1:4] for w in box.children]
    return ui, dict(zip(["coil__MOT__A", "lockbox__MOT__MHz"], sliders)), toggles


def _messages(ui):
    return "".join(o["text"] for o in ui.children[-1].outputs)


def test_the_UI_configures_the_console_and_sends_while_dragging():
    machine = _Machine()
    machine.start()
    ui, sliders, _ = _ui(machine)
    machine.sweep()
    assert machine.hardware == DEFAULTS
    assert sliders["coil__MOT__A"].continuous_update is True


def test_the_UI_puts_a_refused_move_back():
    machine = _Machine()
    machine.start()
    ui, sliders, _ = _ui(machine)
    machine.par[OWNER] = 1
    sliders["coil__MOT__A"].value = 2.0
    assert sliders["coil__MOT__A"].value == 1.5, "put back, since nothing was written"
    assert "owns the outputs" in _messages(ui)


def test_the_UI_catches_up_with_a_run_at_the_next_move():
    machine = _Machine()
    machine.start()
    ui, sliders, toggles = _ui(machine)
    machine.sweep()
    machine.sequence(**FINAL)

    sliders["lockbox__MOT__MHz"].value = 10.0

    assert sliders["coil__MOT__A"].value == pytest.approx(-1.2, abs=0.01)
    assert toggles[0].value is False, "the shutter as the final state left it"
    assert "Unknown after the last run: lockbox__MOT__MHz" in _messages(ui)
    assert (
        sliders["lockbox__MOT__MHz"].style.handle_color is None
    ), "known again once set"
    assert machine.data[console.DATA__WANTED][2] == conversion.to_digits(10.0 * 0.05)
