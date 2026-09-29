"""
The cases behind `test_reference.py`, and the one way to regenerate their frozen outputs.

Defined here rather than in the test module because the test module reads the frozen files
while it is being collected, so it cannot also be what writes them. Run this file only when
a change of output is intended, and say so in the commit:

    PYTHONPATH=.. poetry run python test/wignertime/reference_cases.py

`PYTHONPATH=..` makes the lab's package next door importable; regeneration needs it.
"""

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

from wignertime import timeline as tl
from wignertime.internal import util as wt_util

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "reference"

PERIODS = (5e-6, 2e-6, 1e-6)
"""Lab1's period, Lab2's, and the finest either would be run at."""

COLUMNS = ["time", "variable", "value", "context"]

TOLERANCE = 1e-12
"""
Absolute, in seconds and in each variable's own unit. Far below anything the hardware can
resolve, and above the rounding a refactor may move by reordering the same arithmetic.
"""

FUNCTION__SAMPLE = dict(origin=[0.0, 0.0], terminus=[1.0, 1.0], time_resolution=0.25)
"""The fixed input each ramp function is sampled on to describe it."""

LAB__SHOT = "imaging at MT"
"""The lab case whose arrays are pinned: a whole shot, preparation, imaging and finish."""


# --- describing a timeline as data ------------------------------------------------


def _function__name(f):
    return "{}.{}".format(
        getattr(f, "__module__", "?"), getattr(f, "__qualname__", repr(f))
    )


def _function__points(f):
    """What a ramp function does, written down: its curve on `FUNCTION__SAMPLE`."""
    sampled = wt_util.function__filtered_kws(
        f, time_resolution=FUNCTION__SAMPLE["time_resolution"]
    )(FUNCTION__SAMPLE["origin"], FUNCTION__SAMPLE["terminus"])
    return ";".join("{:.12g},{:.12g}".format(t, v) for t, v in np.asarray(sampled))


def describe(timeline):
    """
    The base columns, with each ramp function reduced to its name and its curve. The name
    is kept for whoever reads the file; the comparison uses the curve.
    """
    out = timeline[COLUMNS].reset_index(drop=True).copy()
    functions = (
        timeline["function"].tolist()
        if "function" in timeline.columns
        else [None] * len(timeline)
    )
    cache = {}
    out["function"] = [_function__name(f) if callable(f) else None for f in functions]
    out["function__points"] = [
        cache.setdefault(id(f), _function__points(f)) if callable(f) else None
        for f in functions
    ]
    return out


def digest__tuples(rows):
    """As in `test_lab2_regression.py`: order-free, over the integers the machine gets."""
    ordered = sorted(tuple(int(x) for x in row) for row in rows)
    return hashlib.sha256(np.asarray(ordered, dtype=np.int64).tobytes()).hexdigest()


def convert(timeline, connections, devices, period):
    """
    `adwin.core.convert` at `period`. The period used to travel in the machine
    specifications; since `issue#94` it is an argument of its own, and the ramps are
    sampled at it unless a resolution is given.
    """
    from wignertime.adwin import core

    return core.convert(timeline, connections, devices, period)


def arrays(timeline, connections, devices, period):
    analogue, digital = convert(timeline, connections, devices, period)
    return {
        "analogue__rows": len(analogue),
        "analogue__digest": digest__tuples(analogue),
        "digital__rows": len(digital),
        "digital__digest": digest__tuples(digital),
    }


def key(period):
    return "{:g}".format(period)


# --- the cases --------------------------------------------------------------------


def demo_cases():
    """The demo module, and its cases by name."""
    from wignertime.demo import full_experiment as ex

    return ex, {
        "timeline__demo": lambda: ex.timeline__demo,
        "trigger_camera at molasses (sec:interweaving)": lambda: tl.to_timeline(
            ex.trigger_camera(2e-3, 1e-3, "imaging", origin="molasses"),
            onto=ex.timeline__demo,
        ),
    }


def lab_cases(ex, di):
    """
    `ex` and `di` are the lab's `timeline.experiment` and `timeline.diagnostics`, as its
    `issue#85` branch has them: `prepare_sample` and the imaging are stages. Each stage's
    context is named after the stage, which is what the imaging is placed against.
    """
    cases = {}
    for stage in ex.Stage:
        for finish in (True, False):
            for dispenser_off in (-1.0, 0.5):
                name = "prepare_sample stage={} finish={} dispenser_off={}".format(
                    stage.name, finish, dispenser_off
                )
                cases[name] = (
                    lambda stage=stage, finish=finish, off=dispenser_off: tl.to_timeline(
                        ex.prepare_sample(
                            stage=stage,
                            add_finish=finish,
                            duration_without_dispenser=off,
                        )
                    )
                )

    for stage in ex.Stage:
        cases["imaging at {}".format(stage.name)] = lambda stage=stage: tl.to_timeline(
            di.imaging_absorption(3e-3, 1e-4, origin=stage.name),
            onto=tl.to_timeline(di.prepare_sample(stage=stage)),
        )

    base = {}

    def _base():
        if "MT" not in base:
            base["MT"] = tl.to_timeline(di.prepare_sample(stage=ex.Stage.MT))
        return base["MT"]

    for delay in (1, 2, 3):
        cases["time of flight {} ms, onto one base".format(delay)] = (
            lambda delay=delay: tl.to_timeline(
                di.imaging_absorption(1e-3 * delay, 1e-4, origin="MT"), onto=_base()
            )
        )
    return cases


# --- regeneration -----------------------------------------------------------------


def _freeze(cases):
    return pd.concat(
        [describe(build()).assign(case=name) for name, build in cases.items()],
        ignore_index=True,
    )[["case", *COLUMNS, "function", "function__points"]]


if __name__ == "__main__":
    from quantum_optics_lab.timeline import diagnostics as di
    from quantum_optics_lab.timeline import experiment as ex_lab

    FIXTURES.mkdir(parents=True, exist_ok=True)
    ex_demo, cases__demo = demo_cases()
    cases__lab = lab_cases(ex_lab, di)

    _freeze(cases__demo).to_parquet(FIXTURES / "demo.parquet", index=False)
    _freeze(cases__lab).to_parquet(FIXTURES / "quantum_optics_lab.parquet", index=False)
    frozen = {
        "timeline__demo": {
            key(p): arrays(
                cases__demo["timeline__demo"](), ex_demo.connections, ex_demo.devices, p
            )
            for p in PERIODS
        },
        LAB__SHOT: {
            key(p): arrays(cases__lab[LAB__SHOT](), di.connections, ex_lab.devices, p)
            for p in PERIODS
        },
    }
    (FIXTURES / "arrays.json").write_text(json.dumps(frozen, indent=2) + "\n")
    print("wrote", sorted(p.name for p in FIXTURES.iterdir()))
