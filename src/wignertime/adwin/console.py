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

The contract with the program:

- `Par_70`, `Par_71`, `Par_72`: the module, channel and digits of one request, and `Par_73`,
  nonzero while it waits to be served. The program serves it and clears `Par_73`. A request
  is written only once the previous one is served, so the program never reads half of one.
- `Par_74`: how many requests the program has served since it was started.
- `Par_17` (`adwin.PAR__SEQUENCE__OWNER`): nonzero while a sequence owns the outputs. A
  sequence stops the console for its run and starts it again afterwards, and the apparatus
  then holds the run's final state. A request made meanwhile is discarded (maintainer,
  2026-09-27). `actuate` refuses to write one, and the program's `init:` drops one that was
  written in the instant before the sequence took the outputs.
"""

import importlib.util
import time
from typing import NamedTuple

import numpy as np

import wignertime.adwin as wt_adwin
from wignertime import conversion
from wignertime import device
from wignertime import variable as wt_variable
from wignertime.internal import dataframe as wt_frame

PROCESS = 10
"""The process number in the header of `WignerTimeConsole.bas`."""

PAR__MODULE = 70
PAR__CHANNEL = 71
PAR__DIGITS = 72
PAR__REQUEST = 73
PAR__SERVED = 74

WAIT__MAX = 1.0
"""How long `actuate` waits for the previous request to be served, in seconds."""

POLL__PERIOD = 0.01

MODULE__DIGITAL = 1
"""The digital module, the only one the program switches as such (D18)."""


class OutputsOwned(RuntimeError):
    """
    A sequence owns the outputs, so a request is discarded: after the run the apparatus
    holds the run's final state, and a move made during it does not follow.
    """

    def __init__(self, owner):
        self.owner = owner
        super().__init__(
            "A sequence, process {}, owns the outputs, so the request is discarded. After"
            " the run the apparatus holds its final state; `final_state` reads it back.".format(
                owner
            )
        )


def panel(connections, devices, timeline__defaults):
    """
    The table the console works from: `connections` joined to `devices`, with a
    `default_value` per variable, the last value `timeline__defaults` gives it (normally the
    lab's `experiment.init()`).

    The two tables must describe the same apparatus (`device.check_correspondence`). Here
    that matters more than anywhere: a variable with no device is taken for a digital line,
    so an analogue channel whose device name was mistyped would be switched between digits
    0 and 1, that is, to -10 V. Every analogue variable needs finite bounds, which are its
    slider's range. A channel the defaults do not mention starts at 0, and is reported.
    """
    device.check_correspondence(connections, devices)
    table = wt_frame.join(connections, devices)

    analogue = table["to_V"].notna()
    unbounded = table.loc[
        analogue
        & ~(np.isfinite(table["value__min"]) & np.isfinite(table["value__max"])),
        "variable",
    ]
    if len(unbounded):
        raise ValueError(
            "The console bounds each analogue slider by its device's `value__min` and"
            " `value__max`, and these have none, or an infinite one: {}.".format(
                sorted(unbounded)
            )
        )

    defaults = (
        timeline__defaults.sort_values("time")
        .groupby("variable")["value"]
        .last()
        .rename("default_value")
        .reset_index()
    )
    table = wt_frame.join(table, defaults)

    missing = sorted(table.loc[table["default_value"].isna(), "variable"])
    if missing:
        print(
            "console: the defaults give no value for {}; they start at 0.".format(
                missing
            )
        )
    table["default_value"] = table["default_value"].fillna(0.0)

    return table


def actuate(machine, module, channel, digits):
    """
    Asks the console to write `digits` to `channel` of `module`, and returns once the
    request is written, not once it is served.

    Refuses while a sequence owns the outputs (`OutputsOwned`), and when the console process
    is not running, since the request would then wait unserved. Waits for the previous
    request to be served, at most `WAIT__MAX` seconds.
    """
    owner = machine.Get_Par(wt_adwin.PAR__SEQUENCE__OWNER)
    if owner:
        raise OutputsOwned(owner)
    if machine.Process_Status(PROCESS) == 0:
        raise RuntimeError(
            "The console, process {}, is not running, so nothing would serve the request."
            " Load `WignerTimeConsole.bas` and start it.".format(PROCESS)
        )

    deadline = time.monotonic() + WAIT__MAX
    while machine.Get_Par(PAR__REQUEST) != 0:
        if time.monotonic() > deadline:
            raise TimeoutError(
                "The console has not served the previous request within {:g} s.".format(
                    WAIT__MAX
                )
            )
        time.sleep(POLL__PERIOD)

    machine.Set_Par(PAR__MODULE, int(module))
    machine.Set_Par(PAR__CHANNEL, int(channel))
    machine.Set_Par(PAR__DIGITS, int(digits))
    machine.Set_Par(PAR__REQUEST, 1)


def to_digits(value, to_V):
    """The digits for `value` of a device with conversion `to_V`, as the sequencer gets them."""
    voltage = to_V(value) if callable(to_V) else value * to_V
    return int(conversion.to_digits(voltage))


def actuate_analog(machine, module, channel, value, to_V):
    """`actuate` with a value in the device's own unit."""
    actuate(machine, module, channel, to_digits(value, to_V))


def _row(table, name):
    rows = table.loc[table["variable"] == name]
    if rows.empty:
        raise ValueError(
            "The panel has no variable {!r}. It has: {}.".format(
                name, sorted(table["variable"])
            )
        )
    return rows.iloc[0]


def set_value(machine, table, name, value):
    """
    Sets the variable `name` of the `panel` to `value`, in its own unit: 0 or 1 for a
    digital line. An analogue value is checked against the device's range by
    `device.check_within_range`, as a timeline's values are.
    """
    row = _row(table, name)
    if wt_frame.isnull(row["to_V"]):
        if value not in (0, 1):
            raise ValueError(
                "{} is a digital line, so it takes 0 or 1, not {!r}.".format(
                    name, value
                )
            )
        actuate(machine, row["module"], row["channel"], int(value))
        return

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
    actuate_analog(machine, row["module"], row["channel"], value, row["to_V"])


def final_state(machine, table):
    """
    What the last run left the apparatus holding, as `{variable: value}` for the variables
    of the `panel` that its final state sets, read back from the machine.

    An analogue value is recovered from its digits over the variable's range: the value
    whose digits come closest, among 2**16 + 1 evenly spaced ones. This works for any
    `to_V`, a calibration function included, which cannot in general be inverted
    otherwise.
    """
    by_port = {(row.module, row.channel): row for row in table.itertuples()}
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
                grid = np.linspace(row.value__min, row.value__max, 2**16 + 1)
                voltages = (
                    np.vectorize(row.to_V)(grid)
                    if callable(row.to_V)
                    else grid * row.to_V
                )
                closest = np.argmin(np.abs(conversion.to_digits(voltages) - digit))
                state[row.variable] = float(grid[closest])

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


class Health(NamedTuple):
    """
    A snapshot of the machine as the console sees it. `workload` is ADwin's processor
    workload in percent. It is for the fault reported in the lab, the processor saturating
    for seconds at a time while the console runs: sampled over a session, it dates each
    episode.
    """

    workload: int
    console: int
    owner: int
    served: int
    pending: bool


def health(machine):
    """The console's `Health` now: workload, its process status, the arrays' owner, requests."""
    return Health(
        workload=machine.Workload(),
        console=machine.Process_Status(PROCESS),
        owner=machine.Get_Par(wt_adwin.PAR__SEQUENCE__OWNER),
        served=machine.Get_Par(PAR__SERVED),
        pending=machine.Get_Par(PAR__REQUEST) != 0,
    )


def create_UI(machine, table):
    """
    The console's widgets for the `panel`: a vertical slider per analogue variable, a toggle
    per digital line, a button that shows the final state of the last run, and a line for
    messages. Building it writes every default to the apparatus.

    A slider sends its value when it is released, not while it is dragged; a drag used to
    send one request per pixel. A move that is refused, because a sequence owns the outputs
    or the console is not running, puts the widget back and says why, so that what the
    widgets show is what was written.
    """
    if not importlib.util.find_spec("ipywidgets"):
        raise ImportError("The console's widgets require `ipywidgets` to be installed.")
    import ipywidgets as widgets

    messages = widgets.Output()
    quiet = {"on": False}  # set while widgets are moved from here rather than by hand
    controls = {}

    def observe(control, name):
        def on_change(change):
            if quiet["on"]:
                return
            try:
                set_value(machine, table, name, change["new"])
            except (RuntimeError, TimeoutError) as refused:
                quiet["on"] = True
                try:
                    control.value = change["old"]
                finally:
                    quiet["on"] = False
                messages.append_stdout("{}: {}\n".format(name, refused))

        control.observe(on_change, names="value")

    sliders, toggles = [], [[], [], []]
    for row in table.itertuples():
        if wt_frame.isnull(row.to_V):
            control = widgets.ToggleButton(
                value=bool(row.default_value),
                description=row.variable,
                layout=widgets.Layout(margin="20px 5px"),
            )
            group = {"shutter": 0, "AOM": 1}.get(row.variable.split("_", 1)[0], 2)
            toggles[group].append(control)
        else:
            control = widgets.FloatSlider(
                value=row.default_value,
                min=row.value__min,
                max=row.value__max,
                step=0.01,
                description="{}\n({})".format(
                    row.variable.rsplit("__", 1)[0], wt_variable.unit(row.variable)
                ),
                orientation="vertical",
                continuous_update=False,
                layout=widgets.Layout(margin="20px 40px", height="300px"),
            )
            sliders.append(control)
        observe(control, row.variable)
        controls[row.variable] = control
        set_value(machine, table, row.variable, row.default_value)

    def show_final_state(_):
        state = final_state(machine, table)
        quiet["on"] = True
        try:
            for name, value in state.items():
                control = controls[name]
                digital = wt_frame.isnull(_row(table, name)["to_V"])
                control.value = bool(value) if digital else value
        finally:
            quiet["on"] = False
        messages.append_stdout(
            "Showing the final state of the last run, {} variables.\n".format(
                len(state)
            )
        )

    button = widgets.Button(description="Final state")
    button.on_click(show_final_state)

    return widgets.VBox(
        [widgets.HBox(sliders), *[widgets.HBox(t) for t in toggles], button, messages]
    )
