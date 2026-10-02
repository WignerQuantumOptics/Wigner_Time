# SPDX-FileCopyrightText: 2025 András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The manual console: direct access to the apparatus's channels from a notebook, for alignment
and debugging, through `resources/ADwin/WignerTimeConsole.bas` loaded as process 10.

It works from the tables the timelines use. `panel` joins `connections` to `devices`, so a
channel is named, converted and bounded in one place only (D22). An analogue value goes
through its device's `to_V`, a function where it is one, and then through
`conversion.to_digits`, the conversion the sequencer's arrays are made with. The console
has no notion of a timeline beyond the one it takes its starting values from.

**Shadow state, not a mailbox.** `configure` writes the panel into the program as a list of
entries, one per variable. `set_value` writes one word, the digits wanted for one entry, and
returns without waiting. The program's sweep writes to the hardware wherever the wanted digits
differ from the ones last written, so repeated values coalesce and nothing on either side waits
on the other. The mailbox this replaced made Python poll `Par_73` until the program had served
the previous request, and both explanations kept for the fault in which the processor saturated
for seconds at a time involved that loop (D22).

The contract with the program, whose `#define`s must agree with the numbers below:

- `data_51[i]` / `data_52[i]`: the digits wanted for entry `i`, written here, and the digits
  last written to the hardware, written by the program. -1 in `data_52` means write again; -2 in
  either means unknown.
- `data_53[i]` / `data_54[i]`: the module and channel of entry `i`, in the panel's row order;
  module 1 is the digital one, and takes 0 or 1.
- `data_55[i]`: 1 where the program has written entry `i` since it started, which is what makes
  its value one set on the console rather than one a run left there. `jumps` reads it.
- `Par_75`: the number of entries. `configure` sets it to 0 while it rewrites them.
- `Par_78`: a token `configure` draws, so that a panel configured again elsewhere makes the old
  one refuse, rather than write its values into another panel's entries.
- `Par_74`, `Par_77`: hardware writes and sweeps since the program started, for `health`.
- `Par_76`: the value of `adwin.PAR__SEQUENCES__FINISHED` the program last saw.

**After a run.** A sequence stops the console for its run, and starts it again afterwards if it
was running. The program then adopts the run's final state (maintainer's policy, 2026-09-27):
an entry the final state names takes its digits, and one it does not name becomes unknown,
because it holds whatever the run left it at. Nothing is written to either, and anything wanted
before or during the run is discarded. `set_value` refuses while a sequence owns the outputs. A
start by hand, with no run since, writes every entry again from what was wanted.

**Before a run.** `adwin.core.upload` warns about each analogue channel set on the console that
the run will jump from its value, whether in the initial state or at the first row that commands
it (`jumps`). The MOT coils are the case in point: the lab leaves them out of the initial state,
so that the MOT stays in its steady state between runs, and the jump from a value set by hand
comes with the first stage that sets them.
"""

import importlib.util
import random
from types import SimpleNamespace
from typing import NamedTuple

import numpy as np

import wignertime.backend.adwin as wt_adwin
from wignertime.hardware import conversion
from wignertime.hardware import device
from wignertime.timeline import variable as wt_variable
from wignertime.backend.adwin import internal as wt_internal
from wignertime.internal import dataframe as wt_frame

PROCESS = 10
"""The process number in the header of `WignerTimeConsole.bas`."""

ENTRIES__MAX = 512
"""`consoleMaxEntries` in the program: 16 modules of 32 channels."""

DATA__WANTED = 51
DATA__WRITTEN = 52
DATA__MODULE = 53
DATA__CHANNEL = 54
DATA__TOUCHED = 55

PAR__WRITES = 74
PAR__ENTRIES = 75
PAR__SEQUENCES__SEEN = 76
PAR__SWEEPS = 77
PAR__TOKEN = 78

DIGITS__REASSERT = -1
DIGITS__UNKNOWN = -2

MODULE__DIGITAL = 1
"""The digital module, the only one the program switches as such (D18)."""


class OutputsOwned(RuntimeError):
    """
    A sequence owns the outputs, so a value is refused: after the run the apparatus holds the
    run's final state, and the console adopts it.
    """

    def __init__(self, owner):
        self.owner = owner
        super().__init__(
            "A sequence, process {}, owns the outputs, so the value is refused. After the run"
            " the apparatus holds its final state, which the console adopts.".format(
                owner
            )
        )


class Console(NamedTuple):
    """
    A console configured with a panel: the machine, the panel `table` whose rows are its
    entries, and the `token` that `configure` drew for it.
    """

    machine: object
    table: wt_frame.CLASS
    token: int


def panel(connections, devices, timeline__defaults):
    """
    The table the console works from: `connections` joined to `devices`, with a
    `default_value` per variable, the last value `timeline__defaults` gives it (normally the
    lab's `experiment.init()`).

    The two tables must describe the same apparatus (`device.check_correspondence`). Here
    that matters more than anywhere: a variable with no device is taken for a digital line,
    so an analogue channel whose device name was mistyped would be switched between digits
    0 and 1, that is, to -10 V. Every analogue variable needs finite bounds, which are its
    slider's range.

    A variable the defaults do not mention keeps NaN as its `default_value`, is reported, and is
    left as it is: `configure` writes nothing to it until it is set. The lab leaves the MOT coils
    and the dispenser out of its initial state so that the MOT stays in its steady state between
    runs, and building the console should not undo that.
    """
    device.check_correspondence(connections, devices)
    # The program switches module 1 as digital and writes every other one as analogue, so a
    # variable of the other kind there would be written as the wrong kind: a digital line on
    # an analogue module goes to its DAC as the digits 0 or 1, that is, -10 V (A16, D18).
    wt_internal.check_module_kinds(connections, [MODULE__DIGITAL])
    table = wt_frame.join(connections, devices)

    analogue = ~wt_frame.isnull(wt_frame.column(table, "to_V"))
    bounded = np.isfinite(
        wt_frame.column(table, "value__min", dtype=float)
    ) & np.isfinite(wt_frame.column(table, "value__max", dtype=float))
    unbounded = wt_frame.column(table, "variable")[analogue & ~bounded]
    if len(unbounded):
        raise ValueError(
            "The console bounds each analogue slider by its device's `value__min` and"
            " `value__max`, and these have none, or an infinite one: {}.".format(
                sorted(unbounded)
            )
        )

    # Sorted stably, so the last written wins; a null value is passed over, as pandas'
    # `last` did.
    last = {}
    for name, value in wt_frame.rows(
        wt_frame.sort(timeline__defaults, "time"), ["variable", "value"]
    ):
        if not wt_frame.isnull(value):
            last[name] = value
        else:
            last.setdefault(name, value)
    defaults = wt_frame.new(
        {"variable": sorted(last), "default_value": [last[n] for n in sorted(last)]}
    )
    table = wt_frame.join(table, defaults)

    missing = sorted(
        wt_frame.column(table, "variable")[
            wt_frame.isnull(wt_frame.column(table, "default_value"))
        ]
    )
    if missing:
        print(
            "console: the defaults give no value for {}; the console leaves them as they are"
            " until they are set.".format(missing)
        )

    return table


def to_digits(value, to_V):
    """The digits for `value` of a device with conversion `to_V`, as the sequencer gets them."""
    voltage = to_V(value) if callable(to_V) else value * to_V
    return int(conversion.to_digits(voltage))


def from_digits(row, digits):
    """
    The value of the panel's `row` whose digits are `digits`. The digits give the voltage
    exactly, as `conversion.to_digits` is linear. A linear `to_V` then gives the value; a
    calibration function, which cannot in general be inverted, is inverted by interpolation
    over the row's range, which assumes that it is monotonic there.
    """
    specification = conversion.SPECIFICATIONS__DEFAULT
    v_min, v_max = np.asarray(specification["voltage_range"]) / specification["gain"]
    step = (v_max - v_min) / (2 ** specification["num_bits"] - 1)
    voltage = v_min + digits * step
    # 0 V falls on the boundary between two codes, and is read back as 0 rather than as the
    # middle of the code it was rounded to, half a step away.
    if abs(voltage) <= step / 2:
        voltage = 0.0
    if not callable(row.to_V):
        return float(voltage / row.to_V)

    grid = np.linspace(row.value__min, row.value__max, 4097)
    voltages = np.vectorize(row.to_V)(grid)
    order = np.argsort(voltages)
    return float(np.interp(voltage, voltages[order], grid[order]))


def _records(table):
    """Each row of the panel, with its columns as attributes."""
    names = wt_frame.columns(table)
    return [SimpleNamespace(**dict(zip(names, row))) for row in wt_frame.rows(table)]


def _index(table, name):
    variables = wt_frame.column(table, "variable")
    positions = np.flatnonzero(variables == name)
    if not len(positions):
        raise ValueError(
            "The panel has no variable {!r}. It has: {}.".format(
                name, sorted(variables)
            )
        )
    return int(positions[0])


def _digits(table, name, value):
    """
    The entry index and digits for setting `name` to `value`: 0 or 1 for a digital line, and
    for an analogue one a value inside its device's range, checked by
    `device.check_within_range` as a timeline's values are.
    """
    index = _index(table, name)
    row = wt_frame.row(table, index)
    if wt_frame.isnull(row["to_V"]):
        if value not in (0, 1):
            raise ValueError(
                "{} is a digital line, so it takes 0 or 1, not {!r}.".format(
                    name, value
                )
            )
        return index, int(value)

    device.check_within_range(
        wt_frame.new(
            {
                "variable": [name],
                "value": [float(value)],
                "value__min": [row["value__min"]],
                "value__max": [row["value__max"]],
            }
        )
    )
    return index, to_digits(value, row["to_V"])


def configure(machine, table):
    """
    Writes the panel into the console program as its entries, each wanting its
    `default_value`, and returns the `Console`. The program writes them to the hardware, except
    the variables without a default, which are unknown until they are set.

    The entries are rewritten with their count at 0, so that the program never sweeps a
    half-written list, and a fresh token is drawn. A run finished before this does not count
    as one the program has yet to adopt, since these values are newer.
    """
    owner = machine.Get_Par(wt_adwin.PAR__SEQUENCE__OWNER)
    if owner:
        raise OutputsOwned(owner)
    if len(table) > ENTRIES__MAX:
        raise ValueError(
            "The console holds at most {} entries, and this panel has {}.".format(
                ENTRIES__MAX, len(table)
            )
        )

    wanted = [
        DIGITS__UNKNOWN if wt_frame.isnull(value) else _digits(table, name, value)[1]
        for name, value in wt_frame.rows(table, ["variable", "default_value"])
    ]
    count = len(table)
    machine.Set_Par(PAR__ENTRIES, 0)
    for number, values in (
        (DATA__MODULE, [int(m) for m in wt_frame.column(table, "module")]),
        (DATA__CHANNEL, [int(c) for c in wt_frame.column(table, "channel")]),
        (DATA__WANTED, wanted),
        (DATA__WRITTEN, [DIGITS__REASSERT] * count),
        (DATA__TOUCHED, [0] * count),
    ):
        machine.SetData_Long(values, number, 1, count)
    machine.Set_Par(
        PAR__SEQUENCES__SEEN, machine.Get_Par(wt_adwin.PAR__SEQUENCES__FINISHED)
    )
    token = random.randrange(1, 2**31 - 1)
    machine.Set_Par(PAR__TOKEN, token)
    machine.Set_Par(PAR__ENTRIES, count)
    return Console(machine, table, token)


def set_value(console, name, value):
    """
    Sets the variable `name` to `value`, in its own unit, and returns without waiting: the
    program writes it to the hardware within a sweep or two.

    Refuses while a sequence owns the outputs (`OutputsOwned`), when the console process is
    not running, and when the console has been configured again since `console` was, from this
    notebook or another, since its entries are then another panel's.
    """
    machine = console.machine
    owner = machine.Get_Par(wt_adwin.PAR__SEQUENCE__OWNER)
    if owner:
        raise OutputsOwned(owner)
    if machine.Get_Par(PAR__TOKEN) != console.token:
        raise RuntimeError(
            "The console has been configured again since this panel was, so its entries are"
            " another panel's. Configure it again, or rebuild the widgets."
        )
    if machine.Process_Status(PROCESS) == 0:
        raise RuntimeError(
            "The console, process {}, is not running, so nothing would write the value. Load"
            " `WignerTimeConsole.bas` and start it.".format(PROCESS)
        )

    index, digits = _digits(console.table, name, value)
    machine.SetData_Long([digits], DATA__WANTED, index + 1, 1)


def readback(console):
    """
    What the console program holds for each variable of the panel: a frame of `variable`,
    `value` (NaN where unknown), and `pending`, true where the value wanted has not yet been
    written to the hardware. That should last a sweep or two at most.

    After a run, this is the final state the program adopted, and NaN for the variables the
    final state does not name.
    """
    machine, table = console.machine, console.table
    count = len(table)
    wanted = np.asarray(machine.GetData_Long(DATA__WANTED, 1, count))
    written = np.asarray(machine.GetData_Long(DATA__WRITTEN, 1, count))

    values = []
    for row, digits in zip(_records(table), wanted):
        if digits == DIGITS__UNKNOWN:
            values.append(np.nan)
        elif wt_frame.isnull(row.to_V):
            values.append(float(digits))
        else:
            values.append(from_digits(row, digits))

    return wt_frame.new(
        {
            "variable": list(wt_frame.column(table, "variable")),
            "value": values,
            "pending": list((wanted >= 0) & (wanted != written)),
        }
    )


def final_state(machine, table):
    """
    The final state of the last upload, as `{variable: value}` for the variables of the
    `panel` it sets, read from the arrays `upload` writes for the sequencer's `finish:`.
    """
    by_port = {(row.module, row.channel): row for row in _records(table)}
    state = {}

    count = machine.Get_Par(wt_adwin.PAR__FINISH__ANALOGUE)
    if count:
        first = wt_adwin.DATA__FINISH__ANALOGUE
        modules, channels, digits = (
            np.asarray(machine.GetData_Long(first + i, 1, count)) for i in range(3)
        )
        for module, channel, digit in zip(modules, channels, digits):
            row = by_port.get((int(module), int(channel)))
            if row is not None:
                state[row.variable] = from_digits(row, digit)

    count = machine.Get_Par(wt_adwin.PAR__FINISH__DIGITAL)
    if count:
        first = wt_adwin.DATA__FINISH__DIGITAL
        channels, values = (
            np.asarray(machine.GetData_Long(first + i, 1, count)) for i in range(2)
        )
        for channel, value in zip(channels, values):
            row = by_port.get((MODULE__DIGITAL, int(channel)))
            if row is not None:
                state[row.variable] = int(value)

    return state


class Jump(NamedTuple):
    """
    An analogue channel that a run will move, at once, from a value set on the console: the
    `variable`, the value it `held`, the value the run first `commanded`, both in its own unit,
    and the `cycle` at which the run does so, negative for the initial state.
    """

    variable: str
    held: float
    commanded: float
    cycle: int


def jumps(machine, analogue, connections, devices):
    """
    The `Jump`s of a run whose analogue rows are `analogue`, as `adwin.core.convert` gives them:
    each analogue channel that holds a value written by the console since it last started, and
    whose first value in the run differs from it by more than one DAC step.

    Only values the console wrote count. After a run the console holds the run's final state,
    and a jump from that is part of the sequence, not a surprise. Nothing is reported when the
    console has not yet seen the last run that finished, because its record is then older than
    what the apparatus holds.
    """
    count = machine.Get_Par(PAR__ENTRIES)
    seen = machine.Get_Par(PAR__SEQUENCES__SEEN)
    if not count or seen != machine.Get_Par(wt_adwin.PAR__SEQUENCES__FINISHED):
        return []

    first = {}
    for cycle, module, channel, digits in analogue:
        if cycle != wt_adwin.CONTEXTS__SPECIAL["ADwin_Finish"]:
            first.setdefault((int(module), int(channel)), (int(cycle), int(digits)))

    table = wt_frame.join(connections, devices)
    by_port = {(int(r.module), int(r.channel)): r for r in _records(table)}
    modules, channels, written, touched = (
        np.asarray(machine.GetData_Long(number, 1, count))
        for number in (DATA__MODULE, DATA__CHANNEL, DATA__WRITTEN, DATA__TOUCHED)
    )

    found = []
    for module, channel, held, mark in zip(modules, channels, written, touched):
        port = (int(module), int(channel))
        if not mark or held < 0 or port not in first or port not in by_port:
            continue
        cycle, digits = first[port]
        if abs(digits - held) > 1:
            row = by_port[port]
            found.append(
                Jump(
                    row.variable,
                    from_digits(row, held),
                    from_digits(row, digits),
                    cycle,
                )
            )
    return found


class Health(NamedTuple):
    """
    A snapshot of the machine as the console sees it. `workload` is ADwin's processor workload
    in percent, `sweeps` the program's heartbeat and `writes` its hardware writes since it
    started. They are for the fault reported in the lab, the processor saturating for seconds
    at a time while the console is in use: sampled over a session, they date an episode, and
    show whether the console was writing while it lasted.
    """

    workload: int
    console: int
    owner: int
    entries: int
    sweeps: int
    writes: int


def health(machine):
    """The console's `Health` now."""
    return Health(
        workload=machine.Workload(),
        console=machine.Process_Status(PROCESS),
        owner=machine.Get_Par(wt_adwin.PAR__SEQUENCE__OWNER),
        entries=machine.Get_Par(PAR__ENTRIES),
        sweeps=machine.Get_Par(PAR__SWEEPS),
        writes=machine.Get_Par(PAR__WRITES),
    )


def create_UI(machine, table, continuous_update=True):
    """
    Configures the console with the `panel` and returns its widgets: a vertical slider per
    analogue variable, a toggle per digital line, a button that shows what the program holds,
    and a line for messages. Configuring writes every default to the apparatus; a variable
    without one is marked as unknown and left as it is.

    A slider sends its value while it is dragged, since a write costs one driver call and
    repeated values coalesce in the program. `continuous_update=False` sends it on release.

    A value that is refused, because a sequence owns the outputs or the console is not
    running, puts the widget back and says why, so that the widgets show what was asked for.
    After a run the widgets are brought up to the adopted final state at the next move, or
    with the button. A variable the final state does not name is marked, since what it
    holds is unknown until it is set.
    """
    if not importlib.util.find_spec("ipywidgets"):
        raise ImportError("The console's widgets require `ipywidgets` to be installed.")
    import ipywidgets as widgets

    console = configure(machine, table)
    messages = widgets.Output()
    quiet = {"on": False}  # set while widgets are moved from here rather than by hand
    adopted = {"seen": machine.Get_Par(PAR__SEQUENCES__SEEN)}
    controls = {}

    def mark(control, unknown):
        if isinstance(control, widgets.ToggleButton):
            control.button_style = "warning" if unknown else ""
        else:
            control.style.handle_color = "orange" if unknown else None

    def refresh(_=None):
        adopted["seen"] = machine.Get_Par(PAR__SEQUENCES__SEEN)
        held = readback(console)
        unknown = []
        quiet["on"] = True
        try:
            for name, value in wt_frame.rows(held, ["variable", "value"]):
                control = controls[name]
                if np.isnan(value):
                    unknown.append(name)
                else:
                    is_toggle = isinstance(control, widgets.ToggleButton)
                    control.value = bool(value) if is_toggle else value
                mark(control, np.isnan(value))
        finally:
            quiet["on"] = False
        messages.append_stdout(
            "Showing what the console holds. Unknown after the last run: {}.\n".format(
                ", ".join(unknown) or "nothing"
            )
        )

    def observe(control, name):
        def on_change(change):
            if quiet["on"]:
                return
            if machine.Get_Par(PAR__SEQUENCES__SEEN) != adopted["seen"]:
                refresh()
            try:
                set_value(console, name, change["new"])
            except RuntimeError as refused:
                quiet["on"] = True
                try:
                    control.value = change["old"]
                finally:
                    quiet["on"] = False
                messages.append_stdout("{}: {}\n".format(name, refused))
                return
            mark(control, False)

        control.observe(on_change, names="value")

    sliders, toggles = [], [[], [], []]
    for row in _records(table):
        unknown = wt_frame.isnull(row.default_value)
        if wt_frame.isnull(row.to_V):
            control = widgets.ToggleButton(
                value=False if unknown else bool(row.default_value),
                description=row.variable,
                layout=widgets.Layout(margin="20px 5px"),
            )
            group = {"shutter": 0, "AOM": 1}.get(row.variable.split("_", 1)[0], 2)
            toggles[group].append(control)
        else:
            control = widgets.FloatSlider(
                value=(
                    min(max(0.0, row.value__min), row.value__max)
                    if unknown
                    else row.default_value
                ),
                min=row.value__min,
                max=row.value__max,
                step=0.01,
                description="{}\n({})".format(
                    wt_variable.without_unit(row.variable),
                    wt_variable.unit(row.variable),
                ),
                orientation="vertical",
                continuous_update=continuous_update,
                layout=widgets.Layout(margin="20px 40px", height="300px"),
            )
            sliders.append(control)
        observe(control, row.variable)
        controls[row.variable] = control
        mark(control, unknown)

    button = widgets.Button(description="Refresh")
    button.on_click(refresh)

    return widgets.VBox(
        [widgets.HBox(sliders), *[widgets.HBox(t) for t in toggles], button, messages]
    )
