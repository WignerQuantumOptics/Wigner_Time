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
def timeline_demo():
    return tl.to_timeline(tl.cascade(demo.init, demo.MOT))


@pytest.fixture
def timeline_demo_function():
    return tl.to_timeline(tl.cascade(demo.init, demo.MOT, demo.MOT_detuned_growth))


def test_save_load__autoname(timeline_demo):
    file.save(timeline_demo)
    actual = file.load("timeline_demo.parquet")
    return frame.assert_equal(actual, timeline_demo)


@pytest.mark.parametrize(
    "fname",
    [
        "timeline_demo.parquet",
        "timeline_demo.csv",
        "timeline_demo.json",
        "timeline_demo.pickle",
        "timeline_demo.feather",
    ],
)
def test_save_load__types(fname, timeline_demo):
    file.save(timeline_demo, fname)
    actual = file.load(fname)
    return frame.assert_equal(actual, timeline_demo)


@pytest.mark.parametrize(
    "fname",
    [
        "timeline_demo_function.parquet",
        "timeline_demo_function.csv",
        "timeline_demo_function.json",
        "timeline_demo_function.pickle",
        "timeline_demo_function.feather",
    ],
)
def test_save_load__types_with_functions(fname, timeline_demo_function):
    file.save(timeline_demo_function, fname)
    actual = file.load(fname)

    mask = actual["function"].notna()

    if bool(actual.loc[mask, "function"].map(lambda x: isinstance(x, str)).all()):
        output = timeline_demo_function.copy(deep=True)
        output.loc[mask, "function"] = "wignertime.ramp_function.tanh"
        # A column of names is typed as one: `object` under pandas 2, `str` under 3.
        output["function"] = output["function"].infer_objects()
    else:
        output = timeline_demo_function

    return frame.assert_equal(actual, output)


def test_save_load__increment_name(timeline_demo):
    file.save(timeline_demo)
    t1 = Path("timeline_demo.parquet").exists()
    file.save(timeline_demo)
    t2 = Path("timeline_demo__002.parquet").exists()
    file.save(timeline_demo)
    t3 = Path("timeline_demo__003.parquet").exists()

    assert t1 and t2 and t3


@pytest.mark.parametrize("suffix", [".parquet", ".csv", ".json", ".pickle", ".feather"])
def test_save_load__nulls_survive_the_round_trip(suffix, timeline_demo_function):
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
    written = file.save(timeline_demo_function, "round_trip" + suffix)
    back = file.load(str(written))

    def kinds(column):
        return {type(v) for v in column if not callable(v) and not isinstance(v, str)}

    assert kinds(back["function"]) == kinds(timeline_demo_function["function"])
    assert not any(v is None for v in back["function"])


@pytest.mark.parametrize("suffix", [".json", ".csv", ".pickle", ".parquet"])
def test_the_state_before_and_after_the_run_survives_a_round_trip(suffix):
    """
    #154: `init` is at -inf and the final state at +inf. JSON has no infinity, and pandas
    wrote both as null, which came back as nan: on neither side of the run.
    """
    if suffix == ".parquet":
        pytest.importorskip("pyarrow")
    timeline = tl.to_timeline(tl.cascade(demo.init, demo.MOT, demo.finish))
    back = file.load(file.save(timeline, "t" + suffix))
    assert {float("-inf"), float("inf")} <= set(timeline["time"])
    # JSON and CSV round the finite times in their last digits, which is not at issue.
    assert list(back["time"]) == pytest.approx(list(timeline["time"]), rel=1e-12)
