"""
Generates `fig:hardware_overview` -- from stages to the apparatus -- as vector PDF.

The figure it replaces was a hand-drawn diagram whose boxes ("Python-only", "Python
bridge", "commands") named nothing in the text. This one is drawn in the paper's own terms:
the three layers of `sec:definitions`, the `connection` and `device` tables, the conversion
step, `upload` and `run` through the ADwin API, and on the controller the sequencer of
`sec:adwin` and the manual console of `sec:adwin_operation`.

Its visual grammar: the PC and the controller are each a region; a coloured box is
something people write, coloured by how often it changes (blue with the experiment, orange
with the apparatus, grey once); a small table is data; an arrow carries the name of the
step it does. The ADwin API is drawn without saying whether it is the manufacturer's or
Wigner Time's wrapper of it, a distinction the reader does not need.

Run from anywhere:

    poetry run python docs/paper/graphic/hardware_overview_figure.py

writing `hardware-overview.pdf` (for the manuscript) and `hardware-overview.png` (for
looking at) beside this file.

Layout: every position is in inches, written out below; text is checked against the box
that holds it before anything is written.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# --- palette -----------------------------------------------------------------
# That of `timeline_anatomy_figure.py`: blue for the physics, orange for the hardware.
INK = "#16232e"
BLUE = "#1f7fd0"
BLUE__DEEP = "#1d5f99"
BLUE__PALE = "#dceaf7"
ORANGE = "#d1762f"
ORANGE__PALE = "#fbe6d4"
GREY = "#78858f"
GREY__PALE = "#eef1f4"
GREY__RULE = "#c9d1d8"
REGION = "#f6f8fa"

CONTEXTS = (
    "#1f7fd0",
    "#3c8d4f",
    "#7a55a8",
)  # the context tints of fig:timeline_overview

FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

PT = dict(title=8.4, body=7.4, small=6.8, region=8.4)

WIDTH__IN = 7.0
HEIGHT__IN = 3.86

# The main row: stages → timeline → arrays → memory, all centred on one line.
Y__ROW = 1.62
# The three layers share a bottom edge, the two tables' (`Figure.table` at 1.33, 0.66 high),
# and so their labels share a line.
Y__TOP, Y__BASE = 0.98, 1.99
Y__LAYER = Y__BASE + 0.15

# The ADwin API, at the right-hand edge of the PC: `upload` and `run` both pass through it.
X__API, W__API = 4.12, 0.56


class Figure:
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        self.ax.axis("off")
        self.held = []  # (text, x0, x1), checked by `check__fits`

    def text(self, x, y, s, *, within=None, **kw):
        kw.setdefault("family", FONT)
        kw.setdefault("fontsize", PT["body"])
        kw.setdefault("color", INK)
        kw.setdefault("va", "center")
        kw.setdefault("ha", "center")
        t = self.ax.text(x, y, s, **kw)
        if within is not None:
            self.held.append((t,) + within)
        return t

    def box(self, x, y, w, h, *, face, edge, dashed=False, linewidth=0.9, z=1):
        self.ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0,rounding_size=0.06",
                facecolor=face,
                edgecolor=edge,
                linewidth=linewidth,
                linestyle=(0, (3, 2)) if dashed else "solid",
                zorder=z,
            )
        )

    def arrow(self, a, b, *, colour=GREY, linewidth=1.0, dashed=False):
        self.ax.add_patch(
            FancyArrowPatch(
                a,
                b,
                arrowstyle="-|>,head_length=4.5,head_width=2.4",
                color=colour,
                linewidth=linewidth,
                linestyle=(0, (3, 2)) if dashed else "solid",
                shrinkA=0,
                shrinkB=0,
                zorder=3,
            )
        )

    def table(self, x, y, w, h, *, header, rows, marks=None):
        """A small table: a coloured header and a few ruled rows, no text."""
        hh = 0.13
        self.ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                hh,
                boxstyle="round,pad=0,rounding_size=0.03",
                facecolor=header,
                edgecolor="none",
                zorder=2,
            )
        )
        self.rect(x, y + hh, w, h - hh, facecolor="white", edgecolor=GREY, lw=0.6)
        step = (h - hh) / rows
        for i in range(1, rows):
            yy = y + hh + i * step
            self.ax.plot([x, x + w], [yy, yy], color=GREY__RULE, lw=0.5, zorder=3)
        for i in range(rows):
            yy = y + hh + (i + 0.5) * step
            for j, frac in enumerate((0.08, 0.32, 0.56)):
                self.ax.plot(
                    [x + w * frac, x + w * (frac + 0.16)],
                    [yy, yy],
                    color=GREY__RULE,
                    lw=1.6,
                    solid_capstyle="round",
                    zorder=3,
                )
            colour = marks[i] if marks else GREY__RULE
            self.ax.plot(
                [x + w * 0.78, x + w * 0.92],
                [yy, yy],
                color=colour,
                lw=1.6,
                solid_capstyle="round",
                zorder=3,
            )

    def rect(self, x, y, w, h, *, facecolor, edgecolor="none", lw=0):
        self.ax.add_patch(
            Rectangle(
                (x, y), w, h, facecolor=facecolor, edgecolor=edgecolor, lw=lw, zorder=2
            )
        )

    def layer(self, x, y, name, **kw):
        self.text(x, y, name, fontsize=PT["small"], color=GREY, style="italic", **kw)

    def rate(self, x, y, s, colour, **kw):
        return self.text(
            x, y, s, fontsize=PT["small"], color=colour, style="italic", **kw
        )


def build():
    f = Figure()

    # --- the two sides ----------------------------------------------------------------
    X__PC, W__PC = 0.02, 4.76
    X__C, W__C = 4.86, 2.12
    Y__BOTTOM = 3.37
    f.box(X__PC, 0.02, W__PC, Y__BOTTOM - 0.02, face=REGION, edge=GREY, z=0)
    f.text(
        X__PC + 0.12,
        Y__BOTTOM - 0.20,
        "Python, on the PC",
        fontsize=PT["region"],
        fontweight="bold",
        ha="left",
    )
    f.box(X__C, 0.95, W__C, Y__BOTTOM - 0.95, face=REGION, edge=GREY, z=0)
    f.text(
        X__C + W__C / 2,
        1.13,
        "ADwin controller",
        fontsize=PT["region"],
        fontweight="bold",
        within=(X__C, X__C + W__C),
    )

    # --- operation layer: stages --------------------------------------------------------
    x, w = 0.16, 1.00
    f.box(x, Y__TOP, w, Y__BASE - Y__TOP, face=BLUE__PALE, edge=BLUE)
    f.text(
        x + w / 2,
        Y__TOP + 0.14,
        "stages",
        fontsize=PT["title"],
        fontweight="bold",
        color=BLUE__DEEP,
    )
    for i, name in enumerate(("MOT", "molasses", "optical_pumping")):
        f.text(
            x + w / 2,
            Y__TOP + 0.34 + 0.165 * i,
            name,
            family=MONO,
            fontsize=PT["small"],
            within=(x + 0.04, x + w - 0.04),
        )
    f.text(x + w / 2, Y__BASE - 0.17, "⋮", color=GREY, fontsize=PT["small"])
    f.layer(x + w / 2, Y__LAYER, "operation layer")
    # Not "changes with every experiment": from shot to shot only the parameters do.
    f.rate(
        x + w / 2,
        Y__LAYER + 0.40,
        "parameters change\nfrom shot to shot,\nstages between\nexperiments",
        BLUE,
        linespacing=1.25,
        within=(X__PC + 0.04, 1.76),
    )

    # --- to_timeline --------------------------------------------------------------------
    f.arrow((1.16, Y__ROW), (1.84, Y__ROW))
    f.text(
        1.50,
        Y__ROW - 0.12,
        "to_timeline",
        family=MONO,
        fontsize=PT["small"],
        within=(1.16, 1.84),
    )

    # --- device layer: the timeline -----------------------------------------------------
    x, w = 1.84, 0.76
    f.text(x + w / 2, 1.17, "timeline", fontsize=PT["title"], fontweight="bold")
    f.table(x, 1.33, w, 0.66, header=BLUE__DEEP, rows=4, marks=CONTEXTS + CONTEXTS[2:])
    f.layer(x + w / 2, Y__LAYER, "device layer")
    f.rate(
        x + w / 2,
        Y__LAYER + 0.26,
        "plotted, compared,\narchived",
        GREY,
        linespacing=1.25,
    )

    # --- the tables, and the conversion step --------------------------------------------
    X__CONV = 2.90  # the middle of the conversion arrow
    for name, rate, x in (
        ("connection", "when rewired", 1.85),
        ("device", "when recalibrated", 2.95),
    ):
        w = 1.00
        f.box(x, 0.28, w, 0.60, face=ORANGE__PALE, edge=ORANGE)
        f.text(
            x + w / 2,
            0.42,
            name,
            family=MONO,
            fontsize=PT["body"],
            fontweight="bold",
            within=(x + 0.04, x + w - 0.04),
        )
        f.rate(
            x + w / 2,
            0.66,
            "changes\n" + rate,
            ORANGE,
            linespacing=1.2,
            within=(x + 0.03, x + w - 0.03),
        )
    f.arrow((2.35, 0.88), (X__CONV - 0.06, Y__ROW - 0.05), colour=ORANGE, linewidth=0.8)
    f.arrow((3.45, 0.88), (X__CONV + 0.06, Y__ROW - 0.05), colour=ORANGE, linewidth=0.8)
    f.arrow((2.60, Y__ROW), (3.20, Y__ROW))
    f.text(X__CONV, Y__ROW + 0.13, "conversion", fontsize=PT["small"])

    # --- connection layer: the arrays ---------------------------------------------------
    x, w = 3.20, 0.60
    f.text(x + w / 2, 1.17, "arrays", fontsize=PT["title"], fontweight="bold")
    f.table(x, 1.33, w, 0.66, header=ORANGE, rows=4)
    f.layer(x + w / 2, Y__LAYER, "connection layer", within=(2.96, X__API - 0.12))

    # --- the ADwin API ------------------------------------------------------------------
    # Whose it is -- the manufacturer's, or Wigner Time's wrapper of it -- is deliberately
    # not drawn: what the reader needs is that both calls go through it.
    Y__SEQ = 2.02
    Y__RUN = Y__SEQ + 0.24
    f.box(X__API, 1.04, W__API, 1.48, face="white", edge=INK)
    f.text(
        X__API + W__API / 2,
        1.24,
        "ADwin\nAPI",
        fontsize=PT["body"],
        fontweight="bold",
        linespacing=1.1,
        within=(X__API + 0.03, X__API + W__API - 0.03),
    )
    for y, name in ((Y__ROW, "upload"), (Y__RUN, "run")):
        f.text(
            X__API + W__API / 2,
            y,
            name,
            family=MONO,
            fontsize=PT["small"],
            within=(X__API + 0.03, X__API + W__API - 0.03),
        )
    f.arrow((3.80, Y__ROW), (X__API, Y__ROW))

    # --- the controller ---------------------------------------------------------------
    X__IN, W__IN = X__C + 0.12, W__C - 0.24
    f.arrow((X__API + W__API, Y__ROW), (X__IN, Y__ROW), colour=INK)
    f.arrow((X__API + W__API, Y__RUN), (X__IN, Y__RUN), colour=INK)

    f.box(X__IN, Y__ROW - 0.19, W__IN, 0.38, face=ORANGE__PALE, edge=ORANGE)
    f.text(
        X__IN + W__IN / 2,
        Y__ROW,
        "arrays, in memory",
        within=(X__IN + 0.04, X__IN + W__IN - 0.04),
    )

    w__seq = 1.12
    f.box(X__IN, Y__SEQ, w__seq, 0.62, face=GREY__PALE, edge=INK)
    f.text(
        X__IN + w__seq / 2,
        Y__SEQ + 0.15,
        "sequencer",
        fontsize=PT["title"],
        fontweight="bold",
    )
    f.text(
        X__IN + w__seq / 2,
        Y__SEQ + 0.33,
        "a few lines of ADbasic",
        fontsize=PT["small"],
        within=(X__IN + 0.03, X__IN + w__seq - 0.03),
    )
    f.rate(X__IN + w__seq / 2, Y__SEQ + 0.49, "written once", GREY)
    f.arrow(
        (X__IN + w__seq / 2, Y__ROW + 0.19), (X__IN + w__seq / 2, Y__SEQ), colour=INK
    )

    x__con = X__IN + w__seq + 0.08
    w__con = X__IN + W__IN - x__con
    f.box(x__con, Y__SEQ, w__con, 0.62, face="white", edge=GREY, dashed=True)
    f.text(
        x__con + w__con / 2,
        Y__SEQ + 0.22,
        "manual\nconsole",
        fontsize=PT["body"],
        linespacing=1.15,
        within=(x__con + 0.03, x__con + w__con - 0.03),
    )
    f.rate(
        x__con + w__con / 2,
        Y__SEQ + 0.49,
        "set by hand",
        GREY,
        within=(x__con + 0.03, x__con + w__con - 0.03),
    )

    Y__OUT = 2.86
    f.box(X__IN, Y__OUT, W__IN, 0.34, face="white", edge=INK)
    f.text(
        X__IN + W__IN / 2,
        Y__OUT + 0.17,
        "outputs – one program at a time",
        fontsize=PT["small"],
        within=(X__IN + 0.03, X__IN + W__IN - 0.03),
    )
    f.arrow(
        (X__IN + w__seq / 2, Y__SEQ + 0.62), (X__IN + w__seq / 2, Y__OUT), colour=INK
    )
    f.arrow(
        (x__con + w__con / 2, Y__SEQ + 0.62),
        (x__con + w__con / 2, Y__OUT),
        colour=GREY,
    )

    # --- the apparatus ----------------------------------------------------------------
    f.arrow((X__C + W__C / 2, Y__OUT + 0.34), (X__C + W__C / 2, 3.56), colour=INK)
    f.text(
        X__C + W__C / 2,
        3.70,
        "apparatus: coils, shutters, AOMs …",
        fontsize=PT["small"],
        within=(X__C - 0.3, WIDTH__IN),
    )

    f.ax.set_xlim(0, WIDTH__IN)
    f.ax.set_ylim(HEIGHT__IN, 0)
    f.fig.subplots_adjust(0, 0, 1, 1)
    f.fig.set_size_inches(WIDTH__IN, HEIGHT__IN)
    return f


def check__fits(f):
    """Reports any text running outside the box that holds it, or outside the figure."""
    f.fig.canvas.draw()
    renderer = f.fig.canvas.get_renderer()
    inverse = f.ax.transData.inverted()
    offenders = []
    for t, x0, x1 in f.held:
        (a, _), (b, _) = inverse.transform(t.get_window_extent(renderer).get_points())
        if a < x0 or b > x1:
            offenders.append(
                "  {!r} needs {:.2f} in, has {:.2f}".format(
                    t.get_text(), b - a, x1 - x0
                )
            )
    for t in f.ax.texts:
        (a, top), (b, bottom) = inverse.transform(
            t.get_window_extent(renderer).get_points()
        )
        if (
            a < 0
            or b > WIDTH__IN
            or min(top, bottom) < 0
            or max(top, bottom) > HEIGHT__IN
        ):
            offenders.append("  {!r} leaves the figure".format(t.get_text()[:40]))
    return offenders


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    f = build()

    offenders = check__fits(f)
    if offenders:
        raise SystemExit(
            "Text runs outside its place; shorten it or widen its box:\n"
            + "\n".join(offenders)
        )

    for suffix, kw in ((".pdf", {}), (".png", dict(dpi=300))):
        f.fig.savefig(
            here / ("hardware-overview" + suffix),
            bbox_inches="tight",
            pad_inches=0.02,
            **kw,
        )
    print("wrote hardware-overview.pdf and .png to {}".format(here))
