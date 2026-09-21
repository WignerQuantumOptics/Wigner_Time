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
    tst = frame.cast(adi.add_cycle(df), wt_adwin.SCHEMA)

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
    Stands in for `ADwin.ADwin`, recording what `core.create` would transfer.

    The hardware calls are the part of the export that cannot be exercised here
    (`KNOWN_ISSUES` §E), so this covers the argument assembly around them and nothing
    more: which parameters are set, and which data arrays are written.
    """

    def __init__(self):
        self.par = {}
        self.data = {}

    def Set_Par(self, number, value):
        self.par[number] = value

    def SetData_Long(self, values, number, startindex, count):
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


def test_create_transfers_an_empty_analogue_set_as_a_count_of_zero():
    """
    #73. An empty set used to raise `IndexError: too many indices` while computing the
    end cycle -- before any `Set_Par` -- so nothing was transferred at all and the
    machine kept the whole of the previous experiment, which then ran.

    The count is what tells the real-time program not to read the array, and it has to
    be set precisely because the arrays are never cleared (#8).
    """
    machine = _MachineRecording()
    adwin.create(*_digital_only(), machine=machine)

    assert machine.par[2] == 0, "analogue count must be transferred as zero"
    assert machine.par[3] == 3, "digital count unaffected"
    assert sorted(machine.data) == [20, 21, 22, 23], "only the digital arrays written"


def test_create_transfers_both_sets_when_both_are_populated():
    machine = _MachineRecording()
    adwin.create(demo.timeline__demo, demo.connections, demo.devices, machine=machine)

    assert sorted(machine.data) == [10, 11, 12, 13, 20, 21, 22, 23]
    assert machine.par[2] == len(machine.data[10][0]) > 0
    assert machine.par[3] == len(machine.data[20][0]) > 0


def test_create_refuses_a_timeline_with_no_run():
    """
    Every update in a special context means the experiment has no duration, and the end
    cycle cannot be derived. That used to be a bare `ValueError: zero-size array`.
    """
    _, conns, devs = _digital_only()
    with pytest.raises(ValueError, match="nothing to run"):
        adwin.create(
            tl.create(shutter_MOT=1, t=-1e-6, context="ADwin_LowInit"),
            conns,
            devs,
            machine=_MachineRecording(),
        )
