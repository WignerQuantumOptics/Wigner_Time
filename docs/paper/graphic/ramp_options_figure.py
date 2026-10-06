"""
Generates the drawing of `fig:ramp` -- the two origins of a ramp -- as vector PDF.

The drawing it replaces was made in Inkscape, with labels from before the signature took
its present form (`origin=default`, `origin2=[variable,default]`, `t`, `t2`), and it measured
the end value from the second origin's own frame. Here the labels are the defaults the
listing beside the figure prints, and the geometry is the rule of #142: the ramp starts where
its variable stands, at the instant `origin` resolves to; `origin2=[VARIABLE, 0.0]` refers the
end time to that start and the end value to zero, so the end value is absolute.

Run from anywhere:

    poetry run python docs/paper/graphic/ramp_options_figure.py

writing `ramp-options.pdf` (for the manuscript), `ramp-options.svg` (for editing) and
`ramp-options.png` (for looking at) beside this file.

Layout: positions are in data units of an invisible axes, time across and value up; text is
checked against the edges of the figure before anything is written.
"""

import math
import pathlib

import matplotlib

matplotlib.use("Agg")
# The SVG keeps its text as text, so that it can be edited (in Inkscape, say); its
# fonts are then the viewer's, and DejaVu is what the PDF embeds.
matplotlib.rcParams["svg.fonttype"] = "none"

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.transforms import offset_copy

# --- palette -----------------------------------------------------------------
# That of the other generated figures, where orange means hardware, so it is not used here:
# the two origins take blue and green, and the ramp the violet of the original drawing.
INK = "#16232e"
BLUE__DEEP = "#1d5f99"
GREEN = "#3c8d4f"
VIOLET = "#5b3a9a"
GREY = "#78858f"

FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

PT = dict(label=7.6, small=6.8, note=6.0, axis=7.6, anchor=10.0)

MONO__ADVANCE = 0.602  # DejaVu Sans Mono's advance width, in ems
LABEL__OFFSET = (3.8, 2.4)  # where an origin's label starts, in points from its point
LABEL__ANGLE = 35.0  # at which both origins' labels rise, in degrees

WIDTH__IN, HEIGHT__IN = 4.4, 2.29
X__MIN, X__MAX = -0.5, 10.6
Y__MIN, Y__MAX = -1.25, 5.75

# The story: a variable held at V0, an anchor at T__ANCHOR, a ramp from T__START to T__END
# ending at V1.
T__ANCHOR, T__START, T__END = 1.9, 4.5, 9.5
V0, V1 = 1.5, 4.6
FRAME = 0.85  # length of a frame's axes


def arrow(ax, a, b, *, colour=INK, linewidth=0.9, dashed=False, head=True):
    """
    An arrow from `a` to `b`. A dashed one is drawn as a dashed shaft and a solid head
    separately: a dash pattern given to the arrow as a whole dashes the outline of the
    head too.
    """
    style = dict(color=colour, linewidth=linewidth, shrinkA=0, shrinkB=0, zorder=3)
    if dashed:
        ax.plot(
            [a[0], b[0]],
            [a[1], b[1]],
            color=colour,
            linewidth=linewidth,
            linestyle=(0, (3, 2)),
            solid_capstyle="butt",
            zorder=3,
        )
        if not head:
            return
        # The head alone, on a vanishing stretch of the shaft's end.
        a = (b[0] - 1e-3 * (b[0] - a[0]), b[1] - 1e-3 * (b[1] - a[1]))
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle="-|>,head_length=4,head_width=2.2" if head else "-",
            **style,
        )
    )


def text(ax, x, y, s, **kw):
    kw.setdefault("family", FONT)
    kw.setdefault("fontsize", PT["label"])
    kw.setdefault("color", INK)
    kw.setdefault("va", "center")
    kw.setdefault("ha", "center")
    return ax.text(x, y, s, **kw)


def frame(ax, x, y, colour):
    """A small coordinate frame: the point an origin resolves to, and its two axes."""
    arrow(ax, (x, y), (x + FRAME, y), colour=colour, linewidth=0.8)
    arrow(ax, (x, y), (x, y + FRAME), colour=colour, linewidth=0.8)
    ax.plot([x], [y], "o", ms=4.2, color=colour, zorder=5)


def diagonal(fig, ax, x, y, angle, parts, **kw):
    """
    An origin's label, rising at `angle` from beside the point it names, into the quadrant
    between its frame's axes: monospaced `parts` along one baseline, a space apart.
    """
    along = 0.0  # points along the baseline, from its start
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for string, style in parts:
        size = style.get("fontsize", PT["label"])
        place = offset_copy(
            ax.transData,
            fig=fig,
            x=LABEL__OFFSET[0] + along * c,
            y=LABEL__OFFSET[1] + along * s,
            units="points",
        )
        text(
            ax,
            x,
            y,
            string,
            family=MONO,
            transform=place,
            rotation=angle,
            rotation_mode="anchor",
            ha="left",
            va="baseline",
            **{"fontsize": size, **style, **kw},
        )
        along += (len(string) + 1) * MONO__ADVANCE * size


def ramp(t):
    """The default ramp function's shape, a tanh, from (T__START, V0) to (T__END, V1)."""
    s = (t - T__START) / (T__END - T__START)
    return V0 + (V1 - V0) * (math.tanh(4 * (s - 0.5)) / math.tanh(2) + 1) / 2


def build():
    fig, ax = plt.subplots()
    ax.axis("off")

    # --- the axes of the timeline ------------------------------------------------------
    arrow(ax, (0, 0), (X__MAX - 0.15, 0))
    arrow(ax, (0, 0), (0, Y__MAX - 0.2))
    text(ax, X__MAX - 0.15, -0.32, "time", style="italic", color=GREY, ha="right")
    text(ax, 0.18, Y__MAX - 0.3, "value", style="italic", color=GREY, ha="left")

    # --- the variable as it stands, and the anchor before it --------------------------
    # The label straddles the line it names, a line above and a line below.
    ax.plot([0, T__START], [V0, V0], color=GREY, lw=1.3, zorder=2)
    for y, line in ((V0 + 0.066, "the variable’s"), (V0 - 0.252, "current value")):
        text(
            ax,
            0.1,
            y,
            line,
            fontsize=PT["note"],
            color=GREY,
            style="italic",
            ha="left",
            va="baseline",
        )
    # The anchor marks an instant, so it hangs from a tick on the time axis.
    ax.plot([T__ANCHOR, T__ANCHOR], [-0.13, 0.13], color=INK, lw=0.9, zorder=3)
    text(ax, T__ANCHOR, -0.45, "⚓", fontsize=PT["anchor"])

    # --- origin: the start time, from the latest anchor, and the variable's value --------
    frame(ax, T__ANCHOR, V0, BLUE__DEEP)
    diagonal(
        fig,
        ax,
        T__ANCHOR,
        V0,
        LABEL__ANGLE,
        [
            ("origin=INFER", dict(fontweight="bold")),
            ("→ [ANCHOR,VARIABLE]", dict(fontsize=PT["small"])),
        ],
        color=BLUE__DEEP,
    )

    # Below the variable's line, where the diagonal label leaves room.
    y = V0 - 0.28
    arrow(ax, (T__ANCHOR, y), (T__START, y), dashed=True)
    text(ax, 3.5, y - 0.33, "time", family=MONO, va="baseline")

    # --- origin2: the end time from the start, the end value from zero -----------------
    frame(ax, T__START, 0, GREEN)
    diagonal(
        fig,
        ax,
        T__START,
        0,
        LABEL__ANGLE,
        [("origin2=[VARIABLE,0.0]", dict(fontweight="bold"))],
        color=GREEN,
    )

    y = -0.55
    arrow(ax, (T__START, y), (T__END, y), dashed=True)
    text(ax, (T__START + T__END) / 2 + 0.3, y - 0.33, "duration or time2", family=MONO)

    arrow(ax, (T__END, 0), (T__END, V1 - 0.2), dashed=True)
    text(ax, T__END + 0.18, V1 / 2, "end\nvalue", ha="left", linespacing=1.15)

    # --- the ramp ---------------------------------------------------------------------
    ts = [T__START + (T__END - T__START) * i / 200 for i in range(201)]
    ax.plot(
        ts,
        [ramp(t) for t in ts],
        color=VIOLET,
        lw=2.2,
        solid_capstyle="round",
        zorder=4,
    )
    ax.plot([T__START, T__END], [V0, V1], "o", ms=4.6, color=VIOLET, zorder=6)

    ax.set_xlim(X__MIN, X__MAX)
    ax.set_ylim(Y__MIN, Y__MAX)
    fig.subplots_adjust(0, 0, 1, 1)
    fig.set_size_inches(WIDTH__IN, HEIGHT__IN)
    return fig, ax


def check__fits(fig, ax):
    """Reports any text running outside the figure."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inverse = ax.transData.inverted()
    offenders = []
    for t in ax.texts:
        (a, b0), (b, b1) = inverse.transform(t.get_window_extent(renderer).get_points())
        if a < X__MIN or b > X__MAX or min(b0, b1) < Y__MIN or max(b0, b1) > Y__MAX:
            offenders.append("  {!r} leaves the figure".format(t.get_text()))
    return offenders


if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    fig, ax = build()

    offenders = check__fits(fig, ax)
    if offenders:
        raise SystemExit(
            "Text runs outside the figure; shorten it or move it:\n"
            + "\n".join(offenders)
        )

    for suffix, kw in (
        (".pdf", {}),
        (".png", dict(dpi=300)),
        (".svg", dict(metadata={"Date": None})),
    ):
        fig.savefig(
            here / ("ramp-options" + suffix), bbox_inches="tight", pad_inches=0.02, **kw
        )
    print("wrote ramp-options.pdf, .png and .svg to {}".format(here))
