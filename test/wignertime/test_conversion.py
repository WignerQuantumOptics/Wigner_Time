import pytest
from munch import Munch
import numpy as np

from wignertime.internal import dataframe as wt_frame
from wignertime import timeline as tl
from wignertime import device
from wignertime import conversion as conv


@pytest.fixture
def df_simple():
    return tl.to_timeline(
        tl.update(
            AOM__imaging=[0.0, 0.0, "init"],
            AOM__imaging__V=[0.0, 2.0, "init"],
            AOM__repump=[0.0, 1.0, "init"],
            AOM__science__trans=[0.0, 1.0, "MOT"],
        )
    )


@pytest.mark.parametrize(
    "gain",
    [1, 2, 4, 8],
)
def test_to_digits(gain):
    assert conv.to_digits(0, [-10, 10], gain=gain) == 2**15


@pytest.mark.parametrize(
    "input",
    list(zip([10, 5, 2.5, 1.25], [1, 2, 4, 8])),
)
def test_to_digits002(input):
    assert conv.to_digits(input[0], [-10, 10], gain=input[1]) == 2**16 - 1


@pytest.mark.parametrize("input", [4.0, np.array([4.0])])
def test_to_digits003(input):
    assert conv.to_digits(input) == 45874


def test_add_linear_conversion(df_simple):
    df_devs = device.add(
        df_simple,
        device.new(
            "AOM__imaging__V",
            1.0,
            -3,
            3,
        ),
    )

    df_added = conv._add_linear(df_devs)

    return wt_frame.assert_equal(
        df_added,
        wt_frame.cast(
            wt_frame.new(
                {
                    "time": [0.0, 0.0, 0.0, 0.0],
                    "variable": [
                        "AOM__imaging",
                        "AOM__imaging__V",
                        "AOM__repump",
                        "AOM__science__trans",
                    ],
                    "value": [0.0, 2.0, 1.0, 1.0],
                    "context": ["init", "init", "init", "MOT"],
                    "to_V": [None, 1.0, None, None],
                    "value__min": [None, -3, None, None],
                    "value__max": [None, 3, None, None],
                    "value__digits": [None, 39321, None, None],
                }
            ),
            {
                "time": float,
                "variable": str,
                "value": float,
                "context": str,
                "to_V": float,
                "value__min": float,
                "value__max": float,
                "value__digits": float,
            },
        ),
    )


def func(x):
    return x + 10


@pytest.fixture
def df_devs():
    return device.add(
        tl.to_timeline(
            tl.update(
                AOM__imaging=[0.0, 0.0, "init"],
                AOM__imaging__transparency=[0.0, 0.5, "init"],
                coil__MOT__A=[0.0, 1.0, "init"],
                AOM__science__trans=[0.0, 1.0, "MOT"],
            )
        ),
        device.new(
            [
                "AOM__imaging__transparency",
                func,
                0.0,
                1.0,
            ],
            ["coil__MOT__A", 0.333, -5.0, 5.0],
        ),
    )


def test_add_function(df_devs):
    wt_frame.assert_equal(
        wt_frame.select(
            conv._add_function(df_devs), ["value", "to_V", "value__digits"]
        ),
        wt_frame.new(
            [
                [
                    0.0,
                    np.nan,
                    np.nan,
                ],
                [0.5, func, 67173.0],
                [1.0, 0.333, np.nan],
                [1.0, np.nan, np.nan],
            ],
            columns=["value", "to_V", "value__digits"],
        ),
    )


def test_add(df_devs):
    calc = wt_frame.select(conv.add(df_devs), ["value", "to_V", "value__digits"])
    guess = wt_frame.new(
        [
            [
                0.0,
                np.nan,
                np.nan,
            ],
            [0.5, func, 67173.0],
            [1.0, 0.333, 33859.0],
            [1.0, np.nan, np.nan],
        ],
        columns=["value", "to_V", "value__digits"],
    )
    # print(guess)

    return wt_frame.assert_equal(wt_frame.cast(calc, {"value__digits": float}), guess)


def test_addRealistic(df_simple):
    """
    A realistic use of conversion function from file.
    """
    func__AOM = conv.function_from_file(
        "resources/calibration/aom_calibration.dat",
        names=["voltage", "transparency"],
        sep=r"\s+",
    )
    df = device.add(df_simple, device.new("AOM__science__trans", func__AOM, 0.0, 1.0))

    actual = wt_frame.select(conv.add(df), ["value", "to_V", "value__digits"])
    expected = wt_frame.new(
        [
            [0.0, np.nan, np.nan],
            [2.0, np.nan, np.nan],
            [1.0, np.nan, np.nan],
            [1.0, func__AOM, 49143],
        ],
        columns=["value", "to_V", "value__digits"],
    )

    return wt_frame.assert_equal(actual, expected)


_CALIBRATION = "resources/calibration/aom_calibration.dat"


def test_function_from_file_inverts_when_the_columns_are_swapped():
    """
    `indices__column=[1, 0]` is how the docstring says to invert a calibration. After
    averaging the duplicated `x` values, the grouped column had moved to the front, and
    both columns were then taken by position -- so `[1, 0]` read the same column twice and
    returned the identity function, silently.
    """
    kw = dict(names=["voltage", "transparency"], sep=r"\s+")
    forward = conv.function_from_file(_CALIBRATION, **kw)
    inverse = conv.function_from_file(_CALIBRATION, indices__column=[1, 0], **kw)
    assert abs(inverse(0.5) - 0.5) > 1e-3  # not the identity
    assert forward(inverse(0.5)) == pytest.approx(0.5, abs=5e-3)


@pytest.mark.parametrize(
    "kw", [dict(sep=r"\s+"), dict(names=["voltage", "transparency"], sep=r"\s+")]
)
def test_function_from_file_reads_the_same_without_pandas(kw, monkeypatch):
    """
    Without pandas the file is read by `conversion` itself, keeping `read_csv`'s rule that
    the first line is a header unless `names` is given. The two agree to rounding: pandas'
    float parser is not exactly Python's.
    """
    import importlib.util

    grid = np.linspace(0.0, 0.3, 301)
    with_pandas = None
    if importlib.util.find_spec("pandas") is not None:
        with_pandas = conv.function_from_file(_CALIBRATION, **kw)(grid)

    find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name, *a: None if name == "pandas" else find_spec(name, *a),
    )
    without = conv.function_from_file(_CALIBRATION, **kw)(grid)
    if with_pandas is not None:
        assert np.max(np.abs(without - with_pandas)) < 1e-12
    with pytest.raises(TypeError, match="reads `sep`, `names` and `header` only"):
        conv.function_from_file(_CALIBRATION, skiprows=1, **kw)
