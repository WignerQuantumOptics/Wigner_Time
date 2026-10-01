# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
For 'lower-level' manipulations of ADwin-specifc timeline informaton.

In general, the user shouldn't need to use these functions and there is no guarantee that the API will not change.

"""

import numpy as np

from wignertime.internal.tags import wtlog as wtl
from wignertime.timeline import build as tl
from wignertime.hardware import conversion as conv
from wignertime.hardware import device
from wignertime.timeline import variable as wt_variable
from wignertime.internal import dataframe as wt_frame
import wignertime.backend.adwin as wt_adwin
from wignertime.backend.adwin import connection
from wignertime.backend.adwin import validate as wt_validate

"""
Represents the key ADwin settings for the given machine.

These should be loaded by the ADwin system during initialization. The settings should grow as large as possible (to encompass all of the internal ADwin features) for maximum reproducibility.

The specifications have the form of a list of 'ADwin device' dictionaries, with the modules represented as a list of dictionaries.
"""
SPECIFICATIONS__DEFAULT = {
    # The cycle period is deliberately *not* here. It belongs to the program loaded on
    # the machine, not to the package -- the two laboratories this was written for run
    # at 5 us and 2 us -- so it is an argument of `core.convert`, and `specifications`
    # refuses an entry for it rather than letting a second source of it stand (#94).
    #
    # NOTE: it was `cycle_period__normal`, where `normal` contrasted with a
    # `cycle_period__burst` of 250 ns that has since been dropped. If ADC burst mode
    # (`P2_Burst_Init` in `WignerTimeADwinADC.bas`) is ever described here, it wants a
    # name of its own -- `sampling_period__ADC` or similar. It is a sampling period for
    # reading, on a different clock and for a different purpose, and calling the two
    # things flavours of one "cycle period" is what made the qualifier necessary.
    "modules": [
        {
            "bits": 1,
            "voltage_range": [0.0, 5.0],
            "gain": 1,
        },
        {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
        {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
        {
            "bits": 16,
            "voltage_range": [-10.0, 10.0],
            "gain": 1,
        },
    ],
}


def modules__digital(machine_specifications):
    """
    The module numbers carrying digital connections, derived from the specifications.

    A digital line is one bit wide, so a module of one-bit channels is a digital module.
    This is a *derivation* rather than a declaration, deliberately: a `kind` field beside
    `bits` would be a second source of truth, and a module declared
    `{"kind": "digital", "bits": 16}` would have no right answer. The same reasoning
    keeps module and channel numbers out of the device conversions.

    Until 2026-09-22 the test read `m.get("bits", False) == True`, which picks out the
    digital module only because `1 == True` in Python (D12/#126). Note what that did and
    did not cost: `x == True` and `x == 1` agree for every number, so the answer was
    never wrong -- what was wrong was that "is one bit wide" was written as a comparison
    against a boolean, leaving the intent unrecoverable from the code.

    A module that declares no `bits` at all now raises rather than being taken for
    analogue, which is the one behaviour that changed. Silently reading an
    under-specified module as analogue is a guess about hardware, and it would put a
    16-bit conversion on a digital line.

    NOTE: Modules are numbered from 1 (unlike Python lists).

    Any number of modules may be digital, and the real-time program honours each: `upload`
    sends it the list, which its `lowinit:` programs as outputs, and the module of every
    digital row, as it does for the analogue ones (D18, #133).
    """
    modules = machine_specifications["modules"]

    modules__unspecified = [i + 1 for i, m in enumerate(modules) if "bits" not in m]
    if modules__unspecified:
        raise ValueError(
            "Module(s) {} declare no `bits`, so whether they are digital cannot be"
            " determined. Every entry of `machine_specifications['modules']` needs its"
            " width: 1 for a digital module, 16 for the usual analogue one.".format(
                modules__unspecified
            )
        )

    return [i + 1 for i, m in enumerate(modules) if m["bits"] == 1]


def check_modules_described(connections, machine_specifications):
    """
    Checks that every module a connection names is one the specifications describe.

    Everything about a module – whether it is digital, and how its values become digits – is
    read from its entry in the specifications, so a connection to a module without one has no
    right answer. It used to be taken for analogue and converted as ±10 V, 16 bits.
    """
    count = len(machine_specifications["modules"])
    undescribed = sorted(
        {int(m) for m in connections["module"] if not 1 <= int(m) <= count}
    )
    if undescribed:
        raise ValueError(
            "Connections name module(s) {}, but the machine specifications describe modules"
            " 1 to {} only. Describe every installed module in"
            " `machine_specifications['modules']`, or correct the connections.".format(
                undescribed, count
            )
        )


def conversion__module(machine_specifications, module):
    """
    How the values of an analogue `module` become digits, as the keyword arguments of
    `conversion.to_digits`: the module's `voltage_range`, its width in `bits`, and its `gain`,
    from its entry in the specifications.

    Each module is converted with its own entry (D11, #125). Every analogue module the
    package had run on is ±10 V and 16 bits, which is why converting all of them with
    `conversion.SPECIFICATIONS__DEFAULT` went unnoticed: a module of any other range was
    converted wrongly, without a word. An entry missing one of the three raises, rather
    than being completed with those values.
    """
    entry = machine_specifications["modules"][module - 1]
    missing = [key for key in ("voltage_range", "bits", "gain") if key not in entry]
    if missing:
        raise ValueError(
            "Module {} is analogue, but its entry in the machine specifications gives no {},"
            " so its values cannot be converted to digits.".format(module, missing)
        )
    return {
        "voltage_range": entry["voltage_range"],
        "num_bits": entry["bits"],
        "gain": entry["gain"],
    }


def check_module_kinds(connections, modules__digital):
    """
    Checks that each connected variable is of the kind of the module it is connected to.

    A variable's kind is stated twice: by its name, since a variable without a `__unit`
    suffix is a digital line, and by its module, whose width says what the port is. Nothing
    checked that the two agree (A16). An analogue variable on the digital module was rounded
    to an integer and switched as a digital line: 1.5 A on a coil became a 2 written to a
    digital output, without a word. A digital line on an analogue module did fail, but later,
    in a cast, with a message that named neither the variable nor the cause.
    """
    kinds = {True: "digital", False: "analogue"}
    wrong = [
        "  {} on module {}: {} by its name, but the module is {}".format(
            name,
            module,
            kinds[wt_variable.unit(name) == "digital"],
            kinds[module in modules__digital],
        )
        for name, module in zip(connections["variable"], connections["module"])
        if (wt_variable.unit(name) == "digital") != (module in modules__digital)
    ]
    if wrong:
        raise ValueError(
            "\n".join(
                [
                    "A variable and the module it is connected to disagree on whether it"
                    " is digital:",
                    "",
                    *wrong,
                    "",
                    "Connect it to a module of its kind, or rename it: a digital line has no"
                    " `__unit` suffix.",
                ]
            )
        )


def specifications(machine_specifications=None):
    """
    The machine specifications to convert against: those given, or else
    `SPECIFICATIONS__DEFAULT` as it stands when this is called.

    Read here rather than bound as a default argument, so that rebinding the global
    reaches every function that uses it (D23).

    An entry for `cycle_period` is refused rather than ignored. The period used to live
    here, and a specification written then would otherwise be accepted with its period
    silently unused -- the failure D15 describes, in a new place.
    """
    if machine_specifications is None:
        machine_specifications = SPECIFICATIONS__DEFAULT

    if "cycle_period" in machine_specifications:
        raise ValueError(
            "The machine specifications carry a `cycle_period`, which is no longer read"
            " from them: it belongs to the program loaded on the machine, not to a"
            " description of its modules. Pass it to `adwin.core.convert` as"
            " `cycle_period` instead, and remove it from the specifications."
        )

    return machine_specifications


def add_cycle(timeline, cycle_period, special_contexts=None):
    """
    Inserts a new `cycle` column into the timeline as a conversion of the `time` column into 'number of cycles'.

    Parameters:
    - timeline: DataFrame containing the experimental data.
    - cycle_period: The period of the controller's event loop, in seconds.
    - special_contexts: Dictionary with context-specific overrides for cycle values;
      `wt_adwin.CONTEXTS__SPECIAL` when not given.

    The column is 64-bit here, although the machine's counter is 32-bit: a row too late
    for the counter has to survive long enough for `validate.cycles` to refuse it, and
    casting first would wrap it into an ordinary-looking number instead. `validate.types`
    narrows it once that check has run.

    Raises:
    - ValueError if the `time` column is missing, or the cycle period is not a positive
      number of seconds.
    """
    if special_contexts is None:
        special_contexts = wt_adwin.CONTEXTS__SPECIAL

    if "time" not in timeline.columns:
        raise ValueError(
            f"`time` column not found. Columns present: {list(timeline.columns)}"
        )

    if not cycle_period > 0:
        raise ValueError(
            "`cycle_period` must be a positive number of seconds, not {!r}.".format(
                cycle_period
            )
        )

    # Rows before the run are at −∞ and rows after it at +∞ (#154), in the special
    # contexts, whose cycles are the sentinels below. Anywhere else a time that is not
    # finite has no cycle, and casting it gave an arbitrary integer with a numpy warning.
    times = timeline["time"].to_numpy(dtype=float)
    mask__finite = np.isfinite(times)
    mask__special = timeline["context"].isin(list(special_contexts)).to_numpy()
    if (~mask__finite & ~mask__special).any():
        raise ValueError(
            "Rows outside the special contexts {} must be at an instant of the run; ±∞"
            " is before or after it (#154). Offending rows:\n{}".format(
                list(special_contexts),
                timeline.loc[
                    ~mask__finite & ~mask__special, ["variable", "time", "context"]
                ],
            )
        )

    cycles = np.zeros(len(times), dtype=np.int64)
    cycles[mask__finite] = np.round(times[mask__finite] / cycle_period)
    timeline["cycle"] = cycles

    # Apply special context cycles
    timeline = wt_frame.replace_column__filtered(
        timeline,
        special_contexts,
        column__change="cycle",
    )

    return timeline


def add(timeline, connections, devices, cycle_period, machine_specifications=None):
    """
    Takes an 'operational' layer timeline and inserts ADwin-specific columns, e.g. cycles and numbers for the module and channel etc.

    Which modules are digital, and how each analogue module converts to digits, are read
    from `machine_specifications` (D11, D18).

    `cycle_period` is the period of the controller's event loop, in seconds; see
    `core.convert`.
    """

    wtl.debug("Got to `adwin.core.add`")
    machine_specifications = specifications(machine_specifications)

    # Here because this is where the two tables meet, and because conversion is the one
    # point at which hardware enters. Neither `connection.new` nor `device.new` can do it
    # alone: each sees only its own vocabulary (A14).
    device.check_correspondence(connections, devices)
    check_modules_described(connections, machine_specifications)
    check_module_kinds(connections, modules__digital(machine_specifications))

    dff = wt_frame.join(timeline, connections)
    dff = wt_frame.join(dff, devices)
    # Stably (A18): among a variable's rows at one instant the last written is in effect,
    # and `drop_duplicates` keeps the last of each cycle. The quicksort this used could
    # put a ramp's end after the `update` superseding it, and send the ramp's end.
    dff = wt_frame.sort(dff, "time")

    mask__digital = dff["module"].isin(modules__digital(machine_specifications))

    # Each analogue module with its own range, width and gain (D11).
    dff["value__digits"] = np.nan
    for module in sorted(set(dff.loc[~mask__digital, "module"])):
        mask = dff["module"] == module
        dff.loc[mask, "value__digits"] = conv.add(
            dff.loc[mask],
            specifications=conversion__module(machine_specifications, int(module)),
        )["value__digits"].to_numpy()

    dff.loc[mask__digital, "value__digits"] = round(dff["value"])

    device.check_within_range(dff)
    dcycle = add_cycle(dff, cycle_period)

    return wt_validate.all(dcycle)


def to_tuples__raw(timeline, cols=["cycle", "module", "channel", "value__digits"]):
    """
    A raw extraction of ADwin-relevant values from a `timeline`, regardless of whether or not the module is digital or not.

    NOTE: No validation is done here.
    """
    return [tuple([np.int32(i) for i in x]) for x in timeline[cols].values]


def to_tuples(timeline, machine_specifications=None):
    """
    Takes a full, ADwin-compatible, dataframe of the experimental run and converts the result to an output format that can be processed by ADwin (tuples), separating analogue and digital values.

    return [[(cycle, module, channel, value), ...],
    [(cycle, module, channel, value), ...]]
    """
    wtl.debug("Got to `output`")
    machine_specifications = specifications(machine_specifications)

    if not timeline["cycle"].is_monotonic_increasing:
        timeline = timeline.sort_values(by=["cycle"], ignore_index=True)

    if not ("module" in timeline.columns):
        raise ValueError(
            "No `module` listed in timeline. Remember to add ADwin specifications before ADwin export."
        )

    mods_digital = modules__digital(machine_specifications)
    mods_analogue = [x for x in timeline["module"].unique() if x not in mods_digital]

    # NOTE: filtered by value rather than by a formatted query string. `module` is an
    # int64 column, so `unique()` yields numpy scalars, and building a query out of them
    # produced `module in [np.int64(3), np.int64(4)]` -- which pandas parses and then
    # rejects with `UndefinedVariableError: name 'np' is not defined`, an error that
    # looks like it comes from inside pandas and says nothing about modules (#41). A
    # bare `int()` on each element used to hold that off; comparing values removes the
    # failure mode instead of guarding it.
    return [
        to_tuples__raw(wt_frame.subframe(timeline, "module", mods_analogue)),
        to_tuples__raw(wt_frame.subframe(timeline, "module", mods_digital)),
    ]
