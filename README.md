![Test Status](https://github.com/WignerQuantumOptics/Wigner_Time/actions/workflows/tests.yml/badge.svg)

# Wigner_Time
Timeline creation and management for open-loop control in AMO experiments and beyond. Keep scrolling for a quick overview.

## Status
Beta. The package has been in use on two cold-atom setups for more than two years. A systematic code review begun in September 2026 surfaced a number of silent-failure cases — wrong answers returned without an error — and **all of them are now fixed**, together with the `origin` mechanism they clustered around; some of those fixes were deliberately breaking. What remains open is catalogued in `KNOWN_ISSUES.md`: open API decisions, structural work deferred past the paper, and the ADwin backend, where **one item is a safety rather than a correctness question** and is being treated as a precondition for wider release (see B11 there). Correctness of the backend can only be established on the hardware, so changes to it are reported as unverified until they have been.

A regression test now freezes a real experiment — a complete atom-cavity run taken off one of the two rigs — and checks the whole pipeline against it, so a change in what the package emits cannot pass unnoticed.

A preprint has been submitted to arXiv; the identifier will be added here once it is announced.

## Installation

**Not yet on PyPI.** Publication is planned once the accompanying paper has been
through review; `pip install wigner-time` will work from that point on. Until then,
install from the repository:

```bash
git clone https://github.com/WignerQuantumOptics/Wigner_Time.git
cd Wigner_Time
poetry install
```

Or, to install it into an existing environment without cloning:

```bash
pip install git+https://github.com/WignerQuantumOptics/Wigner_Time.git
```

Distributed under the GNU General Public License, version 3 — see [LICENSE](LICENSE).

Commercial licences, for use without the obligations of the GPL, are available from the copyright holders on request.

## Optional dependencies (package `extras`) 
 - `performance_and_export` (Recommended): Installs `pyarrow` for memory management, sharing between systems and export to `parquet`.
 - `display`: Installs `matplotlib` and `pyqt` for visualization.

While installing from the repository, extras are selected with
`poetry install --extras "adwin performance_and_export"`, or with
`pip install "wigner-time[adwin] @ git+https://github.com/WignerQuantumOptics/Wigner_Time.git"`.

## Developer Notes
Tests can be run from the root folder with
```bash
poetry run pytest
```

and documentation can be generated locally using 

``` bash
poetry run mkdocs serve
```

# Getting Started

1.  [Abstract](#orgfb88e4f)
2.  [Why not ADbasic?](#org231a69c)
3.  [Why Wigner Time?](#org5e1d714)
    1.  [Easy (separation of concerns)](#org154d75b)
    2.  [&rsquo;Simple&rsquo;](#org2528e95)
    3.  [Flexible](#org1877e40)
    4.  [Portable](#org99c74fd)
    5.  [Robust](#orgb155d13)
    6.  [Graphical display](#org6bc654b)
4.  [How it works?](#org95dac3d)
5.  [Example (For ADwin systems)](#orge8cea69)
6.  [Future?](#orge0a7f00)
7.  [Status](#org48d7fda)



<a id="orgfb88e4f"></a>

# Abstract

We introduce Wigner Time, an approach and Python package for defining and
manipulating experimental timelines in real-time open-loop control systems.
Fundamentally, procedures are expressed functionally and implemented tabularly, such that the core timelines can be represented with in-memory databases, e.g. `pandas.DataFrame`. The associated functional-style API is clear, flexible, and integrates well with the broader scientific Python ecosystem. The package has been optimized for ADwin-based quantum-optics experiments, but is broadly applicable to any experimental domain requiring precisely timed, multi-device control.

![An example timeline.](resources/timeline--example.png "A timeline generated and displayed by the package.")


<a id="org231a69c"></a>

# Why not ADbasic?

> **ADbasic** combines the **power and precision** of a low-level programming language with the **intuitive clarity** of a low-level programming languge.


<a id="org5e1d714"></a>

# Why Wigner Time?


<a id="org154d75b"></a>

## Easy (separation of concerns)

So much of physics is choosing the right level of abstraction.

Wigner Time allows you to use a normal and popular programming language to design your experimental timelines, while still utilizing the low-level features of other languages when you really need it.

Don&rsquo;t write ADbasic unless you need to!


<a id="org2528e95"></a>

## &rsquo;Simple&rsquo;

Easy tools often become complicated, but Wigner Time has been carefully designed so that all conveniences are **optional**. You can always drop down a level of abstraction to manually implement a new feature - to the point of just adding CSV tables.


<a id="org1877e40"></a>

## Flexible

By using a functional, data-oriented and bottom-up programming approach to timeline creation, Wigner Time makes it very easy to add and substract changes from the timeline and so can repsond to fast-changing lab requirements.


<a id="org99c74fd"></a>

## Portable

The essential data is always accesible and transferrable to any other language or collaborator

-   even a spreadsheet!


<a id="orgb155d13"></a>

## Robust

Implemented ontop of the \`pandas\` system, the most widely-used data science package.


<a id="org6bc654b"></a>

## Graphical display

Easily generate and investigate your timeline.


<a id="org95dac3d"></a>

# How it works?

Wigner Time is based around the idea of a &rsquo;timeline&rsquo;, which is, at heart, simply a table of rows and columns. The columns detail &rsquo;parameters&rsquo;, e.g. &rsquo;variable&rsquo; (the name of a quantity), &rsquo;time&rsquo;, &rsquo;value&rsquo;, &rsquo;context&rsquo; (a concise description of a real-world situation, e.g. &rsquo;OpticalTrap&rsquo; )

-   Add more parameters by adding columns
-   Add more operations by adding rows

By boiling the design down to a &rsquo;table&rsquo; as the foundation, then we can benfit from decades of database development, particularly in-memory database-like systems like \`pandas\`. Therefore, when in doubt, the user can simply manipulate their timeline using the well-developed \`pandas\` ecosystem. For most operations however, even this won&rsquo;t be necessary as \`wignertime\` provides layers of convenience functions ontop of this for designing open-loop experiments.


<a id="orge8cea69"></a>

# Example (For ADwin systems)

You want to control an optical shutter, an AOM and a laser lock.

For each channel, simply *name* the ADwin port using standard Python lists. These keep track of the physical connections. A name is `<device>__<UID>`, followed by `__<unit>` for an analog channel.

``` python
    import wignertime.api.v0_9 as wt
    
    connections = wt.adwin.connections(
        ["shutter__MOT", 1, 11],
        ["AOM__MOT", 1, 1],
        ["AOM__MOT__transmission", 3, 1],
        ["lockbox__MOT__MHz", 3, 8],
    )
```
For analog connections, also specify a linear factor, conversion function or calibration file, and the permitted range.

``` python
    devices = wt.devices(
        ["lockbox__MOT__MHz", 0.05, -200, 200],
        [
            "AOM__MOT__transmission",
            wt.function_from_file(
                "resources/calibration/aom_calibration.dat",
                sep=r"\s+",
            ),
            0.0,
            1.0,
        ],
    )
```
Specify how you want your experiment to begin and end, using readable options and user-specific keywords. The initial and final states belong to no instant of the run, so they are placed before and after it, at −∞ and +∞.

``` python
    import math
    
    initial = wt.update(
        time=-math.inf,
        context="ADwin_LowInit",
        shutter__MOT=1,
        AOM__MOT=0,
        AOM__MOT__transmission=1.0,
        lockbox__MOT__MHz=0.0,
    )
    final = wt.update(
        time=math.inf,
        context="ADwin_Finish",
        shutter__MOT=1,
        AOM__MOT=0,
        AOM__MOT__transmission=1.0,
        lockbox__MOT__MHz=0.0,
    )
``` 

And any key processes…

``` python
MOT = wt.update(
            shutter__MOT=0,
            AOM__MOT=1,
            context="MOT",
        )
detuned_growth = wt.ramp(
                    lockbox__MOT__MHz=-5,
                    duration=10e-3,
        )
```
None of these is a timeline yet: each is a *stage*, written relative to its own beginning. Combine them in readable and modular fashion, and make a timeline of the result with `to_timeline`.

Due to the sensible defaults, each component, e.g. `ramp`, will automatically join onto the end of the previous operation in a causal chain.

``` python
tline = wt.to_timeline(
    wt.stack(
        initial,
        MOT,
        detuned_growth,
        final,
    )
)
```

The timeline is a *pandas.DataFrame*, so it can be edited and inspected directly: `tline[tline["context"] == "MOT"]` selects the rows of the MOT stage.

It can then be converted to an ADwin-compatible format. The cycle period has to be stated, in seconds, because it belongs to the program running on the ADwin rather than to the experiment.

``` python
    wt.adwin.convert(tline, connections, devices, cycle_period=5e-6)
```

<a id="orge0a7f00"></a>

# Future?

-   Official support for NI systems
-   Graphical input
-   Feature requests. Post an issue!