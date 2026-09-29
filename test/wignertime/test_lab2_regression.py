"""
A real experiment, frozen from the rig, run end to end through the package.

The description is a timeline written by **Dániel Varga** for the Lab2 atom-cavity
apparatus, taken out of the running experiment on **2026-09-21** and reconciled against
the package on **2026-09-22**. Everything the pipeline needs is in
`fixtures/lab2/` — 13 KB for a run that drives ten analogue and fourteen digital channels
over 12.5 s.

What this is for: the demo exercises the package against an experiment written to suit it.
This exercises it against one that was not — 131 rows, 35 variables, eleven anchors, ramps
of three different sharpnesses, and an apparatus table that predates several of the
package's own conventions.

The checksums pin today's output. They are *not* the values the rig was given: the archive
was produced by a pre-rename Wigner Time, and two deliberate changes since then account
for every difference, both measured rather than assumed:

- `drop_repeats` (new on this branch) removes **82.7%** of the analogue rows — 885 542
  becomes 153 463. Disabling it reproduces the archived count exactly.
- `range__inclusive` (B9, #134) changed the point count of a ramp whose duration is an
  exact multiple of the step, which moves the sample grid slightly. Every tuple still
  matches on `(cycle, module, channel)`; the digits differ by at most 20 parts in 65 536,
  and only on the five channels B9 touched.

`converted/README.md` beside the takeout has the full reconciliation.
"""

import hashlib
import pathlib
import re

import numpy as np
import pandas as pd
import pytest

from wignertime import config, device, ramp_function
from wignertime import timeline as tl
from wignertime.adwin import core

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "lab2"

CYCLE_PERIOD = 2e-6
"""Lab2's ADwin runs at 2 us, not the 5 us of the committed `WignerTimeADwin.bas`."""

EXPANDED__ROWS = 885601
EXPANDED__DIGEST = "7a8d2e753a12ca40643a72e289c1c570a87074d7731dac1c650ac5210b4c6eac"
ANALOGUE__ROWS = 153463
ANALOGUE__DIGEST = "b1bf336f9d55e0c33513cfd1ea3361d7bcb539adc274c2194d08743a75817e65"
DIGITAL__ROWS = 43
DIGITAL__DIGEST = "53f50dbb25ae6a78cbaa2458f7147811db78eb29fd4753c06a6054e6b6a6ba06"


@pytest.fixture(scope="module", autouse=True)
def _lab2_naming():
    """
    Lab2 has a `dispenser__A`, which has no UID and which the present default refuses.

    `config.VARIABLE__REGEX` is documented as a *default* that a site may rebind, so this
    is the sanctioned route rather than a workaround — and exercising it is worth
    something in itself, since nothing else does.
    """
    original = config.VARIABLE__REGEX
    config.VARIABLE__REGEX = re.compile(
        r"^([^_]+)(?:_([^_]+(?:_[^_]+)*))?(?:__([^_]+))?$"
    )
    yield
    config.VARIABLE__REGEX = original


def _ramp_function(sharpness):
    """
    Rebuild a ramp function from its descriptor.

    The takeout stored these as closures, which only `dill` can serialise and only against
    a matching Python. Each was `tanh` with one number, so each is written down in the
    fixture instead. The parameter *names* matter: `expand` filters its keywords against
    the signature, so `time_resolution` has to be called that.
    """
    return lambda origin, terminus, time_resolution: ramp_function.tanh(
        origin, terminus, time_resolution, sharpness
    )


@pytest.fixture(scope="module")
def timeline():
    described = pd.read_parquet(FIXTURES / "timeline.parquet")
    cache = {}
    functions = [
        (
            np.nan
            if not isinstance(name, str)
            else cache.setdefault(float(sharpness), _ramp_function(float(sharpness)))
        )
        for name, sharpness in zip(
            described["function"], described["function__sharpness"]
        )
    ]
    out = described.drop(columns=["function__sharpness"]).copy()
    out["function"] = functions
    return out


@pytest.fixture(scope="module")
def connections():
    return pd.read_parquet(FIXTURES / "connections.parquet")


@pytest.fixture(scope="module")
def devices():
    return pd.read_parquet(FIXTURES / "devices.parquet")[
        ["variable", "to_V", "value__min", "value__max"]
    ]


@pytest.fixture(scope="module")
def converted(timeline, connections, devices):
    """
    Run once for the module: the conversion takes a few seconds at this size.

    Lab2's modules are those of `SPECIFICATIONS__DEFAULT`; only the period differs, and
    it is an argument rather than an entry in the specifications (#94). The ramps are
    sampled at it too, as `time_resolution` defaults to it -- this used to be stated
    twice, once for each.
    """
    return core.convert(
        timeline,
        connections[connections["variable"] != "imaging_beam_intensity__V"],
        devices,
        CYCLE_PERIOD,
    )


def _digest__tuples(rows):
    ordered = sorted(tuple(int(x) for x in row) for row in rows)
    return hashlib.sha256(np.asarray(ordered, dtype=np.int64).tobytes()).hexdigest()


# --- the description itself ---------------------------------------------------


def test_the_fixture_is_the_experiment_it_claims_to_be(timeline):
    assert len(timeline) == 131
    assert timeline["variable"].nunique() == 35
    assert sum(v.startswith("⚓") for v in timeline["variable"].unique()) == 11

    sharpnesses = sorted(
        set(
            pd.read_parquet(FIXTURES / "timeline.parquet")[
                "function__sharpness"
            ].dropna()
        )
    )
    assert sharpnesses == [0.3, 1.6, 3.0]


def test_every_ramp_function_is_data_rather_than_code():
    """
    The point of the fixture: the takeout's closures were reduced to a name and a number,
    and the reconstruction has to reproduce the curve exactly or the archive is worthless.
    """
    described = pd.read_parquet(FIXTURES / "timeline.parquet")
    named = set(described["function"].dropna())
    assert named == {"wignertime.ramp_function.tanh"}

    origin, terminus, resolution = [0.0, 1.0], [0.5, 4.0], 1e-3
    for sharpness in sorted(set(described["function__sharpness"].dropna())):
        assert np.allclose(
            _ramp_function(sharpness)(origin, terminus, resolution),
            ramp_function.tanh(origin, terminus, resolution, sharpness),
        )


# --- what the apparatus tables say --------------------------------------------


def test_lab2_connects_an_analogue_channel_it_does_not_calibrate(connections, devices):
    """
    A14, against a real apparatus rather than a constructed one.
    `imaging_beam_intensity__V` is wired to module 3 channel 2 and has no device, so it
    would be driven with neither a conversion nor a safety range.

    Latent rather than live: that channel carries no rows in this run. It would not be,
    the first time imaging is used with this table.
    """
    with pytest.raises(ValueError, match="do not describe the same apparatus"):
        device.check_correspondence(connections, devices)

    assert "imaging_beam_intensity__V" in set(connections["variable"])
    assert "imaging_beam_intensity__V" not in set(devices["variable"])


# --- the pipeline -------------------------------------------------------------


def test_expansion_is_unchanged(timeline):
    expanded = tl.expand(timeline, time_resolution=CYCLE_PERIOD)

    assert len(expanded) == EXPANDED__ROWS
    assert expanded["time"].max() == pytest.approx(12.4991, abs=1e-4)

    ordered = expanded.sort_values(["variable", "time", "value"]).reset_index(drop=True)
    digest = hashlib.sha256()
    digest.update(chr(0).join(ordered["variable"].astype(str)).encode())
    digest.update(ordered["time"].to_numpy().tobytes())
    digest.update(ordered["value"].to_numpy().tobytes())
    assert digest.hexdigest() == EXPANDED__DIGEST


def test_conversion_is_unchanged(converted):
    analogue, digital = converted

    assert len(analogue) == ANALOGUE__ROWS
    assert len(digital) == DIGITAL__ROWS
    assert _digest__tuples(analogue) == ANALOGUE__DIGEST
    assert _digest__tuples(digital) == DIGITAL__DIGEST


def test_the_run_fits_the_machine(converted):
    """
    The arrays are never cleared, so a run has to fit them (#8), and the counts are what
    tell the real-time program how much to read.
    """
    analogue, digital = converted
    special = {-2, -1, 2**31 - 1}

    cycles = [int(r[0]) for r in analogue if int(r[0]) not in special]
    assert max(cycles) * CYCLE_PERIOD == pytest.approx(12.499, abs=1e-3)
    assert len(analogue) < 10_000_000, "analogMaxArrayDim in WignerTimeADwin.bas"
    assert len(digital) < 10_000, "digitalMaxArrayDim"

    assert {(int(r[1]), int(r[2])) for r in analogue} == {
        (3, 3),
        (3, 4),
        (3, 5),
        (4, 1),
        (4, 2),
        (4, 3),
        (4, 4),
        (4, 5),
        (4, 6),
        (4, 8),
    }
