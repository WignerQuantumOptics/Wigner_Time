"""
Reference outputs for the #85 migration (C7 in `KNOWN_ISSUES.md`), frozen on 2026-09-29.

Composition changes shape along #85's roadmap -- stages stop taking `timeline=`, `create`
goes, a ramp starts where its variable is -- but the tables it produces must not. These
tests pin those tables as they were before any of it, so that every later step has to
reproduce them:

- the demo's `timeline__demo`, and the camera trigger `sec:interweaving` places into it;
- the ADwin arrays the demo converts to, at 5, 2 and 1 us;
- the lab's `prepare_sample` next door (`../quantum_optics_lab`) at each of its five
  stages, with and without its finish and with and without the dispenser switch-off;
  absorption imaging interwoven into each stage; a time-of-flight series placed onto one
  base, as `sec:parameter_scan` does; and the arrays of one real shot.

The lab cases run only when `quantum_optics_lab` can be imported:

    PYTHONPATH=.. poetry run pytest test/wignertime/test_reference.py

Between P2 and P5 of the roadmap they are expected to fail, while the package's API has
moved and the lab's code has not; they are then the lab migration's acceptance test.

A ramp's function is compared by what it does, not by its name: each is sampled on a fixed
input, so renaming `pull_coils` (D7) is not a change and altering its curve is. Row order
is part of the reference, because among rows that share an instant the one written last is
in effect. The cases, and how to regenerate them, are in `reference_cases.py`.
"""

import json

import pandas as pd
import pytest
import reference_cases as ref


def _frozen(name):
    return pd.read_parquet(ref.FIXTURES / "{}.parquet".format(name))


def _cases(name):
    return list(dict.fromkeys(_frozen(name)["case"]))


def _arrays(case):
    return json.loads((ref.FIXTURES / "arrays.json").read_text())[case]


def _assert_same(built, frozen):
    pd.testing.assert_frame_equal(
        ref.describe(built),
        frozen.drop(columns="case").reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        rtol=0,
        atol=ref.TOLERANCE,
    )


def _lab():
    ex = pytest.importorskip(
        "quantum_optics_lab.timeline.experiment",
        reason="the lab's code is next door; run with PYTHONPATH=.. to include it",
    )
    di = pytest.importorskip("quantum_optics_lab.timeline.diagnostics")
    return ex, di


@pytest.mark.parametrize("case", _cases("demo"))
def test_demo_is_unchanged(case):
    _, cases = ref.demo_cases()
    frozen = _frozen("demo")
    _assert_same(cases[case](), frozen[frozen["case"] == case])


@pytest.mark.parametrize("period", ref.PERIODS, ids=ref.key)
def test_demo_arrays_are_unchanged(period):
    pytest.importorskip("ADwin")
    ex, cases = ref.demo_cases()
    built = ref.arrays(cases["timeline__demo"](), ex.connections, ex.devices, period)
    assert built == _arrays("timeline__demo")[ref.key(period)]


@pytest.mark.parametrize("case", _cases("quantum_optics_lab"))
def test_lab_is_unchanged(case):
    ex, di = _lab()
    frozen = _frozen("quantum_optics_lab")
    _assert_same(ref.lab_cases(ex, di)[case](), frozen[frozen["case"] == case])


@pytest.mark.parametrize("period", ref.PERIODS, ids=ref.key)
def test_lab_arrays_are_unchanged(period):
    pytest.importorskip("ADwin")
    ex, di = _lab()
    built = ref.arrays(
        ref.lab_cases(ex, di)[ref.LAB__SHOT](), di.connections, ex.devices, period
    )
    assert built == _arrays(ref.LAB__SHOT)[ref.key(period)]
