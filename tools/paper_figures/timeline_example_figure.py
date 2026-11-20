"""
Generates `fig:timeline__example` -- the demonstration's timeline as `display.quantities` draws
it -- as vector PDF.

The figure it replaces was a screenshot of an interactive window, from a display that drew each
ramp as a hold and a jump at its end (D24, #173). Here the timeline is the one the manuscript's
own listing assembles: the listing of `sec:demonstration` is read out of `main.tex`, which sits
beside the `graphic/` directory given, and run up to the point where it would link to a machine.
The listing differs from `demo/full_experiment.py` in content (`CLAUDE.md`): in this window, its
repump shutter closes 2.3 ms earlier. So the figure shows what the printed code produces, and a
change to the listing or to the display is carried into the manuscript by a rerun.

Run from anywhere, naming the directory that holds the manuscript's figures, the `graphic/` of
its Overleaf project:

    poetry run python tools/paper_figures/timeline_example_figure.py ../Wigner_Time_Overleaf/graphic

writing `timeline__example.pdf` there, for the manuscript, and `timeline__example.png` (for
looking at) and `timeline__example.svg` (for editing, text kept as text) beside this file, where
a rerun shows as a diff.

The window is the one the screenshot showed: from the end of the MOT to just after the magnetic
trap's anchor. The lockbox's return, which lasts 10 ms from the start of the trap, runs out of it. Two channels are left out, `dispenser__Rb__A` and `AOM__science__trans`: both hold
one value through the whole run, and would add a panel and widen a scale without showing anything
("zoomed and cropped for clarity", says the caption).
"""

import contextlib
import io
import os
import pathlib
import re
import runpy
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
# The SVG keeps its text as text, so that it can be edited; its fonts are then the viewer's.
matplotlib.rcParams["svg.fonttype"] = "none"
# Its clip-path ids are otherwise random, and a rerun that changed nothing would rewrite them.
matplotlib.rcParams["svg.hashsalt"] = "wigner-time"

from wignertime.adwin import display

NAME = "timeline__example"
WINDOW = (15.0995, 15.1095)
LEFT_OUT = ("dispenser__Rb__A", "AOM__science__trans")

ROOT = pathlib.Path(__file__).resolve().parents[2]


def listing(manuscript):
    """
    The code of the listing in `sec:demonstration`, up to the banner of the part that links to a
    machine, which is not run here.
    """
    tex = (manuscript.parent / "main.tex").read_text(encoding="utf-8")
    section = tex.index(r"\label{sec:demonstration}")
    match = re.compile(
        r"\\begin\{minted\}[^\n]*\{python\}\n(.*?)\\end\{minted\}", re.S
    ).search(tex, section)
    if match is None:
        raise SystemExit(
            "No Python listing after \\label{sec:demonstration} in main.tex."
        )
    code = match.group(1)
    banner = re.search(r"\n#+\n#\s+Running the experiment\n", code)
    if banner is None:
        raise SystemExit(
            "The listing of sec:demonstration has no 'Running the experiment' banner, which"
            " marks where it links to a machine; say where to stop."
        )
    return code[: banner.start() + 1]


def timeline(manuscript):
    """Runs the listing, from the repository's root, where its calibration file is found."""
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "demonstration.py"
        path.write_text(listing(manuscript), encoding="utf-8")
        here = os.getcwd()
        os.chdir(ROOT)
        try:
            return runpy.run_path(str(path))["timeline_demo"]
        finally:
            os.chdir(here)


def build(manuscript):
    timeline_demo = timeline(manuscript)
    variables = [v for v in timeline_demo["variable"].unique() if v not in LEFT_OUT]
    # The list of the ramps drawn, which `quantities` prints, is for an interactive session.
    with contextlib.redirect_stdout(io.StringIO()):
        fig, _ = display.quantities(
            timeline_demo, variables=variables, do_show=False, range__x=WINDOW
        )
    return fig


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python {} <directory of the manuscript's figures>".format(
                sys.argv[0]
            )
        )
    manuscript = pathlib.Path(sys.argv[1]).resolve()
    here = pathlib.Path(__file__).resolve().parent
    fig = build(manuscript)
    for suffix, kw in (
        # Without its creation date, a rerun that changed nothing rewrites the same bytes.
        (".pdf", dict(metadata={"CreationDate": None})),
        (".png", dict(dpi=200)),
        (".svg", dict(metadata={"Date": None})),
    ):
        fig.savefig(
            (manuscript if suffix == ".pdf" else here) / (NAME + suffix),
            bbox_inches="tight",
            pad_inches=0.02,
            **kw,
        )
    print(
        "wrote {}.pdf to {}, and its .png and .svg to {}".format(NAME, manuscript, here)
    )
