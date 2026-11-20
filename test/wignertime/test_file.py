import functools
import warnings
from pathlib import Path

import pandas as pd
import pytest

from wignertime import file, ramp_function
from wignertime import timeline as tl
from wignertime.demo import full_experiment as demo
from wignertime.internal import dataframe as frame


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
    """
    A ramp comes back with its function, in every format (D27, #191). A text format used to
    return the function's name where the function had been, so the timeline could be read
    and not expanded, and this test expected the name.
    """
    file.save(timeline_demo_function, fname)
    actual = file.load(fname)

    return frame.assert_equal(actual, timeline_demo_function)


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


def test_a_name_without_a_suffix_is_a_file(timeline_demo):
    """D26. It made a directory, against the docstring's rule for a path without a suffix."""
    written = file.save(timeline_demo, "run42")
    assert written == Path("run42.parquet") and written.is_file()


def test_a_name_ending_in_a_separator_is_a_directory(timeline_demo):
    written = file.save(timeline_demo, "runs/")
    assert written.parent == Path("runs") and written.suffix == ".parquet"


# --- a ramp's function is saved as data (D27, #191) -----------------------------------

FORMATS__TEXT = [".parquet", ".csv", ".json", ".feather"]
"""The formats that cannot hold a function, and so hold its name and what it binds."""


def ramp_of_this_module(origin, terminus, time_resolution=None, option=None):
    """A ramp function that is not Wigner Time's, so `load` cannot know it by itself."""
    return ramp_function.linear(origin, terminus, time_resolution)


def _ramped(function):
    return tl.to_timeline(
        tl.stack(
            tl.update(coil__test__A=0.0, time=0.0, context="start"),
            tl.ramp(coil__test__A=1.0, duration=1e-2, function=function),
        )
    )


def _functions(timeline):
    return [f for f in timeline["function"] if callable(f) or isinstance(f, str)]


@pytest.mark.parametrize("suffix", FORMATS__TEXT)
def test_a_function_that_binds_keywords_comes_back_bound(suffix):
    """
    `functools.partial(tanh, sharpness=..., time_resolution=...)` is how a ramp states its
    shape and its own resolution (#65). Its `repr`, memory address included, was what a
    text format kept of it.
    """
    bound = functools.partial(ramp_function.tanh, sharpness=1.5, time_resolution=1e-3)
    timeline = _ramped(bound)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        back = file.load(file.save(timeline, "bound" + suffix))

    functions = _functions(back)
    assert len(functions) == 2
    for f in functions:
        assert isinstance(f, functools.partial)
        assert f.func is ramp_function.tanh
        assert f.keywords == {"sharpness": 1.5, "time_resolution": 1e-3}
    assert file.COLUMN__KEYWORDS not in back.columns
    # ... and so the reloaded timeline is the same experiment.
    frame.assert_equal(tl.expand(back), tl.expand(timeline))


def test_the_keywords_have_a_column_of_their_own_in_the_file():
    """Only when some ramp binds any: a file without one is as it always was."""
    plain = file.save(_ramped(ramp_function.tanh), "plain.csv")
    bound = file.save(
        _ramped(functools.partial(ramp_function.tanh, sharpness=2)), "bound.csv"
    )

    assert file.COLUMN__KEYWORDS not in pd.read_csv(plain).columns
    written = pd.read_csv(bound)
    assert (
        written["function"].dropna().tolist() == ["wignertime.ramp_function.tanh"] * 2
    )
    assert written[file.COLUMN__KEYWORDS].dropna().tolist() == ['{"sharpness": 2}'] * 2


@pytest.mark.parametrize("suffix", FORMATS__TEXT)
def test_a_lambda_is_kept_as_text_and_both_ends_say_so(suffix):
    """
    A lambda has no name a later session could find it by. It is still written, as text,
    so that the file can be read, but `save` names the ramp it cannot keep, `load` says
    what it could not put back, and expanding raises as it did. Silent at the point of
    saving was the defect.
    """
    timeline = _ramped(
        lambda origin, terminus, time_resolution: ramp_function.tanh(
            origin, terminus, time_resolution, 1.5
        )
    )

    with pytest.warns(UserWarning, match=r"coil__test__A \(start\)"):
        written = file.save(timeline, "lambda" + suffix)
    with pytest.warns(UserWarning, match="not known here"):
        back = file.load(written)

    assert all(isinstance(f, str) and "<lambda>" in f for f in _functions(back))
    with pytest.raises(TypeError):
        tl.expand(back, time_resolution=1e-3)


@pytest.mark.parametrize(
    "function",
    [
        functools.partial(ramp_of_this_module, option=(1, 2)),  # a tuple returns a list
        functools.partial(ramp_of_this_module, option=float("inf")),  # not JSON
        functools.partial(ramp_of_this_module, [0.0, 0.0]),  # a positional argument
    ],
    ids=["tuple", "infinity", "positional"],
)
def test_what_a_file_could_not_give_back_as_it_was_is_not_saved_as_data(function):
    timeline = _ramped(ramp_function.tanh)
    # Set as a list: `assign` would call the function.
    timeline["function"] = [
        function if callable(f) else f for f in timeline["function"]
    ]

    with pytest.warns(UserWarning, match="as text only"):
        file.save(timeline, "t.csv")


def test_a_function_of_ones_own_is_handed_to_load():
    """
    `load` puts back Wigner Time's ramp functions by itself and imports nothing a file
    names: which code runs is for the caller to say. Any other function is handed over.
    """
    timeline = _ramped(functools.partial(ramp_of_this_module, option=3))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        written = file.save(timeline, "own.parquet")

    with pytest.warns(UserWarning, match="ramp_of_this_module"):
        unknown = file.load(written)
    assert all(isinstance(f, str) for f in _functions(unknown))

    name = "{}.ramp_of_this_module".format(ramp_of_this_module.__module__)
    for functions in ([ramp_of_this_module], {name: ramp_of_this_module}):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            back = file.load(written, functions=functions)
        for f in _functions(back):
            assert f.func is ramp_of_this_module and f.keywords == {"option": 3}
        frame.assert_equal(
            tl.expand(back, time_resolution=1e-3),
            tl.expand(timeline, time_resolution=1e-3),
        )


def test_a_function_without_a_name_cannot_be_handed_over_in_a_list():
    file.save(_ramped(ramp_function.tanh), "t.csv")
    with pytest.raises(ValueError, match="no name a file could refer to it by"):
        file.load("t.csv", functions=[lambda origin, terminus: None])


@pytest.mark.parametrize("suffix", FORMATS__TEXT + [".pickle"])
def test_the_demonstration_is_archived_without_loss(suffix):
    """
    The paper says a timeline can be archived beside the data it produced. Its
    demonstration, with ramps of three kinds (the default, one of a given sharpness, one
    of a resolution of its own), comes back from every format as the same experiment. It
    could not be pickled either, while `pull_coils` ramped with a lambda.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        back = file.load(file.save(demo.timeline_demo, "demonstration" + suffix))

    assert all(callable(f) for f in _functions(back))
    frame.assert_equal(
        tl.expand(back, time_resolution=1e-4),
        tl.expand(demo.timeline_demo, time_resolution=1e-4),
    )
