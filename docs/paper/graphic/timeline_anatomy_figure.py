"""
Generates `fig:timeline_overview` -- the anatomy of a timeline -- as vector PDF.

The figure it replaces was drawn by hand, with rows that no code had produced and a variable
named in the grammar that D7 retired (`coil_MOTupper__A`). Here the rows are the demo's own:
the first row of `coil__MOT_upper__A`, then its ramps in the molasses and optical-pumping
stages, as `demo/full_experiment.py` writes them, with `value__digits` computed from the demo's
`devices` by the conversion the pipeline uses. A change to the naming, to the demo or to the
conversion is therefore carried into the manuscript by a rerun, not a redraw.

Run from anywhere:

    poetry run python docs/paper/graphic/timeline_anatomy_figure.py

writing `wigner-time--basics.pdf` (for the manuscript, under the name it always had) and
`wigner-time--basics.png` (for looking at) beside this file.

Layout: vertical position is a cursor in inches, running downward from the top, and the
figure's height is whatever the cursor reaches; columns have fixed widths. Every cell's text
is checked against its cell before anything is written, so a longer name cannot overrun.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

from wignertime import conversion, device
from wignertime.demo import full_experiment as demo

# --- palette -----------------------------------------------------------------
# That of `origin_resolution_figure.py`: blue for what every timeline has, orange for what
# is added to it.
INK = "#16232e"
BLUE = "#1f7fd0"
BLUE__DEEP = "#1d5f99"
ORANGE = "#d1762f"
ORANGE__PALE = "#fbe6d4"
ORANGE__BAND = "#fdf3e9"
GREY = "#78858f"
GREY__RULE = "#c9d1d8"
ROW__ODD = "#f5f8fb"

# One tint per context, so that a reader sees a stage as a run of rows.
CONTEXT__COLOURS = {
    "MOT": ("#dceaf7", "#1f7fd0"),
    "molasses": ("#dff0e2", "#3c8d4f"),
    "optical_pumping": ("#ebe3f4", "#7a55a8"),
}

FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

PT = dict(header=8.6, cell=7.8, note=7.6, axis=8.0, dots=11.0)

VARIABLE = "coil__MOT_upper__A"
CONTEXTS__APPENDED = ("molasses", "optical_pumping")

# Columns, in inches: the four every timeline has, the columns elided, the one added.
X__AXIS = 0.18
COLUMNS = [  # (name, x, width)
    ("time", 0.42, 0.80),
    ("variable", 1.22, 1.62),
    ("value", 2.84, 0.72),
    ("context", 3.56, 1.38),
]
X__ELIDED, W__ELIDED = 4.94, 0.62
X__DOTS, X__PLUS = X__ELIDED + 0.22, X__ELIDED + 0.48  # within the elided columns
X__ADDED, W__ADDED = 5.56, 1.14
WIDTH__IN = X__ADDED + W__ADDED + 0.06

ROW__IN = 0.27
HEADER__IN = 0.30


class Cursor:
    """Vertical position, in inches, running downward from the top of the figure."""

    def __init__(self):
        self.y = 0.0

    def take(self, height):
        y = self.y
        self.y += height
        return y


def rows():
    """The demo's rows for `VARIABLE`, with the digits the conversion step gives them."""
    timeline = demo.timeline_demo
    timeline = timeline[timeline["variable"] == VARIABLE]
    timeline = conversion.add(device.add(timeline, demo.devices))

    first = timeline.iloc[:1]
    appended = timeline[timeline["context"].isin(CONTEXTS__APPENDED)]
    if first["context"].iloc[0] != "MOT" or len(appended) != 4:
        raise SystemExit(
            "The demo's {} no longer starts in MOT with two ramps after it; "
            "choose the rows again.".format(VARIABLE)
        )
    return first, appended


def number(x, digits):
    """A number as typeset: a true minus sign, and no `-0`."""
    text = "{:.{}f}".format(x, digits)
    return text.replace("-", "−") if float(text) != 0 else text.lstrip("-")


class Figure:
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        self.ax.axis("off")
        self.cells = []  # (text, x0, x1), checked by `check__fits`

    def text(self, x, y, s, *, cell=None, **kw):
        kw.setdefault("family", MONO)
        kw.setdefault("fontsize", PT["cell"])
        kw.setdefault("color", INK)
        kw.setdefault("va", "center")
        kw.setdefault("ha", "center")
        t = self.ax.text(x, y, s, **kw)
        if cell is not None:
            self.cells.append((t,) + cell)
        return t

    def rect(self, x, y, w, h, **kw):
        kw.setdefault("linewidth", 0)
        self.ax.add_patch(Rectangle((x, y), w, h, **kw))

    def header(self, y, name, x, w, colour):
        self.ax.add_patch(
            FancyBboxPatch(
                (x + 0.02, y + 0.03),
                w - 0.04,
                HEADER__IN - 0.06,
                boxstyle="round,pad=0,rounding_size=0.05",
                facecolor=colour,
                edgecolor="none",
            )
        )
        self.text(
            x + w / 2,
            y + HEADER__IN / 2,
            name,
            fontsize=PT["header"],
            fontweight="bold",
            color="white",
            cell=(x + 0.02, x + w - 0.02),
        )

    def row(self, y, record, *, shade):
        x0, x1 = COLUMNS[0][1], COLUMNS[-1][1] + COLUMNS[-1][2]
        if shade:
            self.rect(x0, y, x1 - x0, ROW__IN, facecolor=ROW__ODD, zorder=0)
        # The added column is tinted throughout, so that it reads as one thing.
        self.rect(X__ADDED, y, W__ADDED, ROW__IN, facecolor=ORANGE__BAND, zorder=0)

        yc = y + ROW__IN / 2
        (_, xt, wt), (_, xv, wv), (_, xn, wn), (_, xc, wc) = COLUMNS
        self.text(xt + wt / 2, yc, number(record["time"], 4), cell=(xt, xt + wt))
        self.text(xv + wv / 2, yc, record["variable"], cell=(xv, xv + wv))
        self.text(xn + wn / 2, yc, number(record["value"], 2), cell=(xn, xn + wn))

        face, edge = CONTEXT__COLOURS[record["context"]]
        self.text(
            xc + wc / 2,
            yc,
            record["context"],
            color=edge,
            cell=(xc + 0.04, xc + wc - 0.04),
            bbox=dict(
                boxstyle="round,pad=0.22,rounding_size=0.35",
                facecolor=face,
                edgecolor=edge,
                linewidth=0.6,
            ),
        )
        self.text(X__DOTS, yc, "⋯", family=FONT, color=GREY__RULE)
        self.text(
            X__ADDED + W__ADDED / 2,
            yc,
            "{:d}".format(int(record["value__digits"])),
            color=ORANGE,
            cell=(X__ADDED, X__ADDED + W__ADDED),
        )

    def rule(self, y, colour=GREY__RULE, linewidth=0.5):
        x0, x1 = COLUMNS[0][1], COLUMNS[-1][1] + COLUMNS[-1][2]
        for a, b in ((x0, x1), (X__ADDED, X__ADDED + W__ADDED)):
            self.ax.plot([a, b], [y, y], color=colour, linewidth=linewidth, zorder=1)

    def block(self, cur, records):
        y__top = cur.y
        for i, (_, record) in enumerate(records.iterrows()):
            y = cur.take(ROW__IN)
            self.row(y, record, shade=i % 2 == 1)
            if i:
                self.rule(y)
        self.rule(y__top, colour=GREY, linewidth=0.7)
        self.rule(cur.y, colour=GREY, linewidth=0.7)
        return y__top, cur.y

    def note(self, x, y, lines, *, ha):
        self.text(
            x,
            y,
            "\n".join(lines),
            family=FONT,
            fontsize=PT["note"],
            ha=ha,
            linespacing=1.35,
            bbox=dict(
                boxstyle="round,pad=0.45,rounding_size=0.25",
                facecolor=ORANGE__PALE,
                edgecolor=ORANGE,
                linewidth=0.8,
            ),
        )


def build():
    first, appended = rows()
    f = Figure()
    cur = Cursor()

    # --- the added column, announced ----------------------------------------------
    f.note(
        X__ADDED + W__ADDED,
        cur.take(0.62) + 0.30,
        ["Later steps add columns –", "here, the digits sent to the hardware"],
        ha="right",
    )

    # --- the header ---------------------------------------------------------------
    y__header = cur.take(HEADER__IN)
    for name, x, w in COLUMNS:
        f.header(y__header, name, x, w, BLUE__DEEP)
    f.text(X__DOTS, y__header + HEADER__IN / 2, "⋯", family=FONT, color=GREY)
    f.header(y__header, "value__digits", X__ADDED, W__ADDED, ORANGE)
    f.text(
        X__PLUS,
        y__header + HEADER__IN / 2,
        "+",
        family=FONT,
        fontsize=PT["dots"],
        fontweight="bold",
        color=ORANGE,
    )

    # --- the first row ------------------------------------------------------------
    cur.take(0.04)
    f.block(cur, first)

    # --- the rows elided, and the rows added ----------------------------------------
    y__gap = cur.take(0.78)
    for x in (COLUMNS[0][1] + COLUMNS[0][2] / 2, X__ADDED + W__ADDED / 2):
        f.text(x, y__gap + 0.39, "⋮", family=FONT, color=GREY, fontsize=PT["dots"])
    f.note(
        COLUMNS[1][1] + 0.10,
        y__gap + 0.39,
        ["Composing an experiment adds rows –", "here, the coil ramps of two stages"],
        ha="left",
    )
    f.text(
        COLUMNS[0][1] - 0.035,
        y__gap + 0.62,
        "+",
        family=FONT,
        fontsize=PT["dots"],
        fontweight="bold",
        color=ORANGE,
    )
    y0, y1 = f.block(cur, appended)
    f.rect(COLUMNS[0][1] - 0.05, y0, 0.03, y1 - y0, facecolor=ORANGE, zorder=2)
    cur.take(0.06)

    # --- time runs down -------------------------------------------------------------
    f.ax.add_patch(
        FancyArrowPatch(
            (X__AXIS, y__header + 0.05),
            (X__AXIS, cur.y),
            arrowstyle="-|>,head_length=4,head_width=2.2",
            color=GREY,
            linewidth=0.9,
            shrinkA=0,
            shrinkB=0,
        )
    )
    f.text(
        X__AXIS - 0.07,
        (y__header + cur.y) / 2,
        "time",
        family=FONT,
        fontsize=PT["axis"],
        style="italic",
        color=GREY,
        rotation=90,
    )

    f.ax.set_xlim(0, WIDTH__IN)
    f.ax.set_ylim(cur.y, 0)
    f.fig.subplots_adjust(0, 0, 1, 1)
    f.fig.set_size_inches(WIDTH__IN, cur.y)
    return f


def check__fits(f):
    """
    Reports any text running outside its cell, or outside the figure.

    The rows come from the demo, so a renamed variable or context reaches this figure without
    anyone looking at it; this is where it is looked at.
    """
    f.fig.canvas.draw()
    renderer = f.fig.canvas.get_renderer()
    inverse = f.ax.transData.inverted()
    offenders = []
    for t, x0, x1 in f.cells:
        (a, _), (b, _) = inverse.transform(t.get_window_extent(renderer).get_points())
        if a < x0 or b > x1:
            offenders.append(
                "  {!r} needs {:.2f} in, has {:.2f}".format(
                    t.get_text(), b - a, x1 - x0
                )
            )
    height = f.ax.get_ylim()[0]
    for t in f.ax.texts:
        box = t.get_bbox_patch() or t
        (a, top), (b, bottom) = inverse.transform(
            box.get_window_extent(renderer).get_points()
        )
        if a < 0 or b > WIDTH__IN or min(top, bottom) < 0 or max(top, bottom) > height:
            offenders.append("  {!r} leaves the figure".format(t.get_text()[:40]))
    return offenders


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    f = build()

    offenders = check__fits(f)
    if offenders:
        raise SystemExit(
            "Text runs outside its place; shorten it or widen the column:\n"
            + "\n".join(offenders)
        )

    for suffix, kw in ((".pdf", {}), (".png", dict(dpi=300))):
        f.fig.savefig(
            here / ("wigner-time--basics" + suffix),
            bbox_inches="tight",
            pad_inches=0.02,
            **kw,
        )
    print("wrote wigner-time--basics.pdf and .png to {}".format(here))
