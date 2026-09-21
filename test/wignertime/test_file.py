import pytest
from pathlib import Path

from wignertime import file
from wignertime import timeline as tl
from wignertime.internal import dataframe as frame


from wignertime.demo import full_experiment as demo


@pytest.fixture(autouse=True)
def _in_a_directory_of_its_own(tmp_path, monkeypatch):
    """
    Run each test in a fresh directory.

    `file.save` resolves a relative path against the cwd and, on a collision, appends
    `__002`, `__003`, … rather than overwriting. Run from the repository root that left
    fourteen files there per run, the numbered ones accumulating without limit — and it
    made two of the tests below dishonest:

    - `test_save_load__autoname` saved, found the name taken, wrote `…__00N` instead, and
      then loaded the *original* — an artefact of some earlier run. It was comparing
      against a file it had not written.
    - `test_save_load__increment_name` asserted that `…__002` and `…__003` exist, which
      after the first run they already did, whoever had made them.

    A fresh directory per test fixes the pollution, bounds the growth (pytest keeps the
    last three runs and discards the rest), and makes both assertions mean what they say.
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def timeline__demo():
    return tl.cascade(
        demo.init,
        demo.MOT,
    )


@pytest.fixture
def timeline__demo__function():
    return tl.cascade(demo.init, demo.MOT, demo.MOT__detuned_growth)


def test_save_load__autoname(timeline__demo):
    file.save(timeline__demo)
    actual = file.load("timeline__demo.parquet")
    return frame.assert_equal(actual, timeline__demo)


@pytest.mark.parametrize(
    "fname",
    [
        "timeline__demo.parquet",
        "timeline__demo.csv",
        "timeline__demo.json",
        "timeline__demo.pickle",
        "timeline__demo.feather",
    ],
)
def test_save_load__types(fname, timeline__demo):
    file.save(timeline__demo, fname)
    actual = file.load(fname)
    return frame.assert_equal(actual, timeline__demo)


@pytest.mark.parametrize(
    "fname",
    [
        "timeline__demo__function.parquet",
        "timeline__demo__function.csv",
        "timeline__demo__function.json",
        "timeline__demo__function.pickle",
        "timeline__demo__function.feather",
    ],
)
def test_save_load__types_with_functions(fname, timeline__demo__function):
    file.save(timeline__demo__function, fname)
    actual = file.load(fname)

    mask = actual["function"].notna()

    if bool(actual.loc[mask, "function"].map(lambda x: isinstance(x, str)).all()):
        output = timeline__demo__function.copy(deep=True)
        output.loc[mask, "function"] = "wignertime.ramp_function.tanh"
    else:
        output = timeline__demo__function

    return frame.assert_equal(actual, output)


def test_save_load__increment_name(timeline__demo):
    file.save(timeline__demo)
    t1 = Path("timeline__demo.parquet").exists()
    file.save(timeline__demo)
    t2 = Path("timeline__demo__002.parquet").exists()
    file.save(timeline__demo)
    t3 = Path("timeline__demo__003.parquet").exists()

    assert t1 and t2 and t3


@pytest.mark.parametrize("suffix", [".parquet", ".csv", ".json", ".pickle", ".feather"])
def test_save_load__nulls_survive_the_round_trip(suffix, timeline__demo__function):
    """
    A missing value must come back as the same thing it went in as, whichever format was
    chosen.

    It did not: an in-memory timeline holds `nan` where a column does not apply — what
    `concat` leaves when a frame without a `function` column is joined to one that has
    it — while parquet, JSON and feather returned `None` and CSV and pickle returned
    `nan`. `assert_frame_equal` merely *warned* about the mismatch, and says it will stop
    treating the two as matching, so the comparison above would have become an error
    without anyone having changed anything. `file.load` now settles on one
    representation.
    """
    written = file.save(timeline__demo__function, "round_trip" + suffix)
    back = file.load(str(written))

    def kinds(column):
        return {type(v) for v in column if not callable(v) and not isinstance(v, str)}

    assert kinds(back["function"]) == kinds(timeline__demo__function["function"])
    assert not any(v is None for v in back["function"])
