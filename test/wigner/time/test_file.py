import pytest
from pathlib import Path

from wigner.time import file
from wigner.time import timeline as tl
from wigner.time.internal import dataframe as frame


from wigner.time.demo import full_experiment as demo


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
        output.loc[mask, "function"] = "wigner.time.ramp_function.tanh"
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

    assert t1 and t2
