import pathlib as pl
import sys
import pytest

import wignertime.adwin as wt_adwin

# `adwin.core` needs the optional `adwin` extra. Skip rather than error, so that
# the suite is green for the right reasons in an environment without it.
pytest.importorskip("ADwin", reason="the `adwin` extra is not installed")

from wignertime.adwin import core as adwin
from wignertime.adwin import adc
from wignertime.adwin import console
from wignertime.adwin import connection as adcon
from wignertime.adwin import validate as wt_validate
from wignertime.adwin import internal as adi
from wignertime import conversion
from wignertime import device
from wignertime import timeline as tl
from wignertime.internal import dataframe as frame
from wignertime.demo import full_experiment as demo
from wignertime.internal import dataframe as wt_frame

sys.path.append(str(pl.Path.cwd() / "doc"))
# import experimentDemo as ex

print(str(pl.Path.cwd() / "doc"))


@pytest.fixture
def df_simple():
    return wt_frame.new(
        [
            [0.0, "AOM__imaging", 0.0, "init"],
            [0.0, "AOM__imaging__V", 2.0, "init"],
            [0.0, "AOM__repump", 1.0, "init"],
            [0.0, "virtual", 1.0, "MOT"],
        ],
        columns=["time", "variable", "value", "context"],
    )


@pytest.fixture
def connections_simple():
    return adcon.new(
        ["AOM__imaging", 1, 1],
        ["AOM__imaging__V", 1, 2],
        ["AOM__repump", 2, 3],
    )


def test_remove_unconnected_variables(df_simple, connections_simple):
    return wt_frame.assert_equal(
        adcon.remove_unconnected_variables(df_simple, connections_simple),
        wt_frame.new(
            {
                "time": [0.0] * 3,
                "variable": ["AOM__imaging", "AOM__imaging__V", "AOM__repump"],
                "value": [0.0, 2.0, 1.0],
                "context": ["init"] * 3,
            }
        ),
    )


def test_add_cycle():
    df = wt_frame.new({"time": range(10), "value": range(11, 21)})
    df["context"] = (
        ["MOT"] * 4 + ["ADwin_LowInit"] * 3 + ["ADwin_Init"] * 2 + ["ADwin_Finish"]
    )
    tst = frame.cast(adi.add_cycle(df, 5e-6), wt_adwin.SCHEMA)

    return wt_frame.assert_equal(
        tst,
        frame.cast(
            wt_frame.new(
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
        [0.0, "AOM__imaging", 0.0, "ADwin_Init"],
        [10.0, "AOM__imaging", 0.0, "ADwin_Init"],
        [0.0, "AOM__imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM__repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)


df_special2 = frame.new(
    [
        [0.0, "AOM__imaging", 0, "ADwin_Init"],
        [10.0, "AOM__imaging", 1, "ADwin_Init"],
        [0.0, "AOM__imaging__V", 2.0, "ADwin_Init"],
        [0.0, "AOM__repump", 1.0, "init"],
        [0.0, "virtual", 1.0, "MOT"],
    ],
    columns=["time", "variable", "value", "context"],
)

df_special3 = frame.cast(
    frame.new(
        [
            [0.0, "AOM__imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [0.0, "AOM__imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM__repump", 1.0, "init", 1, 1, 0, 5],
            [0.0, "AOM__imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
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
            [-1, "AOM__imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
            [-1, "AOM__imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
            [0.0, "AOM__repump", 1.0, "init", 1, 1, 0, 5],
            [2**31 - 1, "AOM__imaging", 0.0, "ADwin_Finish", 1, 1, 0, 1],
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
        [0.0, "AOM__imaging", 0.0, "ADwin_Init", 1, 1, 0, 1],
        [0.0, "AOM__imaging__V", 2.0, "ADwin_Init", 1, 1, 0, 5],
        [0.0, "AOM__repump", 1.0, "init", 1, 1, 0, 5],
    ],
    schema=wt_adwin.SCHEMA,
)


@pytest.mark.parametrize("input_value", [df_special1, df_special2])
def test_sanitize_raises(input_value):
    with pytest.raises(ValueError):
        wt_validate.special_contexts(input_value)


def test_sanitize_success():
    return wt_frame.assert_equal(wt_validate.all(df_special3), df_special3__corrected)


def test_convert():
    connections = adcon.new(
        ["shutter__MOT", 1, 11],
        ["lockbox__MOT__MHz", 3, 8],
    )

    devices = device.new(
        ["lockbox__MOT__MHz", 0.05],
    )

    tuples = adwin.convert(
        tl.to_timeline(
            tl.stack(
                tl.anchor(time=0.0, origin=0.0, context="InitialAnchor"),
                tl.update(
                    shutter__MOT=1,
                    context="MOT",
                ),
                tl.anchor(15),
                tl.ramp(
                    lockbox__MOT__MHz=-5,
                    duration=10e-3,
                    context="MOT",
                ),
                tl.anchor(100e-3),
            ),
            onto=tl.to_timeline(
                tl.update(
                    lockbox__MOT__MHz=0.0,
                    shutter__MOT=0,
                    context="ADwin_LowInit",
                )
            ),
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
            [0.0, "AOM__imaging", 0.0, "init", 1, 1, 0, 0],
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

    def __init__(
        self,
        processor="T12",
        processdelay=None,
        status=(),
        lost_events=(),
        reports=None,
    ):
        self.par = {}
        self.data = {}
        self.processor = processor
        self.processdelay = {1: 5000} if processdelay is None else processdelay
        # What `Process_Status` and `Get_Lost_Events` answer, one entry per call; then 0.
        self.status = dict(status) if isinstance(status, dict) else list(status)
        self.lost_events = list(lost_events)
        # What the started program reports as its Processdelay (Par_14): its own unless
        # told otherwise, and 0 -- no report at all -- for a program older than the check.
        self.reports = reports
        self.calls = []
        # What `GetData_Long` answers: the console's arrays, where a test sets them.
        self.arrays = {}

    def Start_Process(self, process):
        self.calls.append(("Start_Process", process))
        reported = self.processdelay[process] if self.reports is None else self.reports
        if reported:
            self.par[wt_adwin.PAR__PROCESSDELAY__REPORTED] = reported

    def Get_Par(self, number):
        return self.par.get(number, 0)

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
        # A list answers for every process; a dict scripts each process on its own.
        answers = (
            self.status.setdefault(process, [])
            if isinstance(self.status, dict)
            else self.status
        )
        answer = answers.pop(0) if answers else 0
        self.calls.append(("Process_Status", answer))
        return answer

    def Set_Par(self, number, value):
        self.calls.append(("Set_Par", number))
        self.par[number] = value

    def SetData_Long(self, values, number, startindex, count):
        self.calls.append(("SetData_Long", number))
        self.data[number] = (list(values), count)

    def GetData_Long(self, number, startindex, count):
        array = self.arrays.get(number, [0] * (startindex - 1 + count))
        return array[startindex - 1 : startindex - 1 + count]


def _digital_only():
    conns = adcon.new(["shutter__MOT", 1, 11], ["AOM__MOT", 1, 1])
    devs = (
        device.new()
    )  # nothing analogue is connected, so there is nothing to calibrate
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(shutter__MOT=0, time=1.0),
        ),
        onto=tl.to_timeline(
            tl.update(shutter__MOT=1, AOM__MOT=1, time=0.0, context="run")
        ),
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
    adwin.upload(demo.timeline_demo, demo.connections, demo.devices, machine, 1)

    assert sorted(machine.data) == [10, 11, 12, 13, 20, 21, 22, 23, 31, 32, 33, 42, 43]
    assert machine.par[2] == len(machine.data[10][0]) > 0
    assert machine.par[3] == len(machine.data[20][0]) > 0
    assert machine.par[15] == len(machine.data[31][0]) > 0
    assert machine.par[16] == len(machine.data[42][0]) > 0


###############################################################################
#   B11 / #148 -- the final state has arrays of its own (roadmap step 8)
###############################################################################


def _with_a_final_state():
    conns = adcon.new(
        ["shutter__MOT", 1, 11], ["AOM__MOT", 1, 1], ["coil__MOT__A", 3, 2]
    )
    devs = device.new(["coil__MOT__A", 2.0, -5.0, 5.0])
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(
                shutter__MOT=0, AOM__MOT=0, coil__MOT__A=0.0, context="ADwin_LowInit"
            ),
            tl.anchor(0.0, origin=0.0, context="run"),
            tl.update(shutter__MOT=1, coil__MOT__A=1.0, time=0.5),
            tl.update(
                shutter__MOT=0,
                AOM__MOT=1,
                coil__MOT__A=0.0,
                time=1.0,
                context="ADwin_Finish",
            ),
        )
    )
    return timeline, conns, devs


def test_the_final_state_leaves_the_playback_arrays():
    """
    `finish:` used to play the final state from the playback arrays, and only if the run
    had reached them, so a stopped run never did. Now nothing at the finish sentinel is
    played, and the final state is in arrays that `finish:` plays from the start.
    """
    machine = _MachineRecording()
    log = adwin.upload(*_with_a_final_state(), machine, 1)

    finish = wt_adwin.CONTEXTS__SPECIAL["ADwin_Finish"]
    assert finish not in machine.data[10][0] + machine.data[20][0]
    # The analogue final state: module, channel, digits; 0 A is mid-scale.
    assert [machine.data[n][0] for n in (31, 32, 33)] == [[3], [2], [32768]]
    # The digital final state: channel and value; the module is not sent (D18).
    assert sorted(zip(machine.data[42][0], machine.data[43][0])) == [(1, 1), (11, 0)]
    assert (machine.par[15], machine.par[16]) == (1, 2)
    assert log.analogue__finish == [(3, 2, 32768)]


def test_a_timeline_too_large_for_the_arrays_is_refused_before_anything_is_written(
    monkeypatch,
):
    monkeypatch.setitem(wt_adwin.ROWS__MAX, "digital__finish", 1)
    machine = _MachineRecording()

    with pytest.raises(ValueError, match=r"'digital__finish': 2.* room for.* 1"):
        adwin.upload(*_with_a_final_state(), machine, 1)

    assert not machine.par and not machine.data, "nothing was written"


def test_upload_refuses_a_timeline_with_no_run():
    """
    Every update in a special context means the experiment has no duration, and the end
    cycle cannot be derived. That used to be a bare `ValueError: zero-size array`.
    """
    _, conns, devs = _digital_only()
    with pytest.raises(ValueError, match="nothing to run"):
        adwin.upload(
            tl.to_timeline(
                tl.update(shutter__MOT=1, time=-1e-6, context="ADwin_LowInit")
            ),
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
    conns = adcon.new(["shutter__MOT", 2, 11], ["AOM__MOT", 2, 1])
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

    assert _names(inside) == ["Process_Status", "Start_Process"]
    assert _names(log.machine.calls[len(inside) :]) == [
        "Process_Status",
        "Process_Status",
        "Process_Status",
        "Get_Lost_Events",
    ]
    assert run.lost_events == 0 and run.duration >= 0 and run.upload is log


def test_a_run_that_lost_events_is_refused_with_its_slip():
    """At Lab1's 5 us, 2 lost events stretch the run by 10 us."""
    log = _uploaded(lost_events=[2])
    with pytest.raises(adwin.LostEvents, match=r"lost 2 events .* 10\.0 us longer"):
        adwin.run(log)


def test_the_refusal_carries_the_record():
    log = _uploaded(lost_events=[1])
    with pytest.raises(adwin.LostEvents) as refused:
        adwin.run(log)
    assert refused.value.run.lost_events == 1
    assert refused.value.run.slip == pytest.approx(5e-6)


def test_the_count_is_read_once_after_the_run():
    """
    ADwin counts lost events since the process's start, so the count after the run is the
    run's own. Read as a difference across the run, as it was, a run that lost as many
    events as the one before it passed.
    """
    log = _uploaded(lost_events=[3])
    with pytest.raises(adwin.LostEvents, match="lost 3 events"):
        adwin.run(log)
    assert _names(log.machine.calls).count("Get_Lost_Events") == 1
    assert _names(log.machine.calls)[-1] == "Get_Lost_Events"


def test_an_error_inside_the_block_waits_the_run_out_and_goes_on(monkeypatch):
    """Not stopped: that a stop from the PC plays the final state (B11) awaits the rig."""
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    log = _uploaded(lost_events=[7])
    log.machine.status = [0, 1, 0]

    with pytest.raises(TimeoutError, match="camera"):
        with adwin.running(log):
            raise TimeoutError("camera")

    names = _names(log.machine.calls)
    assert names[-2:] == ["Process_Status", "Process_Status"], "waited until stopped"
    assert "Get_Lost_Events" not in names, "the camera's error, not a lost-events one"
    assert "Stop_Process" not in names


###############################################################################
#   D14 / #128 -- the sequencer checks the period it runs at (roadmap step 7)
###############################################################################


def test_upload_leaves_the_expected_processdelay_and_clears_the_report():
    machine = _MachineRecording(processdelay={1: 2000})
    machine.par[wt_adwin.PAR__PROCESSDELAY__REPORTED] = 2000  # an old report
    adwin.upload(*_digital_only(), machine, 1)

    assert machine.par[wt_adwin.PAR__PROCESSDELAY__EXPECTED] == 2000
    assert machine.par[wt_adwin.PAR__PROCESSDELAY__REPORTED] == 0


def test_a_run_the_sequencer_refused_says_what_it_ran_at():
    """
    The program set a Processdelay of its own once started: 2000 against the 5000 read
    before the start, which is what `upload` alone could not see.
    """
    log = _uploaded(reports=2000)
    with pytest.raises(adwin.PeriodRefused, match=r"2000 \(2 us\).* 5000 \(5 us\)"):
        adwin.run(log)


def test_a_program_that_does_not_report_is_refused():
    """A program older than the check leaves Par_14 at the 0 `upload` wrote."""
    with pytest.raises(RuntimeError, match="older than the period check"):
        adwin.run(_uploaded(reports=0))


def test_an_agreeing_run_records_what_it_ran_at():
    assert adwin.run(_uploaded()).processdelay__reported == 5000


###############################################################################
#   Step 9 -- the arrays have an owner, and nothing writes under it
###############################################################################


def _owned_by(owner, status):
    machine = _MachineRecording(status=status)
    machine.par[wt_adwin.PAR__SEQUENCE__OWNER] = owner
    return machine


def test_upload_waits_for_another_process_playing_the_arrays(monkeypatch, caplog):
    """A15's limit: process 4, the ADC variant, plays the same arrays as process 1."""
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    machine = _owned_by(4, {4: [1, 1, 0]})

    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_digital_only(), machine, 1)

    assert [r.message for r in caplog.records] == [
        "Process 4 is still running; waiting for it to stop before uploading for process"
        " 1, so as not to rewrite the arrays it is playing."
    ]
    first_write = next(
        i for i, c in enumerate(machine.calls) if c[0] != "Process_Status"
    )
    assert [c[1] for c in machine.calls[:first_write]] == [0, 1, 1, 0]


def test_an_owner_that_is_not_running_holds_nothing_up(caplog):
    """A value left behind by a process that did not finish names it; it does not block."""
    machine = _owned_by(4, {})
    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_digital_only(), machine, 1)
    assert not caplog.records


def test_starting_waits_for_another_process_playing_the_arrays(monkeypatch, caplog):
    monkeypatch.setattr(adwin, "POLL__PERIOD", 0.0)
    log = _uploaded()
    log.machine.par[wt_adwin.PAR__SEQUENCE__OWNER] = 4
    log.machine.status = {4: [1, 0]}

    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.start(log)

    assert [r.message for r in caplog.records] == [
        "Process 4 is still running; waiting for it to stop before starting process 1,"
        " which would play the same arrays."
    ]
    assert log.machine.calls[-1] == ("Start_Process", 1)


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
        demo.timeline_demo, demo.connections, demo.devices, _MachineRecording(), 1
    )
    assert len(repr(log)) < 300
    assert "rows={} analogue".format(len(log.analogue)) in repr(log)


def test_an_update_at_the_instant_a_ramp_ends_is_what_is_sent():
    """
    A18 (#153). Among a variable's rows at one instant the one written last is in
    effect, and `drop_duplicates` keeps the last of each cycle. `internal.add` sorted by
    time with pandas' default quicksort, which does not keep tied rows in written order:
    at 7 of these 20 instants the ramp's superseded end was sent instead, for one cycle,
    up to 8 A from the value commanded. Nothing raised.
    """
    conns = adcon.new(["coil__MOT__A", 3, 2], ["shutter__MOT", 1, 11])
    devs = device.new(["coil__MOT__A", 2.0, -5.0, 5.0])
    steps = [
        step
        for i in range(1, 21)
        for step in (
            tl.ramp(coil__MOT__A=0.2 * i, duration=1e-3),
            tl.update(coil__MOT__A=-0.2 * i, time=1e-3),
            tl.anchor(1e-3),
        )
    ]
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(coil__MOT__A=0.0, shutter__MOT=0, time=0.0, context="run"),
            tl.anchor(0.0),
            *steps,
        )
    )
    analogue, _ = adwin.convert(timeline, conns, devs, 5e-6)
    sent = {cycle: digits for cycle, _, _, digits in analogue}
    assert [sent[200 * i] for i in range(1, 21)] == [
        conversion.to_digits(-0.2 * i * 2.0) for i in range(1, 21)
    ]


def test_an_analogue_variable_on_the_digital_module_is_refused():
    """
    A16. It was rounded and switched as a digital line: 1.5 A on a coil became a 2 written
    to a digital output, without a word.
    """
    timeline = tl.to_timeline(tl.update(coil__MOT__A=1.5, time=0.0, context="run"))
    with pytest.raises(
        ValueError, match="coil__MOT__A on module 1: analogue by its name"
    ):
        adwin.convert(
            timeline,
            adcon.new(["coil__MOT__A", 1, 5]),
            device.new(["coil__MOT__A", 2.0, -5, 5]),
            5e-6,
        )


def test_a_digital_line_on_an_analogue_module_is_refused_by_name():
    """A16. It used to fail in a cast, naming neither the variable nor the cause."""
    timeline = tl.to_timeline(tl.update(shutter__MOT=1, time=0.0, context="run"))
    with pytest.raises(
        ValueError, match="shutter__MOT on module 3: digital by its name"
    ):
        adwin.convert(timeline, adcon.new(["shutter__MOT", 3, 5]), device.new(), 5e-6)


def _console_holding(machine, digits, touched):
    """The console's record: one entry, the coil on module 4, channel 1, at `digits`."""
    machine.par[console.PAR__ENTRIES] = 1
    machine.arrays = {
        console.DATA__MODULE: [4],
        console.DATA__CHANNEL: [1],
        console.DATA__WRITTEN: [digits],
        console.DATA__TOUCHED: [touched],
    }


def _coil_run():
    connections = adcon.new(["coil__MOT__A", 4, 1])
    devices = device.new(["coil__MOT__A", 2.0, -5, 5])
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(coil__MOT__A=-1.5, time=0.0, context="run"),
            tl.update(coil__MOT__A=-1.0, time=1.0),
        )
    )
    return timeline, connections, devices


def test_upload_warns_of_a_channel_the_run_jumps_from_a_console_value(caplog):
    """The coil set to 2 A by hand, and the run's first row for it at -1.5 A."""
    machine = _MachineRecording()
    _console_holding(machine, conversion.to_digits(4.0), touched=1)
    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_coil_run(), machine, 1)
    assert [r.message for r in caplog.records] == [
        "The run will jump 1 analogue channel(s) from a value set on the console:"
        " coil__MOT__A from 2 to -1.5 A, at 0 s."
    ]


def test_upload_is_quiet_about_a_value_the_console_did_not_set(caplog):
    """The same record, but adopted from the last run's final state rather than set by hand."""
    machine = _MachineRecording()
    _console_holding(machine, conversion.to_digits(4.0), touched=0)
    with caplog.at_level("WARNING", logger="wtlog"):
        adwin.upload(*_coil_run(), machine, 1)
    assert not caplog.records


def test_a_specification_carrying_a_cycle_period_is_refused():
    """Accepting it with the period unused would be D15 again, one layer down."""
    specifications = {"cycle_period": 2e-6, **adi.SPECIFICATIONS__DEFAULT}
    with pytest.raises(ValueError, match="no longer read"):
        adwin.convert(*_digital_only(), 2e-6, machine_specifications=specifications)


###############################################################################
#   Step 10 -- the ADC variant records in a window stated in cycles
###############################################################################


class _MachineRecordingADC(_MachineRecording):
    """
    Adds what `adc` touches, and plays `WignerTimeADwinADC.bas`'s half of the contract on
    each start, line for line: `lowinit:` turns the duration into samples, reports the
    sample period and arms only a window inside the run; `finish:` reports the samples only
    if the run lasted until the window closed, then disarms. `stopped_at` ends the run at
    that cycle; `old_program` plays a program older than the contract, which reports nothing.
    """

    TIME_INTERVAL__US = 0.25  # ADC_TimeInterval
    MAX_DATA_AMOUNT = 67108860  # ADC_MaxDataAmount

    def __init__(self, stopped_at=None, old_program=False, **machine):
        machine.setdefault("processdelay", {4: 5000})
        super().__init__(**machine)
        self.fpar = {}
        self.stopped_at = stopped_at
        self.old_program = old_program

    def Set_FPar(self, number, value):
        self.calls.append(("Set_FPar", number))
        self.fpar[number] = value

    def Get_FPar(self, number):
        return self.fpar.get(number, 0.0)

    def GetData_Int64(self, number, startindex, count):
        self.calls.append(("GetData_Int64", number))
        return list(range(startindex, startindex + count))

    def Start_Process(self, process):
        super().Start_Process(process)
        if self.old_program:
            return
        par, fpar = self.par, self.fpar
        # lowinit:
        amount = int(1000000 * fpar.get(61, 0.0) / self.TIME_INTERVAL__US)
        amount = min(amount, self.MAX_DATA_AMOUNT)
        par[44] = int(self.TIME_INTERVAL__US * 1000)
        start, end, end_cc = par.get(42, 0), par.get(43, 0), par.get(1, 0)
        if start < 0 or end <= start or end > end_cc:
            start = -1
        # the run, then finish:
        cyclecount = end_cc + 1 if self.stopped_at is None else self.stopped_at
        par[41] = amount if (start >= 0 and cyclecount > end) else 0
        par[43] = 0


def _uploaded__ADC(**machine):
    """An upload for process 4, the ADC variant; `_digital_only` runs from 0 to 1 s."""
    log = adwin.upload(*_digital_only(), _MachineRecordingADC(**machine), 4)
    log.machine.calls.clear()
    return log


@pytest.mark.parametrize(
    "processdelay, cycle__start, cycles", [(5000, 100_000, 2), (2000, 250_000, 5)]
)
def test_the_window_is_written_in_cycles_at_the_machines_period(
    processdelay, cycle__start, cycles
):
    """
    At 0.5 s, and at both labs' periods. The program used to divide by a fixed 5 us, so at
    Lab2's 2 us it would have written 100 000 for 0.5 s, which is 0.2 s.
    """
    log = _uploaded__ADC(processdelay={4: processdelay})
    window = adc.arm(log, 0.5, 10e-6)

    assert log.machine.par[adc.PAR__CYCLE__START] == cycle__start
    assert log.machine.par[adc.PAR__CYCLE__END] == window.cycle__end
    assert window.cycle__end - cycle__start == cycles  # 10 us, exactly, at 2 us too
    assert log.machine.fpar[adc.FPAR__DURATION] == 10e-6
    assert window.time__start == pytest.approx(0.5)


def test_a_recording_is_timed_from_the_start_as_armed():
    samples = adc.run(_uploaded__ADC(), 0.5, 10e-6)

    assert len(samples.digits) == 40  # 10 us at 0.25 us
    assert samples.time[0] == pytest.approx(0.5)
    assert samples.time[1] - samples.time[0] == pytest.approx(0.25e-6)
    assert samples.run.upload is samples.window.upload


def test_arming_clears_what_the_program_reports():
    """So that a report after the run is this run's, not one left from an earlier one."""
    log = _uploaded__ADC()
    log.machine.par[adc.PAR__SAMPLES] = 7
    log.machine.par[adc.PAR__SAMPLE_PERIOD__NS] = 250
    adc.arm(log, 0.5, 10e-6)
    assert log.machine.par[adc.PAR__SAMPLES] == 0
    assert log.machine.par[adc.PAR__SAMPLE_PERIOD__NS] == 0


def test_only_the_ADC_variant_records():
    with pytest.raises(
        ValueError, match="process 4, but this upload was made for process 1"
    ):
        adc.arm(_uploaded(), 0.5, 10e-6)


@pytest.mark.parametrize(
    "t, duration, match",
    [
        (0.99, 0.5, "ends after the run, which ends at 1 s"),
        (-0.1, 0.5, "cannot start before the run"),
        (0.5, 0.0, "positive number of seconds"),
    ],
)
def test_a_window_outside_the_run_is_refused(t, duration, match):
    """The samples are read out in `finish:`: a burst still under way there is partly stale."""
    log = _uploaded__ADC()
    with pytest.raises(ValueError, match=match):
        adc.arm(log, t, duration)
    assert "Set_Par" not in _names(log.machine.calls), "nothing armed"


def test_a_window_is_armed_for_one_run():
    """A second run without arming records nothing, and says so; `adc.run` arms each time."""
    log = _uploaded__ADC()
    window = adc.arm(log, 0.5, 10e-6)
    adc.read(window, adwin.run(log))

    with pytest.raises(RuntimeError, match="not armed"):
        adc.read(window, adwin.run(log))
    assert len(adc.run(log, 0.5, 10e-6).digits) == 40


def test_a_run_that_ended_before_the_window_closed_records_nothing():
    log = _uploaded__ADC(
        stopped_at=100_001
    )  # inside the window, which closes at 100 002
    window = adc.arm(log, 0.5, 10e-6)
    with pytest.raises(RuntimeError, match="ended before cycle 100002"):
        adc.read(window, adwin.run(log))


def test_a_program_older_than_the_contract_is_refused():
    """It would have placed the window by its own 5 us, whatever the machine runs at."""
    with pytest.raises(RuntimeError, match="did not report its sample period"):
        adc.run(_uploaded__ADC(old_program=True), 0.5, 10e-6)


def test_a_window_longer_than_the_buffer_is_refused(monkeypatch):
    monkeypatch.setattr(_MachineRecordingADC, "MAX_DATA_AMOUNT", 10)
    with pytest.raises(
        RuntimeError, match="recorded 10 samples.*longer than its buffer"
    ):
        adc.run(_uploaded__ADC(), 0.5, 10e-6)


def test_a_window_is_read_only_after_its_own_run(monkeypatch):
    log = _uploaded__ADC()
    window = adc.arm(log, 0.5, 10e-6)
    with pytest.raises(ValueError, match="has not been waited for"):
        adc.read(window, adwin.start(log))

    other = _uploaded__ADC()
    with pytest.raises(ValueError, match="armed for another upload"):
        adc.read(window, adwin.run(other))


###############################################################################
#   D19 / D20 -- what the real-time program can play
###############################################################################


def _with_a_row_at(time, cycle_period=5e-6):
    timeline, conns, devs = _digital_only()
    timeline = tl.to_timeline(
        tl.update(shutter__MOT=1, time=time, origin=0.0), onto=timeline
    )
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
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(shutter__MOT=0, AOM__MOT=0, time=-1e-3, context="ADwin_LowInit"),
            tl.update(shutter__MOT=1, time=1.0, origin=0.0, context="run"),
        )
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


def test_a_ramp_keeps_its_own_resolution_through_conversion():
    """
    #65: a coarse ramp in a timeline converted at the cycle period. Bound with a
    `partial`, it used to be sampled at the 5 us cycle regardless, since `convert` passes
    the cycle period to `expand` and `expand` handed it to every function declaring it.
    """
    import functools

    from wignertime import ramp_function

    conns = adcon.new(["coil__MOT__A", 3, 2])
    devs = device.new(["coil__MOT__A", 2.0, -5.0, 5.0])
    timeline = tl.to_timeline(
        tl.stack(
            tl.update(coil__MOT__A=0.0, time=0.0, context="run"),
            tl.anchor(0.0),
            tl.ramp(
                coil__MOT__A=1.0,
                duration=1e-3,
                function=functools.partial(ramp_function.tanh, time_resolution=1e-4),
            ),
        )
    )
    analogue, _ = adwin.convert(timeline, conns, devs, 5e-6)
    cycles = [cycle for cycle, _, _, _ in analogue]
    assert cycles == list(range(0, 201, 20))


###############################################################################
#   #154 -- rows before the run at -inf, after it at +inf
###############################################################################


def _before_and_after(before, after):
    import math

    conns = adcon.new(["shutter__MOT", 1, 11], ["AOM__MOT", 1, 1])
    return (
        tl.to_timeline(
            tl.stack(
                *[
                    tl.update(time=-math.inf, context=context, **values)
                    for context, values in before
                ],
                tl.update(shutter__MOT=1, time=0.0, context="run"),
                tl.anchor(1.0),
                tl.update(time=math.inf, context="ADwin_Finish", **after),
            )
        ),
        conns,
        device.new(),
    )


def test_the_state_before_and_after_the_run_converts_at_the_sentinels():
    """
    Cycles are computed for finite rows only: ±inf used to be cast to an integer, with a
    numpy warning, before the sentinels overwrote it.
    """
    import warnings

    timeline, conns, devs = _before_and_after(
        [("ADwin_LowInit", dict(shutter__MOT=0, AOM__MOT=1))], dict(shutter__MOT=0)
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _, digital = adwin.convert(timeline, conns, devs, 5e-6)
    assert [row[0] for row in digital] == [-2, -2, 0, 2**31 - 1]


def test_a_row_at_infinity_outside_the_special_contexts_is_refused():
    import math

    timeline, conns, devs = _digital_only()
    timeline = tl.to_timeline(
        tl.update(AOM__MOT=0, time=math.inf, context="run"), onto=timeline
    )
    with pytest.raises(ValueError, match="must be at an instant of the run"):
        adwin.convert(timeline, conns, devs, 5e-6)


def test_a_variable_set_in_both_lowinit_and_init_is_refused():
    """
    (b1): both are at -inf, so nothing orders them. They used to be counted per
    context, so this was accepted, and the `init:` value was in force.
    """
    timeline, conns, devs = _before_and_after(
        [("ADwin_LowInit", dict(shutter__MOT=0)), ("ADwin_Init", dict(shutter__MOT=1))],
        dict(shutter__MOT=0),
    )
    with pytest.raises(ValueError, match="more than one value before the run"):
        adwin.convert(timeline, conns, devs, 5e-6)


def test_lowinit_and_init_may_set_different_variables():
    timeline, conns, devs = _before_and_after(
        [("ADwin_LowInit", dict(shutter__MOT=0)), ("ADwin_Init", dict(AOM__MOT=1))],
        dict(shutter__MOT=0),
    )
    _, digital = adwin.convert(timeline, conns, devs, 5e-6)
    assert [row[0] for row in digital] == [-2, -1, 0, 2**31 - 1]
