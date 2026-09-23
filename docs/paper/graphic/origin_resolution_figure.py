"""
Generates `fig:origin` -- the resolution of an `origin` -- as vector PDF.

The figure it replaces existed only as a low-resolution PNG exported from a mind-mapping
tool, and drew the mechanism as one flat tree serving both slots. Since 2026-09-18 the
time and value slots admit different vocabularies, so the resolution is drawn per slot.

Run from anywhere:

    poetry run python docs/paper/graphic/origin_resolution_figure.py

writing `origin-resolution.pdf` (for the manuscript) and `origin-resolution.png` (for
looking at) beside this file. The content's source of truth is `internal/origin.py` --
`_ORIGINS__TIME`, `_ORIGINS__VALUE` and `find`.

Layout: vertical position is a cursor measured in rows, running downward from the top,
and the figure's height is whatever the cursor reaches. Keys are right-aligned to one
column and outcomes begin at another. Nothing is placed by eye against rendered text, so
adding a branch or lengthening a phrase cannot make two things collide.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# --- palette -----------------------------------------------------------------
# Close to the figure this replaces: one blue, with orange for the paths that occur in
# nearly all user code.
INK = "#16232e"
BLUE = "#1f7fd0"
BLUE__PALE = "#dceaf7"
ORANGE = "#d1762f"
ORANGE__PALE = "#fbe6d4"
ORANGE__BAND = "#fdf3e9"
RED = "#a8443a"
RED__PALE = "#f7dedb"
GREY = "#78858f"

FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

PT = dict(key=8.0, out=8.0, head=9.5, slot=10.0, sub=7.4, note=7.2)

# Columns, in axes fractions of the width.
X__SPINE = 0.045
X__KEY = 0.335  # keys are right-aligned here
X__OUT = 0.360  # outcomes begin here
X__END = 0.985

WIDTH__IN = 7.0
ROW__IN = 0.245  # one row of the cursor, in inches


class Cursor:
    """Vertical position, in rows, running downward from the top of the figure."""

    def __init__(self):
        self.y = 0.0

    def take(self, rows):
        y = self.y
        self.y += rows
        return y


def branch(ax, y, key, outcome, *, mono=True, highlight=False, refuse=False):
    """One branch of a slot: a tick off the spine, its key, and what it resolves to."""
    face, edge, ink = BLUE__PALE, BLUE, INK
    if refuse:
        face, edge, ink = RED__PALE, RED, RED
    if highlight:
        face, edge = ORANGE__PALE, ORANGE

    if highlight:
        ax.add_patch(
            FancyBboxPatch(
                (X__SPINE, y - 0.42),
                X__END - X__SPINE,
                0.84,
                boxstyle="square,pad=0",
                facecolor=ORANGE__BAND,
                edgecolor="none",
                zorder=0,
            )
        )

    ax.plot(
        [X__SPINE, X__SPINE + 0.016],
        [y, y],
        color=ORANGE if highlight else GREY,
        linewidth=1.5 if highlight else 0.8,
        zorder=2,
        solid_capstyle="round",
    )
    ax.text(
        X__KEY,
        y,
        key,
        family=MONO if mono else FONT,
        fontsize=PT["key"],
        va="center",
        ha="right",
        color=ink,
        zorder=3,
        linespacing=1.4,
        bbox=dict(
            boxstyle="round,pad=0.30",
            facecolor=face,
            edgecolor=edge,
            linewidth=0.7,
        ),
    )
    ax.text(
        X__OUT,
        y,
        outcome,
        family=FONT,
        fontsize=PT["out"],
        va="center",
        ha="left",
        color=ink,
        zorder=3,
    )


def slot(ax, cur, title, subtitle, branches):
    """A slot's heading and spine, with its branches hung off it."""
    y__title = cur.take(1.0)
    ax.text(
        X__SPINE,
        y__title,
        title,
        family=FONT,
        fontsize=PT["slot"],
        fontweight="bold",
        va="center",
        ha="left",
        color=BLUE,
    )
    ax.text(
        X__SPINE,
        cur.take(0.85),
        subtitle,
        family=FONT,
        fontsize=PT["sub"],
        style="italic",
        va="center",
        ha="left",
        color=GREY,
    )

    ys = []
    for key, outcome, kw in branches:
        rows = 1.65 if "\n" in key else 1.0
        ys.append(cur.take(rows) + (rows - 1.0) / 2.0)
        branch(ax, ys[-1], key, outcome, **kw)

    ax.plot([X__SPINE, X__SPINE], [ys[0], ys[-1]], color=GREY, linewidth=0.8, zorder=1)


def paragraph(ax, cur, lines, colour, *, indent=0.0):
    """A block of note text, one cursor row per line."""
    for line in lines:
        ax.text(
            X__SPINE + indent,
            cur.take(0.78),
            line,
            family=FONT,
            fontsize=PT["note"],
            va="center",
            ha="left",
            color=colour,
        )


def build():
    cur = Cursor()
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1)
    ax.axis("off")

    # --- the head ---------------------------------------------------------------
    y__head = cur.take(0.55)
    ax.text(
        0.042,
        cur.take(1.05),
        "Every origin is first normalised to a  [time, value]  pair",
        family=FONT,
        fontsize=PT["head"],
        fontweight="bold",
        va="center",
        ha="left",
        color=INK,
        zorder=2,
    )
    for line in (
        "None → [None, None]          0.5 → [0.5, None]",
        '"molasses" → ["molasses", None]          [a, b] → [a, b]',
    ):
        ax.text(
            0.042,
            cur.take(0.82),
            line,
            family=MONO,
            fontsize=PT["note"],
            va="center",
            ha="left",
            color=GREY,
            zorder=2,
        )
    ax.text(
        0.042,
        cur.take(0.95),
        "Each slot is then completed independently: one left as "
        "None takes the caller's default for that slot.",
        family=FONT,
        fontsize=PT["note"],
        va="center",
        ha="left",
        color=INK,
        zorder=2,
    )
    ax.add_patch(
        FancyBboxPatch(
            (0.02, y__head),
            0.96,
            cur.y - y__head - 0.15,
            boxstyle="round,pad=0,rounding_size=0.012",
            facecolor="#f3f7fb",
            edgecolor=BLUE,
            linewidth=0.9,
            zorder=0,
        )
    )

    # --- the two slots ----------------------------------------------------------
    plain = dict(mono=False)
    code = {}
    hl = dict(highlight=True)
    hl__plain = dict(highlight=True, mono=False)

    cur.take(0.9)
    slot(
        ax,
        cur,
        "time slot",
        "every option names an instant",
        [
            ("None", "the caller's chain:  anchor → last → 0.0 with a warning", hl),
            ("a number", "that number", plain),
            ('"anchor"', "the most recent anchor — an error if there is none", code),
            ('"last"', "the highest time recorded so far", code),
            ('"variable"', "per variable: its own most recent time", code),
            ("a variable name", "that variable's most recent time", plain),
            ("a context name", "its anchor, or its last row if it has none", hl__plain),
            ("anything else", "an error", plain),
        ],
    )

    cur.take(1.2)
    slot(
        ax,
        cur,
        "value slot",
        "only a variable names a quantity",
        [
            ("None", 'the caller\'s default: absolute — or "variable" for ramp', hl),
            ("a number", "that number", plain),
            ('"variable"', "per variable: its own last value  †", code),
            ("a variable name", "that variable's last value  †", plain),
            (
                '"anchor", "last",\na context name',
                "refused — each names an instant, not a quantity",
                dict(refuse=True),
            ),
            ("anything else", "an error", plain),
        ],
    )

    # --- footnotes --------------------------------------------------------------
    # Only the one note. Why the value slot is narrow, and that nothing is lost by it,
    # belongs to the caption and is already there -- repeating it here would put the same
    # argument in two places that have to be kept in step.
    cur.take(1.0)
    paragraph(
        ax,
        cur,
        [
            "†  Bounded by the resolved time origin: the value in effect at the instant the new",
            "    rows will occupy, not the variable's last value in the timeline as a whole. That is",
            "    what lets an operation be interwoven and still see the state that precedes it.",
        ],
        INK,
    )
    cur.take(0.45)

    ax.set_ylim(cur.y, 0)
    fig.set_size_inches(WIDTH__IN, cur.y * ROW__IN)
    return fig


def check__fits(fig, ax):
    """
    Reports any text running outside the drawing area.

    The layout places text by cursor rather than by measuring it, which keeps the source
    readable but means a longer phrase can overrun. Rather than check that by eye: the
    figure is regenerated whenever the mechanism changes, and whoever regenerates it will
    be thinking about the mechanism, not about the edges.
    """
    fig.canvas.draw()
    inverse = ax.transAxes.inverted()
    offenders = []
    for text in ax.texts:
        box = text.get_window_extent(fig.canvas.get_renderer())
        (x0, _), (x1, _) = inverse.transform(box.get_points())
        if x0 < 0.005 or x1 > 0.975:
            offenders.append(
                "  {:.3f}..{:.3f}  {!r}".format(
                    x0, x1, text.get_text().splitlines()[0][:60]
                )
            )
    return offenders


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    fig = build()

    offenders = check__fits(fig, fig.axes[0])
    if offenders:
        raise SystemExit(
            "Text runs outside the drawing area; shorten it or widen the figure:\n"
            + "\n".join(offenders)
        )

    fig.savefig(here / "origin-resolution.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(
        here / "origin-resolution.png", dpi=300, bbox_inches="tight", pad_inches=0.02
    )
    print("wrote origin-resolution.pdf and .png to {}".format(here))
