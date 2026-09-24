import pathlib as pl
import sys
import pytest
import pandas as pd

import wignertime.adwin as wt_adwin

# `adwin.core` needs the optional `adwin` extra. Skip rather than error, so that
# the suite is green for the right reasons in an environment without it.
pytest.importorskip("ADwin", reason="the `adwin` extra is not installed")

from wignertime.adwin import core as adwin
from wignertime.adwin import connection as adcon
from wignertime.adwin import validate as wt_validate
from wignertime.adwin import internal as adi
from wignertime import device
from wignertime import timeline as tl
from wignertime.internal import dataframe as frame
from wignertime.demo import full_experiment as demo

sys.path.append(str(pl.Path.cwd() / "doc"))
# import experimentDemo as ex

print(str(pl.Path.cwd() / "doc"))


@pytest.fixture
def df_simple():
    return pd.DataFrame(
        [
            [0.0, "AOM_imaging", 0.0, "init"],
            [0.0, "AOM_imaging__V", 2.0, "init"],
            [0.0, "AOM_repump", 1.0, "init"],
            [0.0, "virtual", 1.0, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def connections_simple():
    return adcon.new(
        ["AOM_imaging", 1, 1],
        ["AOM_imaging__V", 1, 2],
        ["AOM_repump", 2, 3],
    )


def test_remove_unconnected_variables(df_simple, connections_simple):
    return pd.testing.assert_frame_equal(
        adcon.remove_unconnected_variables(df_simple, connections_simple),
        pd.DataFrame(
            {
                "time": [0.0] * 3,
                "variable": ["AOM_imaging", "AOM_imaging__V", "AOM_repump"],
                "value": [0.0, 2.0, 1.0],
                "context": ["init"] * 3,
            }
        ),
    )


def test_add_cycle():
    df = pd.DataFrame({"time": range(10), "value": range(11, 21)})
    df["context"] = (
        ["MOT"] * 4 + ["ADwin_LowInit"] * 3 + ["ADwin_Init"] * 2 + ["ADwin_Finish"]
    )
    tst = frame.cast(adi.add_cycle(df, 5e-6), wt_adwin.SCHEMA)

    return pd.testing.assert_frame_equal(
        tst,
        frame.cast(
            pd.DataFrame(
                {
                    "time": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                    "value": [11, 12, 13, 14, 15.0, 16, 17, 18, 19, 20],
                    "context": [
                        "MOT",
                        "MOT",
                        "MOT",
                        "MOT",
                        "ADwin_LowInit",
                        "ADwin_LowInit",
                        "ADwin_LowInit",
                        "ADwin_Init",
                        "ADwin_Init",
                        "ADwin_Finish",
                    ],
                    "cycle": [
                        0,
                        200000,
                        400000,
                        600000,
                        -2,
                        -2,
                        -2,
                        -1,
                        -1,
                        2147483647,
                    ],
                }
            ),
            wt_adwin.SCHEMA,
        ),
    )


###############################################################################
#                        dealing with special contexts                        #
###############################################################################

df_special1 = frame.new(
    [
        [0.0, "AOM_imaging", 0.0, "ADwin_Init"],
        [10.0, "AOM_imaging", 0.0, "ADwin_Init"],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM_repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)


df_special2 = frame.new(
    [
        [0.0, "AOM_imaging", 0, "ADwin_Init"],
        [10.0, "AOM_imaging", 1, "ADwin_Init"],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM_repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)

df_special3 = frame.cast(
    frame.new(
        [
            [0.0, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [0.0, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
            [0.0, "AOM_imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
        ],
        columns=[
            "time",
            "variable",
            "value",
            "context",
            "module",
            "channel",
            "cycle",
            "value__digits",
        ],
    ),
    wt_adwin.SCHEMA,
)


df_special3__corrected = frame.cast(
    frame.new(
        [
            [-1, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [-1, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
            [2**31 - 1, "AOM_imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
        ],
        columns=[
            "time",
            "variable",
            "value",
            "context",
            "module",
            "channel",
            "cycle",
            "value__digits",
        ],
    ),
    wt_adwin.SCHEMA,
)


df_special4 = frame.new_schema(
    [
        [0.0, "AOM_imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
        [0.0, "AOM_imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
        [0.0, "AOM_repump", 1.0, "init", 1, 1, 0, 5],
    ],
    schema=wt_adwin.SCHEMA,
)


@pytest.mark.parametrize("input_value", [df_special1, df_special2])
def test_sanitize_raises(input_value):
    with pytest.raises(ValueError):
        wt_validate.special_contexts(input_value)


def test_sanitize_success():
    return pd.testing.assert_frame_equal(
        wt_validate.all(df_special3), df_special3__corrected
    )


def test_convert():
    connections = adcon.new(
        ["shutter_MOT", 1, 11],
        ["lockbox_MOT__MHz", 3, 8],
    )

    devices = device.new(
        ["lockbox_MOT__MHz", 0.05],
    )

    tuples = adwin.convert(
        tl.stack(
            tl.create(
                lockbox_MOT__MHz=0.0,
                shutter_MOT=0,
                context="ADwin_LowInit",
            ),
            tl.anchor(t=0.0, origin=0.0, context="InitialAnchor"),
            tl.update(
                shutter_MOT=1,
                context="MOT",
            ),
            tl.anchor(15),
            tl.ramp(
                lockbox_MOT__MHz=-5,
                duration=10e-3,
                context="MOT",
            ),
            tl.anchor(100e-3),
        ),
        connections,
        devices,
        5e-6,
        time_resolution=5e-3,
    )
    tuples__guess = [
        [
            (-2, 3, 8, 32768),
            (3000000, 3, 8, 32768),
            (3001000, 3, 8, 32358),
            (3002000, 3, 8, 31948),
        ],
        [
            (-2, 1, 11, 0),
            (0, 1, 11, 1),
        ],
    ]

    assert tuples == tuples__guess


def test_to_tuples_separates_modules_despite_numpy_scalars():
    """
    #41. `module` is an int64 column, so `unique()` yields numpy scalars. Selecting on
    them by way of a formatted query string built `module in [np.int64(3), np.int64(4)]`,
    which pandas parses and then rejects with `UndefinedVariableError: name 'np' is not
    defined` -- an error that appears to come from inside pandas and mentions nothing
    about modules.

    Filtering by value cannot have that failure mode, so this guards the separation
    itself: every analogue tuple on a non-digital module, every digital one on module 1,
    and nothing dropped.
    """
    import numpy as np
    from wignertime.internal import dataframe as frame

    digital = adi.modules__digital(adi.SPECIFICATIONS__DEFAULT)

    timeline = frame.new_schema(
        [
            [0.0, "AOM_imaging", 0.0, "init", 1, 1, 0, 0],
            [0.0, "coil__A", 1.0, "init", 3, 2, 0, 32768],
            [1.0, "coil__A", 2.0, "init", 4, 5, 1, 65535],
        ],
        schema=wt_adwin.SCHEMA,
    )
    assert timeline["module"].dtype == np.int64, "the premise of the bug"

    analogue, digitals = adi.to_tuples(timeline)

    assert [t[1] for t in digitals] == [1]
    assert sorted(int(t[1]) for t in analogue) == [3, 4]
    assert len(analogue) + len(digitals) == len(timeline), "no row dropped"


class _MachineRecording:
    """
    Stands in for `ADwin.ADwin`, recording what `core.upload` would transfer.

    The hardware calls are the part of the export that cannot be exercised here
    (`KNOWN_ISSUES` §E), so this covers the argument assembly around them and nothing
    more: which parameters are set, which data arrays are written, and what is read.
    It reports a T12 with process 1 at Lab1's 5 us unless told otherwise.
    """

    def __init__(self, processor="T12", processdelay=None, status=(), lost_events=()):
        self.par = {}
        self.data = {}
        self.processor = processor
        self.processdelay = {1: 5000} if processdelay is None else processdelay
        # What `Process_Status` and `Get_Lost_Events` answer, one entry per call; then 0.
        self.status = list(status)
        self.lost_events = list(lost_events)
        self.calls = []

    def Start_Process(self, process):
        self.calls.append(("Start_Process", process))

    def Get_Lost_Events(self, process):
        answer = self.lost_events.pop(0) if self.lost_events else 0
        self.calls.append(("Get_Lost_Events", answer))
        return answer

    def Processor_Type(self):
        return self.processor

    def Get_Processdelay(self, process):
        # The driver answers for any process number; an empty slot reads as nothing.
        return self.processdelay.get(process, 0)

    def Process_Status(self, process):
        answer = self.status.pop(0) if self.status else 0
        self.calls.append(("Process_Status", answer))
        return answer

    def Set_Par(self, number, value):
        self.calls.append(("Set_Par", number))
        self.par[number] = value

    def SetData_Long(self, values, number, startindex, count):
        self.calls.append(("SetData_Long", number))
        self.data[number] = (list(values), count)


def _digital_only():
    conns = adcon.new(["shutter_MOT", 1, 11], ["AOM_MOT", 1, 1])
    devs = (
        device.new()
    )  # nothing analogue is connected, so there is nothing to calibrate
    timeline = tl.stack(
        tl.create(shutter_MOT=1, AOM_MOT=1, t=0.0, context="run"),
        tl.update(shutter_MOT=0, t=1.0),
    )
    return timeline, conns, devs


def test_upload_transfers_an_empty_analogue_set_as_a_count_of_zero():
    """
    #73. An empty set used to raise `IndexError: too many indices` while computing the
    end cycle -- before any `Set_Par` -- so nothing was transferred at all and the
    machine kept the whole of the previous experiment, which then ran.

    The count is what tells the real-time program not to read the array, and it has to
    be set precisely because the arrays are never cleared (#8).
    """
    machine = _MachineRecording()
    adwin.upload(*_digital_only(), machine, 1)

    assert machine.par[2] == 0, "analogue count must be transferred as zero"
    assert machine.par[3] == 3, "digital count unaffected"
    assert sorted(machine.data) == [20, 21, 22, 23], "only the digital arrays written"


def test_upload_transfers_both_sets_when_both_are_populated():
    machine = _MachineRecording()
    adwin.upload(demo.timeline__demo, demo.connections, demo.devices, machine, 1)

    assert sorted(machine.data) == [10, 11, 12, 13, 20, 21, 22, 23]
    assert machine.par[2] == len(machine.data[10][0]) > 0
    assert machine.par[3] == len(machine.data[20][0]) > 0


def test_upload_refuses_a_timeline_with_no_run():
    """
    Every update in a special context means the experiment has no duration, and the end
    cycle cannot be derived. That used to be a bare `ValueError: zero-size array`.
    """
    _, conns, devs = _digital_only()
    with pytest.raises(ValueError, match="nothing to run"):
        adwin.upload(
            tl.create(shutter_MOT=1, t=-1e-6, context="ADwin_LowInit"),
            conns,
            devs,
            _MachineRecording(),
            1,
        )


###############################################################################
#   D15 / #129, D14 / #128 -- the period is read off the machine, never given
###############################################################################


def test_convert_has_no_default_cycle_period():
    """The period belongs to the machine, so an offline conversion has to state it."""
    import inspect

    parameter = inspect.signature(adwin.convert).parameters["cycle_period"]
    assert parameter.default is inspect.Parameter.empty


def test_upload_requires_the_machine_and_the_process_and_takes_no_period():
    """Without both, the period cannot be read; given one, it could disagree with them."""
    import inspect

    parameters = inspect.signature(adwin.upload).parameters
    for name in ["machine", "process"]:
        assert parameters[name].default is inspect.Parameter.empty
    assert "cycle_period" not in parameters


def test_upload_converts_at_the_period_the_machine_reports():
    """
    D15, now at its root: the period is the process's Processdelay over the processor's
    rate, so Lab2's 2000 on a T12 puts the update at t = 1 s at cycle 500 000.
    """
    machine = _MachineRecording(processdelay={1: 2000})
    log = adwin.upload(*_digital_only(), machine, 1)

    assert log.cycle_period == 2e-6, "2000 / 1e9 is exactly the float 2e-6"
    assert machine.par[1] == log.cycle__last == 500_000
    assert max(machine.data[20][0]) == 500_000


def test_upload_reads_the_period_of_the_process_it_is_told():
    """Process 4, the ADC variant, plays the same arrays at its own period."""
    machine = _MachineRecording(processdelay={1: 5000, 4: 2000})
    assert adwin.upload(*_digital_only(), machine, 4).cycle_period == 2e-6
    assert adwin.upload(*_digital_only(), machine, 1).cycle_period == 5e-6


def test_upload_refuses_a_processor_it_does_not_know():
    """The T11's rate would be a guess, and a wrong one rescales every time."""
    with pytest.raises(ValueError, match="'T11' processor"):
        adwin.upload(*_digital_only(), _MachineRecording(processor="T11"), 1)


def test_upload_refuses_a_process_that_is_not_loaded():
    with pytest.raises(ValueError, match="Process 2 reports a Processdelay of 0"):
        adwin.upload(*_digital_only(), _MachineRecording(), 2)


def test_upload_converts_against_the_specification_it_is_given():
    """D15's other half: `machine_specifications` used to stop at `create`."""
    timeline, _, devs = _digital_only()
    conns = adcon.new(["shutter_MOT", 2, 11], ["AOM_MOT", 2, 1])
    specifications = {"modules": [{"bits": 16}, {"bits": 1}]}

    machine = _MachineRecording()
    adwin.upload(
        timeline, conns, devs, machine, 1, machine_specifications=specifications
    )

    assert sorted(machine.data) == [20, 21, 22, 23], "module 2 is the digital one here"


def test_the_log_records_what_was_written_and_where():
    machine = _MachineRecording()
    log = adwin.upload(*_digital_only(), machine, 1)

    assert (log.machine, log.process) == (machine, 1)
    assert (log.processor, log.processdelay) == ("T12", 5000)
    assert log.time__last == pytest.approx(1.0)
    assert [row[0] for row in log.digital] == machine.data[20][0]
    assert log.analogue == []


def test_the_log_stands_in_for_the_machine_and_process_pair():
    """
    Routines that start the controller take `(machine, process)` and index it, as the
    camera routines of `sec:parameter_scan` do, so the log can be handed to them as is.
    """
    machine = _MachineRecording()
    log = adwin.upload(*_digital_only(), machine, 1)
    assert log[0] is machine and log[1] == 1


###############################################################################
#   A15 / #151 -- an upload does not land under a run that is still playing
###############################################################################


def test_upload_waits_for_a_running_process_before_writing(monkeypatch, caplog):
    """
    The machine accepts writes mid-run, so the only protection is not to make them. `-1`
    stands for a process still in its `finish:` section, which is running too.
    """
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    machine = _MachineRecording(status=[1, 1, -1])

    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_digital_only(), machine, 1)

    first_write = next(
        i for i, c in enumerate(machine.calls) if c[0] != "Process_Status"
    )
    assert [c[1] for c in machine.calls[:first_write]] == [1, 1, -1, 0]
    assert [r.message for r in caplog.records].count(
        "Process 1 is still running; waiting for it to stop before uploading, so as not"
        " to rewrite the arrays it is playing."
    ) == 1, "said once, not once per poll"


def test_upload_to_a_stopped_process_neither_waits_nor_says_so(caplog):
    machine = _MachineRecording()
    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_digital_only(), machine, 1)

    assert machine.calls[0] == ("Process_Status", 0)
    assert not caplog.records


###############################################################################
#   Running what was uploaded -- roadmap step 6
###############################################################################


def _uploaded(**machine):
    """An upload to a recording machine, with the calls the upload made forgotten."""
    log = adwin.upload(*_digital_only(), _MachineRecording(**machine), 1)
    log.machine.calls.clear()
    return log


def _names(calls):
    return [name for name, _ in calls]


def test_running_starts_before_the_block_and_waits_after_it(monkeypatch):
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    log = _uploaded()
    log.machine.status = [0, 1, 1, 0]  # stopped at the start; running for two polls

    with adwin.running(log) as run:
        inside = list(log.machine.calls)

    assert _names(inside) == ["Process_Status", "Get_Lost_Events", "Start_Process"]
    assert _names(log.machine.calls[len(inside) :]) == [
        "Process_Status",
        "Process_Status",
        "Process_Status",
        "Get_Lost_Events",
    ]
    assert run.lost_events == 0 and run.duration >= 0 and run.upload is log


def test_a_run_that_lost_events_is_refused_with_its_slip():
    """At Lab1's 5 us, 2 lost events stretch the run by 10 us."""
    log = _uploaded(lost_events=[3, 5])
    with pytest.raises(adwin.LostEvents, match=r"lost 2 events .* 10\.0 us longer"):
        adwin.run(log)


def test_the_refusal_carries_the_record():
    log = _uploaded(lost_events=[0, 1])
    with pytest.raises(adwin.LostEvents) as refused:
        adwin.run(log)
    assert refused.value.run.lost_events == 1
    assert refused.value.run.slip == pytest.approx(5e-6)


def test_a_counter_that_falls_across_the_run_says_it_restarts():
    """The counter's semantics are unverified; a fall is the tell, and it is not hidden."""
    with pytest.raises(RuntimeError, match="evidently restarts with every start"):
        adwin.run(_uploaded(lost_events=[4, 0]))


def test_an_error_inside_the_block_waits_the_run_out_and_goes_on(monkeypatch):
    """Not stopped: until B11 is fixed, stopping would leave the apparatus driven."""
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    log = _uploaded(lost_events=[0, 7])
    log.machine.status = [0, 1, 0]

    with pytest.raises(TimeoutError, match="camera"):
        with adwin.running(log):
            raise TimeoutError("camera")

    names = _names(log.machine.calls)
    assert names[-2:] == ["Process_Status", "Process_Status"], "waited until stopped"
    assert (
        names.count("Get_Lost_Events") == 1
    ), "the camera's error, not a lost-events one"
    assert "Stop_Process" not in names


def test_starting_a_replay_waits_for_the_previous_run(monkeypatch, caplog):
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    log = _uploaded()
    log.machine.status = [1, 1, 0]

    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.start(log)

    assert _names(log.machine.calls)[-1] == "Start_Process"
    assert [r.message for r in caplog.records] == [
        "Process 1 is still running; waiting for it to stop before starting it again."
    ]


def test_the_log_is_short_to_print():
    """The arrays can run to hundreds of thousands of rows; they are counted, not shown."""
    log = adwin.upload(
        demo.timeline__demo, demo.connections, demo.devices, _MachineRecording(), 1
    )
    assert len(repr(log)) < 300
    assert "rows={} analogue".format(len(log.analogue)) in repr(log)


def test_a_specification_carrying_a_cycle_period_is_refused():
    """Accepting it with the period unused would be D15 again, one layer down."""
    specifications = {"cycle_period": 2e-6, **adi.SPECIFICATIONS__DEFAULT}
    with pytest.raises(ValueError, match="no longer read"):
        adwin.convert(*_digital_only(), 2e-6, machine_specifications=specifications)


###############################################################################
#   D19 / D20 -- what the real-time program can play
###############################################################################


def _with_a_row_at(time, cycle_period=5e-6):
    timeline, conns, devs = _digital_only()
    timeline = tl.update(shutter_MOT=1, t=time, origin=0.0, timeline=timeline)
    return adwin.convert(timeline, conns, devs, cycle_period)


@pytest.mark.parametrize(
    "time",
    [
        -1e-3,  # sorts ahead of the lowinit rows: nothing in the array is played
        -5e-6,  # cycle -1: played with the init rows
        (2**31 - 1) * 5e-6,  # the finish sentinel, and past it the counter wraps
    ],
)
def test_a_row_outside_the_run_is_refused(time):
    with pytest.raises(ValueError, match="must fall within cycles 0..2147483646"):
        _with_a_row_at(time)


@pytest.mark.parametrize("time", [-2e-6, (2**31 - 2) * 5e-6])
def test_the_run_reaches_both_of_its_ends(time):
    """Less than half a cycle before zero rounds to zero; the last cycle is playable."""
    assert _with_a_row_at(time)


def test_the_special_contexts_are_not_held_to_the_run():
    """Their times are nominal; `init` in the lab places them at t = -1 us."""
    _, conns, devs = _digital_only()
    timeline = tl.stack(
        tl.create(shutter_MOT=0, AOM_MOT=0, t=-1e-3, context="ADwin_LowInit"),
        tl.update(shutter_MOT=1, t=1.0, origin=0.0, context="run"),
    )
    analogue, digital = adwin.convert(timeline, conns, devs, 5e-6)
    assert [row[0] for row in digital] == [-2, -2, 200_000]


def test_arrays_out_of_order_are_refused():
    """
    `processUpdates` never rewinds, so the row at 200 would be played at 300, with the
    row before it. Built by hand: `to_tuples` sorts, so conversion cannot produce it.
    """
    in_order = [[], [(-2, 1, 11, 0), (100, 1, 11, 1), (200, 1, 12, 1)]]
    assert wt_validate.ascending(in_order) is in_order

    with pytest.raises(
        ValueError, match="row 3 is at cycle 200, after one at cycle 300"
    ):
        wt_validate.ascending([[], [(-2, 1, 11, 0), (300, 1, 11, 1), (200, 1, 12, 1)]])


###############################################################################
#   D12 / #126 -- "digital" is derived from the module's width
###############################################################################


def test_modules__digital_reads_the_shipped_specification():
    """Module 1 is the one-bit module in `SPECIFICATIONS__DEFAULT`; the rest are 16-bit."""
    assert adi.modules__digital(adi.SPECIFICATIONS__DEFAULT) == [1]


@pytest.mark.parametrize("width", [2, 8, 16, 32])
def test_modules__digital_only_one_bit_wide_is_digital(width):
    """
    A pin rather than a regression test: `x == True` and `x == 1` agree for every
    number, so this passed before D12 was fixed too. It records the boundary the
    old spelling could not express -- that the test is on the *width*, not on a
    module being flagged.
    """
    specifications = {"modules": [{"bits": width}, {"bits": 1}]}
    assert adi.modules__digital(specifications) == [2]


def test_modules__digital_refuses_a_module_of_unstated_width():
    """
    The one behaviour D12 changed. A module with no `bits` used to fall through as
    analogue, which is a guess about hardware -- and the wrong one puts a 16-bit
    conversion on a digital line.
    """
    specifications = {"modules": [{"bits": 1}, {"voltage_range": [-10.0, 10.0]}]}
    with pytest.raises(ValueError, match=r"Module\(s\) \[2\] declare no `bits`"):
        adi.modules__digital(specifications)
