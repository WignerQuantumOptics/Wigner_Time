# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
poetry install --with dev --all-extras   # what CI does
poetry run pytest                        # whole suite, from the repo root
poetry run pytest test/wignertime/test_drop_repeats.py                              # one file
poetry run pytest test/wignertime/test_drop_repeats.py::test_channels_are_independent  # one test
poetry run pytest -k ramp                # by name

poetry run black src test                # formatter used throughout
poetry run isort src test
poetry run pyflakes src

poetry run mkdocs serve                  # docs from docs/, API page is generated from docstrings
```

There is no pytest configuration and no `conftest.py`; the suite relies on the project being installed
(`poetry install`) and on being run from the repo root.

`test_file.py` writes through `file.save`, which resolves relative paths against the cwd and
auto-increments rather than overwriting. It therefore runs each of its tests in a fresh `tmp_path`
(an autouse `monkeypatch.chdir`), so the suite leaves nothing in the repo root and pytest bounds the
growth by keeping only the last three runs. Before 2026-09-21 it wrote fourteen files per run into
the root, which also made two of its own assertions vacuous — see the fixture's docstring.

## Working rules

`KNOWN_ISSUES.md` is the standing checklist for code work and is **authoritative over this file** on
anything it covers. Read it before touching `timeline.py` or `internal/origin.py`. Its rules:

- **Do not "fix" by adding try/except or defensive branching.** Failures should be loud and early, at
  the point where the user's intent was ambiguous — not absorbed downstream. The value proposition is
  that experiment descriptions are inspectable data.
- **Silent failures outrank visible ones.** A wrong answer that raises is a nuisance; one that returns
  quietly can sit in an experiment for months.
- **Section C items are open API decisions — flag and ask, never settle unilaterally.** (A3, the
  degenerate-row filtering, was such a case and was settled on 2026-09-18: a zero duration raises, a
  zero value change is a hold and is kept.)
- **A green suite does not clear the ADwin backend.** Changes under `wignertime/adwin/` can only be
  checked for internal consistency; correctness must be verified on the rig. Say so explicitly rather
  than reporting such a change as done.
- **The paper and the code are developed together.** If a change makes a claim in `docs/paper/main.tex`
  inaccurate or hard to state, stop and report it. Do not edit the paper to match the code. If a
  behaviour is awkward to describe in prose, that is a signal to change the code.

**Reader-facing prose follows `WRITING.md`**: the paper, `README.md`, `docs/index.md`, onboarding
documents and the front pages of the documentation. They are written for physicists who write Python,
not for developers. That means no programming vocabulary the arXiv text does not already use, no
history of the code, and Unicode typography (`–`, never `--`). The history and mechanism that fill
this file and `KNOWN_ISSUES.md` do not belong there. Docstrings may be more technical. Prose written
in this environment has drifted into developer-note style before (2026-09-23), so check new paper
text against the arXiv version's voice.

## Primary reference

`docs/paper/main.tex` is the most comprehensive description of the project: a SciPost Physics Codebases
submission (Clark, Sárközi, … Vukics) that states the design rationale, not just the API. Read it
before any non-trivial design decision. Useful section map: `sec:definitions` (the three layers),
`sec:origin` + appendix `sec:origin_full` (the complete `origin` specification and resolution order),
`sec:functions` (`update`/`ramp`/`anchor` and `to_timeline`, with input-format tables), `sec:context`,
`sec:stacking` and `sec:interweaving`, `sec:adwin` (the whole real-time program, in ~15 lines),
appendix `sec:adwin_operation` (how the sequencer and the manual console share the outputs, at a
high level: the period check, the final state, the hand-over, the jump warning),
`sec:discussion` (comparison with labscript / ARTIQ / Cicero / Entangleware, and stated future work).

The manuscript is now committed and self-contained under `docs/paper/`, imported from Overleaf:
`main.tex`, `SciPost.cls`, `SciPost_bibstyle.bst`, `WignerTime.bib`, and all five figures under
`docs/paper/graphic/`. One of those figures is **generated, not drawn**: `fig:origin` comes from
`graphic/origin_resolution_figure.py`, so a change to the origin mechanism should be carried into the
manuscript by rerunning it. It checks its own text for overflow and refuses to write a figure that
does not fit. The others are still static images. Every `\includegraphics` target and the
`\bibliography{WignerTime.bib}` call resolve. No LaTeX toolchain is installed here, so the build is
Overleaf's. `minted` requires `pygmentize` and `-shell-escape`, which `docs/paper/.latexmkrc` sets.
Build from inside `docs/paper/`; the figure paths are relative to it.

**The committed manuscript is canonical, and Overleaf is kept in step with it from here.** The
arXiv version was imported at `fdd2e0d` (2026-09-15). Since 2026-10-01 the Overleaf project is
cloned next door, in `../Wigner_Time_Overleaf/` (branch `master`, the only one Overleaf has), and
syncing it is ours to do, push included (maintainer, 2026-10-01). A sync goes both ways, Overleaf
first: pull the clone, and bring any edit made on Overleaf into `docs/paper/` as an ordinary commit
on the working branch; then copy `docs/paper/` over the clone, commit there naming the repository
commit it carries (`Sync with docs/paper/ of Wigner_Time at <hash>`), and push. When both sides
changed the same passage, stop and show the maintainer both, rather than choosing. The last
synced point is therefore the newest such message in the clone's `git log`. The clone carries what the build
needs and nothing else: not `graphic/origin_resolution_figure.py` and its unused PNG preview, nor
`desktop.ini`. `.latexmkrc`, which sets `-shell-escape` for `minted`, came from Overleaf and lives
in both. Line numbers quoted in these notes refer to the repository's copy.

**The paper describes version 1.0.0** (maintainer, 2026-10-01). `pyproject.toml` stays at 0.9.0 until
the release: the bump is the last commit before the tag `v1.0.0` on `main`, so that 1.0.0 is exactly
the code the paper prints; the steps are #169. From then on that API is frozen, and the question
about any change is whether it breaks it, which is what the milestones `1.x` and `2.0` encode
(`KNOWN_ISSUES.md`, "How work is tracked", for the whole tracker scheme agreed on 2026-10-02).

**The lab code that uses the package is next door, and can be read at any time**:
`../quantum_optics_lab/` (sibling of this repo). `timeline/experiment.py` and
`timeline/diagnostics.py` are the real counterparts of the demo and of the paper's `sec:forwarding`;
`control/time_of_flight.py` is `sec:parameter_scan`; `console.py` re-exports the manual console of
D22, which moved into this package on 2026-09-27 (`wignertime.adwin.console`); and
`../notebooks/` holds the notebooks the experiments are run from (`diagnosticsStageByStage.ipynb`
interweaves imaging into each preparation stage). It has its own `KNOWN_ISSUES.md` (items `L*`).
`../Lab2TimelineTakeout_VargaDani_20260921/` is the source of the Lab2 regression fixture. Check
real usage there before deciding what a demo should show or whether an API change breaks anyone.

For the `origin` mechanism specifically, read `docs/origin-resolution.md` first: it maps every branch
of the resolution in four layers, and since 2026-09-18 it is a record rather than a plan — every defect
it catalogues is fixed, each entry saying what replaced it, and the measurements are kept because they
are the argument for the design. `sec:origin` and `sec:origin_full` now match the code, and so does `fig:origin`:
it was redrawn and made generated on 2026-09-19 (#123, closed). The origin block is finished.

## Architecture

The governing idea, and the one to preserve: **the experimental description is data, not a
program.** Comparable systems (labscript, ARTIQ, Cicero, Entangleware) describe an experiment as a
program that is *executed to emit* hardware instructions, so the description is consumed as it is
produced. Here the description is a table — a value — which is why it can be plotted, filtered,
diffed between runs, archived next to its data, or handed to a collaborator without the hardware.
Hardware enters at exactly one point, the conversion step. Accordingly: no in-place modification and
no global state; every core function returns a new timeline, and user-defined stages should too.

A *timeline* is a `pandas.DataFrame`, nothing more. The base schema is `timeline._SCHEMA`
(`time`, `variable`, `value`, `context`) — hence **vtvc**, the name behind `*vtvc` and `**vtvc_dict`
throughout the input plumbing. Every other column is bolted on by a later stage (`module`/`channel`
from `connection`s, `to_V`/`value__min`/`value__max` from `device`s, `value__digits` from
`conversion`, `cycle` from `adwin`). Users are expected to fall back to plain pandas whenever the
conveniences don't fit.

Three named layers, with movement in both directions as an explicit goal:

- **operation** — experiment stages ("take a fluorescence image"). *Client code, deliberately not
  part of the package*; `demo/full_experiment.py` is an example of it, not an API.
- **device** — the vtvc timeline in real physical units (MHz, A). The core abstraction, `timeline.py`.
- **connection** — hardware-ready arrays ("send 5 V to connection 2"), produced solely by
  `adwin/core.py::convert`. Porting to other hardware means writing a new conversion here plus a
  consumer program on the controller; nothing above this layer should need to change.

`device` and `connection` are two separate tables on purpose: recalibrating a device and rewiring
the apparatus are independent operations, each touching one place. Never fold module/channel numbers
into device conversions or vice versa. **They must still answer for each other**: since 2026-09-21
`device.check_correspondence(connections, devices)` raises in *both* directions — a device with no
connection, and an analogue connection with no device. The second is the dangerous one (A14): a
mistyped device name used to leave `check_within_range` with nothing to check, so the variable ran
with its safety limits silently absent.

### Stages and timelines

There are two kinds of object (#85, C7 in `KNOWN_ISSUES.md`). A **stage** is a function of a
timeline: what `update`, `ramp`, `anchor`, `stack` and `cascade` return, and what every user-defined
stage returns. It is written once, relative only to its own beginning, and can be placed anywhere. A
**timeline** is the table. **`to_timeline(stage, onto=None)` is the one way from the first to the
second**: the stage applied to `onto`, or to an empty timeline. `onto` is first-class, not a
convenience — building a timeline can be expensive, so a parameter scan keeps its base as a table and
places each variation onto it; `to_timeline(b, onto=to_timeline(a))` equals `to_timeline(stack(a, b))`.

`stack` and `cascade` **compose stages only, and always return one**: a table is refused in any
position, with a message naming `to_timeline`. **`create` is gone** (2026-09-29): the first rows of a
timeline are an `update` like any other, applied to the empty timeline, where the origin is absolute
zero and the rows must name their context (#156). A module `__getattr__` in `timeline.py` says so to
anyone still writing `tl.create`. **The core functions take no timeline** (2026-09-29, P2 step 3):
`update`, `ramp` and `anchor` are keyword-only (`anchor` keeps `time` positional) and always return a
stage, and a `timeline=` given to one is refused with a message naming `to_timeline`. Each is a thin
public function over a private body (`_update`, `_ramp`, `_anchor`, which take the timeline first),
joined by `util.stage(body, signature, arguments)`: that builds the stage, tags it, records which
keywords it can consume, and makes a keyword forwarded later by a `stack` a *default*, filling only
what the call left unstated (#136, #145). It replaced `function__lambda`, which recovered the
arguments by reading the caller's frame. User-defined stages take no `timeline` either: they return a
`stack`, and are applied with `to_timeline`.

`cascade` adds prefix-routed keyword forwarding (`MOT_duration=...` reaches `MOT`'s `duration`), so a
whole experiment has a single point of contact for its nested parameters.

**`stack` and `cascade` take their stages differently, and nothing in the syntax says so.** `stack`
takes stages *already called* — `stack(MOT(duration=15), molasses())` — where everything but the
timeline is bound (partial application, not currying: the remaining argument arrives in one call).
`cascade` takes the functions *themselves* — `cascade(MOT, molasses, MOT_duration=15)` — and calls
them with the routed keywords. So a stage reaches `cascade` bare and `stack` applied; they are not
interchangeable, and `stack(MOT)` raises (D17).

**Stages compose as siblings of a `stack`, never by nesting.** `expand(ramp(...))` looks like
composition but passes a function in as `expand`'s `timeline`; `util.ensure_timeline` raises a
`TypeError` naming the mistake, and also rejects anything that is neither a frame nor `None` (C4,
2026-09-16). Allowing nesting to *compose* was considered and rejected; see C4 for why.

Stages are tagged (`util.ATTRIBUTE__DEFERRED`, set by `util.stage` and by `stack`), because a
stage, a composed `stack` and an *uncalled stage function* are otherwise indistinguishable — all plain
functions with similar signatures. `stack` and `to_timeline` check the tag, so `stack(MOT)` for
`stack(MOT(...))` raises instead of binding the timeline to `MOT`'s first parameter (D17). An untagged
callable taking exactly one required positional argument is accepted too, so a hand-written
`lambda tline: ...` still works; `timeline.as_deferred` marks anything else. `noop` is consequently
our own tagged function rather than `funcy.identity`.

A trap now closed: **`expand` acts on the whole timeline it receives**, not on the adjacent ramp.
Mid-`stack` in a late stage it expanded every ramp accumulated so far, and since it then drops the
`function` column, the `expand` inside `adwin.core.convert` became a no-op and the hand-passed
resolution is what reached the hardware. **`expand` now takes a table only** (C7 item 6, done in P2
step 3): it is not a stage and cannot sit in a `stack`. **A ramp's resolution belongs to the ramp**
(#65, C7 item 7, P3, 2026-09-29): `function=functools.partial(tanh, time_resolution=1e-4)` keeps its
1e-4 through `expand` and `convert`. `expand` kept its `time_resolution` (maintainer, 2026-09-29,
rather than losing it as item 7 first said), but as a *default*: it reaches only the ramp functions
that leave it unstated, the rule a keyword forwarded by `stack` follows (#145). The ramp functions
default to `None`, meaning unbound, and a ramp binding none, expanded with none given, raises.
`config.TIME_RESOLUTION`, their old import-time default (#144), is gone.

### Origins — why chaining is causal by default

`internal/origin.py` is the heart of the package. An `origin` is a `[time, value]` pair.
`origin.update` shifts a newly built fragment's `time`/`value` per variable relative to the preceding
timeline, which is what makes `stack(timeline, update(...), ramp(...))` join end-to-end without
explicit times.

**The two slots admit different vocabularies** (2026-09-18, A7/#105):

| slot | admits |
| --- | --- |
| time | a number, `ANCHOR`, `LAST`, `VARIABLE`, a variable name, a context name |
| value | a number, `VARIABLE`, a variable name (and for `ramp` only `VARIABLE`, #142) |

**The rules are tags, not strings** (#158, 2026-09-29): `config.Origin`, exported as `tl.ANCHOR`,
`tl.LAST` and `tl.VARIABLE`, recognised with `is` and printing as their bare names, like `INFER`. So a
string in an origin is always a *name* — a variable's first, then a context's — and nothing needs
reserving: A9's refusal of contexts and variables named `anchor`, `last` or `variable` is gone. One of
those words written as a string, where nothing in the timeline has that name, raises with a message
naming the tag.

The time slot asks *when*; the value slot asks *how much, of what*, and only a variable names a
quantity — `ANCHOR`, `LAST` and a context name each resolve to whichever variable happens to hold
the row at that instant, so they answered in the wrong units. They now raise. Nothing is lost: "the
value `coil__A` held at the end of molasses" is `["molasses", VARIABLE]`. The `fig:origin` caption
licensed the wider reading and was amended; the figure is generated
(`docs/paper/graphic/origin_resolution_figure.py`) and was rerun for the tags in P6 (`a31757e`).

**`None` in a slot means "defer to the default for this slot"; `0.0` means "absolute".** Do not
conflate them — that conflation was A6. `config.ORIGIN__DEFAULTS` (for `update`/`anchor`) and
`config.ORIGIN__DEFAULTS__RAMP` are **terminal chains**: each entry's time reference is tried in turn,
and if none is satisfiable the origin is `0.0` with a warning. A partially stated origin keeps the
default for the slot it omits.

**The signatures name that default `INFER`** (`wt_config.INFER`, #142, 2026-09-28), so that `help()`
shows the default does something, and `context` defaults to it too. It is an object, recognised with
`is`, and **`None` means exactly the same**, as the whole argument and in a slot. Keep it that way: a
stage that takes `origin=None` or `context=None` and forwards it is the ordinary way to pass "no
opinion" on, and giving `None` a meaning of its own would change what every such stage does (A8's
amendment in `KNOWN_ISSUES.md`). Absolute placement is a number. There is no "off" for context:
**every row has a context**, stated or inherited (#156, 2026-09-29), so the first rows of a timeline
must name theirs, `context=""` is refused, and so is a table handed in with a row lacking one.

**Do not propose replacing `origin` with separate `t0`/`v0` keywords.** It is a reasonable idea and
it was declined on 2026-09-19 (#74), on the merits rather than for inertia: the two slots really are
independent now, and splitting would delete the normalisation layer whose string-padding rule was A6's
mechanism. What settles it is `ramp.origin2`, which places the *end* point and does not decompose into
the same scheme — `ramp` would carry `t0`, `v0` and two more for the end, alongside the `time`, `time2` and
`duration` it already has. A ramp's second reference is a different kind of thing from its first, and a
flat `t0`/`v0` vocabulary would flatten that. The same issue's second half, a `default` sentinel in
place of `None`, was resolved rather than declined: `None` now carries one meaning, not two.

Three properties of the mechanism that are easy to break:

- **The flexibility exists only at construction time and never leaks into the data.** Once resolved,
  a timeline holds nothing but absolute times and values; any origin could equally have been written
  as a numeric coordinate. Don't introduce a column or a marker that defers resolution.
- **Value lookups against a variable are bounded in time** — the value *in effect at the origin
  instant*, not the variable's last value in the timeline overall. This is what the `time__max` /
  `time__max__relative` plumbing in `origin.py` is for, and what makes interweaving see the state that
  physically precedes it.
- **A ramp always starts where its variable is** (#142, 2026-09-29). Its start value is never
  written: the 2-D form `v=[[t1, v1], [t2, v2]]` is refused, and so is anything but `"variable"` in
  the value slot of its `origin`. A start that differs from the current value is a step hidden in a
  ramp, and a wanted jump is an `update` before the ramp, where it shows. This is why
  `config.ORIGIN__DEFAULTS__RAMP` (`[[ANCHOR, VARIABLE], [LAST, VARIABLE]]`) carries a value
  slot at all, and it is the only thing that slot can hold; `update` needs none since its values are
  absolute. An explicitly given origin *completes* rather than replaces the default, so
  `ramp(..., origin="stage1")` means what it reads as — time from `stage1`, value from the variable
  itself (it used to start the ramp from **0.0**, silently: A6). `origin=0.0` is absolute time and
  reads the same in `update` and `ramp`.
- **A ramp must end after it begins**: zero and negative durations both raise. The negative case was
  the dangerous one — `expand` sorts each ramp's boundaries by time, so the endpoints were silently
  exchanged and the variable finished at its *old* value (A12). A ramp whose value does not change is
  not an error: it is a hold, and is kept.
- **A variable is in at most one ramp at a time** (#157, 2026-09-29). A ramp holds rows for its
  boundaries only, so a ramp starting inside another took the other's *start* value, and `expand`
  paired the boundaries wrongly. Overlaps raise; meeting end to start is fine, compared exactly —
  a tolerance would let a ramp placed by a different sum start 4e-17 s early, from the wrong value.
- **A ramp of a variable with no previous value raises**, because there is nothing to start from,
  and the message says to `update` it first. Zero amps on an uninitialised coil is a command, not a
  neutral default. (The escapes that used to exist, `origin=[None, 0.0]` and the 2-D form, went with
  #142's rule.)

*Anchors* are a non-physical variable named `⚓` (`config.LABEL__ANCHOR`), auto-numbered `⚓__001`, used
as a time reference within a `context`. They deliberately have no `connection`, so
`adwin.connection.remove_unconnected_variables` drops them at export. Their purpose is that the
instants that matter physically are often ones where nothing is commanded — a MOT collection ends
because enough time has passed, not because a device switched. **Every user-defined stage is
recommended to end with an anchor** carrying that stage's context; the anchor-then-last default is
what then turns every `time` into a Δt from the end of the preceding stage.

### Context does three jobs

`context` carries no timing information and is never sent to the hardware, but it is not decoration:
it is documentation that survives into the archived data (and drives `timeline.context_info` and the
display grouping); it is addressable as an `origin`, which makes a stage a *named region* and is the
basis of interweaving; and a backend may reserve particular names (`ADwin_LowInit`, `ADwin_Finish`).

Contexts are **inherited, not repeated** — `update`, `ramp` and `anchor` adopt the latest context of
the timeline they extend, and any `context=` given to `stack` is forwarded to all its constituents — as a
default, so one that states its own context keeps it, and through nested stacks too. **A context is
inherited from a row at an instant only** (#154, 2026-09-29): the rows before the run sit at −∞ and
those after it at +∞, and pass none on. That closed the trap in which rows written after `init`
inherited `ADwin_LowInit`, and rows added to a finished timeline `ADwin_Finish`, silently. A row after
`init` now has to name its context, as the first rows of any timeline do (#156).

**Rows before the run are at −∞, rows after it at +∞** (#154, option (b), settled by the maintainer
2026-09-29). This is one rule in the core, which does not mention ADwin: ±∞ is not an instant. So the
time slot of an origin, the default chain's `LAST` and context inheritance see finite rows only
(`origin.instants`), and a time reference whose rows are all at ±∞ raises. A value lookup is bounded
by a finite instant, so it sees −∞ and never +∞. `anchor` and `ramp` refuse ±∞. On a timeline with
nothing at an instant yet, the default origin falls back to absolute zero silently, which is what
places the first timed stage: `MOT` no longer says `origin=0.0`. The demo and the lab write `init`
at `time=-math.inf` and the final state at `time=math.inf`. The display draws them in margins either
side of the run, and the JSON writer keeps them as the strings `"-inf"`/`"inf"`.

### Variable naming is load-bearing, not cosmetic

`config.VARIABLE__REGEX` — **`<device>__<UID>(__<unit>)`**, e.g. `coil__MOT_lower__A`,
`shutter__MOT`; `<device>` and `<unit>` contain no `_`, the UID may contain single ones (D7, #121,
settled 2026-09-29). **No `__<unit>` suffix means the line is digital.** `connection.new` rejects
names that don't match, `conversion`/`device` key off the unit, and `adwin/display.py` groups plots
by it. Keeping `_` out of `<device>` is what made the migration from the old
`<device>_<UID>(__<unit>)` safe: every old name has a `_` before its first `__`, so it is refused
rather than read as digital with its unit taken for the UID. The Lab2 fixture keeps its real, old
names; its test rebinds the regex, as a site with its own convention would.

### Ramps are stored as functions, then expanded

`ramp` writes two boundary rows plus a callable in a `function` column. `timeline.expand` applies it
to produce one row per point and drops the `function` column — a one-way operation, done only just
before hardware export. `expand`'s `**function_args` reach each function as defaults, by
`util.function__defaults`: a keyword a function leaves unstated (no default, or `None`) is given, one
it states (any other default, including a value a `partial` binds) is not. That is how `convert`'s
cycle period reaches `ramp_function.tanh` and the demo's `lambda origin, terminus,
time_resolution: ...`, but not a ramp that binds its own resolution. (It was
`util.function__filtered_kws`, which handed every declaring function the value.) **`expand` keeps
each ramp's rows where the ramp was written** (A18); see the filtering note below.

### ADwin export pipeline

`adwin/core.py::convert(timeline, connections, devices, cycle_period, ...)` composes, in order:

1. `connection.remove_unconnected_variables` — anything without a physical port disappears (anchors).
2. `timeline.expand` — ramps become rows at the machine's cycle period (or at `time_resolution`).
3. `adwin/internal.py::add` — join `connections` + `devices`, `conversion.add` → `value__digits`,
   `device.check_within_range` (raises, listing every offending variable), `add_cycle`.
4. `adwin/validate.py::all` — `cycles` → `types` → `special_contexts` → `drop_duplicates` →
   `drop_repeats`. `cycles` must precede `types`, which narrows the column to 32 bits.
5. `internal.to_tuples` — `[[(cycle, module, channel, digits), ...analogue], [...digital]]`.
6. `validate.ascending` — each array in cycle order, since the backend's index never rewinds.

**The cycle period belongs to the machine, not to the package**, so `convert` has no default for it
and the machine specifications may not carry one. Both labs run **T12** processors, at **1 ns per
`Processdelay` tick** (maintainer, 2026-09-23): Lab1 at 5 µs (`Initial_Processdelay = 5000`, as
committed), Lab2 at 2 µs. `adwin.PROCESSDELAY__RATE` is the one hardware constant the package
keeps, and it knows only the T12; any other processor is refused by name.

`adwin/core.py::upload(timeline, connections, devices, machine, process)` is the only way to the
machine. It reads the period off the machine on every call, as `Get_Processdelay(process)` over the
processor's rate, and never sets it, because an ADbasic program can overwrite its own
`Processdelay`. It converts at that period, pushes the result into `Par_1..3` and
`Data_10..13` / `Data_20..23`, starts nothing, and returns an `Upload` log: machine, process,
processor, Processdelay, period, last cycle and the arrays. The log is a named tuple whose first two
fields are the machine and the process, so it serves wherever the lab's `(machine, process)` pair
does. (It was `create` until 2026-09-23; renamed because it neither creates anything nor should be
confused with `timeline.create`.) The final state (`ADwin_Finish`) does not go into the playback
arrays: `upload` moves those rows to `data_31..33` (analogue module, channel, digits) and
`data_42..43` (digital channel, value), with the counts in `Par_15`/`Par_16`. `finish:` plays them
unconditionally, so a stopped run restores the default state too (B11). `convert`'s output still
carries them at the finish sentinel. Every array's capacity is `adwin.ROWS__MAX`, which must match
the `.bas` defines, and `upload` refuses a timeline that exceeds one before writing anything.
The arrays have an owner: each sequencer sets `Par_17` to its own process number at the start of
`lowinit:` and clears it at the end of `finish:`. Right after claiming `Par_17` it stops the manual
console (process 10), having first noted whether it was running (ADbasic's `Process10_Running`), and
starts it again at the very end of `finish:` if it was. The console holds its requests while `Par_17`
is nonzero, and runs at low priority level 2, above the level 1 at which every `lowinit:` and
`finish:` runs, so that no sequence can start between its test of `Par_17` and its write (D22,
lab L23). `upload` and `start` wait on
the process `Par_17` names, as well as on their own. The ADbasic 6.00 manual (Feb. 2017) is the
reference for what the machine side may assume; the maintainer has it, and `KNOWN_ISSUES.md` cites
it by page.
Besides `Par_1..3` it writes `Par_9`, the Processdelay it built
for, and clears `Par_14`. Both sequencer programs report their own Processdelay into `Par_14` at
the end of `init:`, and play nothing past the initial state if it differs from `Par_9` (#128). `wait`
then raises `PeriodRefused`, and refuses a program that did not report at all. `upload` waits for a running process before writing, and says
so once (A15). The machine accepts writes mid-run, and a parameter scan's next upload used to
land in the previous shot's finish tail.

Running what was uploaded is `start(log) -> Run` and `wait(run)`, bracketed by the context
manager `running(log)`, with `run(log)` for a block with nothing in it. `wait` refuses a run that
lost events (`LostEvents`, with the slip in µs). It reads ADwin's counter once, after the run: the
manual counts lost events "since process start", so that count is the run's own. UNVERIFIED on the
rig; if the counter accumulated from load instead, every run after a lossy one would raise, which is
loud, whereas a difference across the run would pass a run that lost as many as the one before. Peripherals such as cameras and the time
controller are **not** Wigner Time's: they are armed before `running` and serviced inside the
block, in the lab's code (maintainer, 2026-09-24; L22 there records the longer-term direction of
one thread per device). An error inside the block waits the run out but does not stop it: that a
stop from the PC reaches `finish:` and plays the final state (B11) awaits the rig. The consumer is `resources/ADwin/WignerTimeADwin.bas` (ADbasic,
real-time side). Its Par `#define`s, its arrays and `processUpdates` live in
`resources/ADwin/WignerTimeSequencer.inc`, included by a path relative to the program, and must stay
in sync with `core.upload`. Par, FPar and Data numbers are shared by every process on the machine,
and processes can start and stop one another. `WignerTimeADwinADC.bas` (process 4) includes the same
file and plays the same arrays. It also records an ADC channel in burst mode over a window that
`adwin.adc.arm` writes in cycles (`Par_42`/`Par_43`), armed for one run and disarmed by its
`finish:`. The program itself has no notion of the period (step 10). The manual console is
`adwin.console` with `WignerTimeConsole.bas` as process 10, which includes the same file. It
keeps a shadow state rather than a mailbox: `configure` writes the panel as entries into
`data_51..54`, `set_value` writes the digits wanted for one entry and returns, and the program's
sweep writes wherever wanted and written differ, so nothing waits on anything. The panel comes
from `panel(connections, devices, defaults)`, so a channel is converted and bounded exactly as
the pipeline does it. Values are refused while a sequence owns the outputs. When a sequence has
finished since the program last looked (`Par_18`, counted by every `finish:`), it adopts the
run's final state on starting, and marks unknown what the final state does not name. A start
by hand writes everything again. A variable the defaults do not name is left alone, since the lab
keeps the MOT coils steady between runs. `upload` warns, after its wait and before writing, about
each analogue channel the console itself wrote since it last started (`data_55`) that the run will
jump from its value, in the initial state or at the first row that sets it (`console.jumps`).

**Keep the real-time program arithmetic-free.** Its whole job is "at this cycle, if a value differs
from the previous one, output it": one comparison per channel group, early exit, no computation. Every
instruction in the event loop must finish within one cycle, so logic there is paid for directly in
temporal resolution — the ADbasic implementation this replaced evaluated `tanh` in-loop and was
limited to a 5 µs cycle; the present system runs the same experiments at 1 µs. The design is a
deliberate trade of computation for memory, which is the entire reason `expand` exists. Proposals that
move logic back into ADbasic to save rows are going the wrong way.

Two distinct kinds of filtering, easy to confuse: `drop_duplicates` removes *temporal* collisions
(two rows for one variable rounding to the same cycle, keeping the last written, so **every step
before it must keep the written order among tied rows**: sort with `wt_frame.sort`, which is
stable, and `expand` puts each ramp's rows back where the ramp was written — A18, where an `update`
at the instant a ramp ended lost to the ramp's end); `drop_repeats` removes *value* redundancy
(a row commanding a channel to the value it already holds), grouped by physical channel rather than
by variable, and always keeping the first and last row of each channel — `core.upload` derives the
run length from the highest non-special cycle, and tanh ramp tails are flat.

`adwin/__init__.py::CONTEXTS__SPECIAL` (`ADwin_LowInit`, `ADwin_Init`, `ADwin_Finish`) map to sentinel
cycle numbers. Rows in these contexts have **no meaningful time**, and are written at −∞ (the two
before the run) or +∞ (after it). They are validated separately, and exempted from both drop
functions. A variable may have at most one row **before the run, across `ADwin_LowInit` and
`ADwin_Init` together** (#154 (b1): both are at −∞, so nothing orders them), and one after it.
`add_cycle` computes cycles for finite rows only, and refuses a non-finite time outside these
contexts. Finite fictional times (the old −1 µs) still convert, but the core then reads them as
real, which is what #154 was about.

## Conventions

- **Two rules for `__`, by audience (D7, settled 2026-09-29).** In what users write and the paper
  shows – the demo, the lab, the stages' parameters – **`__` comes only before a unit**
  (`duration_coil_ramp`, `lag_MOT_shutter`, `to__MHz`, `detuning__MHz`), and a variable name uses it
  as the field separator of its grammar (above). **Library-internal identifiers keep the older rule**,
  `__` between a name and its qualifier or unit: columns (`value__digits`), kwargs (`time__max`,
  `column__value`), functions (`mask__changed`), config constants (`ORIGIN__DEFAULTS`). They were
  deliberately not renamed; extending the units-only rule into the package is a separate decision.
  Trailing `__002` on filenames is `file.py`'s collision suffix. Stage parameters mirror the core
  functions: `time`, not `t`.
- **pandas is the interface, not a detail to hide** (decided 2026-09-30): the paper says a
  timeline *is* a `pandas.DataFrame`, and no change of backend is planned. So use pandas directly
  where it fits. `internal/dataframe.py` (imported as `wt_frame`) was meant as a seam for a polars
  backend; it is now the home of the helpers whose behaviour carries one of the package's rules, and
  new helpers belong there only if they do too. **Sort with `wt_frame.sort`, never `sort_values`
  bare**: pandas sorts one column unstably by default, and order among tied rows is meaning (A18).
  The same goes for `drop_duplicates` (keeps the last row written) and `insert_dataframes` (by
  position). Its thin wrappers over pandas (`new`, `concat`, `isnull`, `read_*`, `assert_equal`) and
  `wt_frame.CLASS` stay, as there is nothing to gain from rewriting their callers, but need not be
  used in new code.
- Optional dependencies are gated at import time with `importlib.util.find_spec` and a raised
  `ImportError` (`adwin/core.py` needs `ADwin`, `display.py` needs `matplotlib`). Keep new optional
  code importable-but-inert the same way.
- Standard aliases: `tl` (timeline), `wt_frame`, `wt_origin`, `wt_util`, `wt_config`, `wt_adwin`.
- Numpy-style docstrings (mkdocstrings is configured for them). Prose in docstrings tends to explain
  *why* a rule exists, not just what the function does — match that.
- `internal/` is explicitly unstable API. `internal/doc/` and `doc/` are org-mode notes and scratch
  notebooks, not built documentation; `docs/` is the mkdocs source (`docs/index.md` duplicates the
  README, so changes to the overview belong in both). The paper lives in its own self-contained
  subtree, `docs/paper/`; neither it nor `docs/origin-resolution.md` is in `mkdocs.yml`'s nav.
- Tests live under `test/wignertime/`, mirroring the package. (They sat under `test/wigner/time/`,
  the pre-rename name, until 2026-09-21.) `test/wignertime/fixtures/lab2/` freezes a **real**
  experiment — Dániel Varga's Lab2 atom-cavity run, taken off the rig on 2026-09-21 — as 13 KB of
  parquet, and `test_lab2_regression.py` runs it end to end and checksums the output. When one of
  those checksums moves, the pipeline changed; see the fixture's own `README.md` for what the
  numbers mean and why they are today's output rather than the rig's. Tests build frames as literal row lists and compare with
  `wt_frame.assert_equal`; behaviour with many input shapes is covered via `@pytest.mark.parametrize`
  over calls to `tl.update` and friends.

## Known rough edges

For bugs and open API decisions, **`KNOWN_ISSUES.md` is the list.** Do not duplicate it here, and do
not re-report its section F. Its items were verified against the live repo on 2026-09-01; D1 (the
`origin.py` self-import) and E (the suite aborting when an optional extra was absent) were fixed then,
and the verification results are recorded in the entries themselves.

The trap that used to lead this section, **A4**, was fixed on 2026-09-18: a `ramp` onto an
anchorless timeline no longer lands at absolute time, because `ramp`'s chain now has a `LAST` step
and a terminal `0.0`. **A8 and B1 are moot since 2026-09-29**: both were about a start value stated
in the 2-D form, which #142's rule removed — every ramp now starts from wherever its variable sits,
`ramp(v=target, time=..., duration=...)`, and a wanted jump is an `update` before it. **A3 is settled**
(2026-09-18): a zero-duration ramp raises, and a flat ramp is kept as the hold it is.

Not covered by `KNOWN_ISSUES.md`:

- `internal/constructor.py` calls `tl.previous_time`, which no longer exists. Nothing in the package
  or the suite imports it; its only importers are `internal/doc/demonstration.py` and
  `internal/experimental/demonstration.py`, which are scratch notes. Dead code, but with references.
- `internal/timeline/validate.py` is documented as out of date with respect to the current schema
  (it references `unit_range`/`safety_range` columns that `device.py` no longer produces).
- `black` passes on everything except `src/wignertime/internal/doc/diagnosticsDemo.py`, which is a
  scratch notebook rather than package code (checked 2026-09-22: 1 file would be reformatted, 57 left
  alone). Format files you touch; a repo-wide `black` run would bury your diff.
- **The paper's demo listing (`sec:demonstration`) is a cleaned-up variant of
  `src/wignertime/demo/full_experiment.py`, not a copy of it**: a smaller apparatus (the rule is
  spelling, not extent). The spellings were reconciled on 2026-09-29 (D7): the demo now uses the
  paper's names (`duration_coil_ramp`, `lower_current_initial`, `shutter__OP1`,
  `MOT_detuned_growth`, `delay_shutter_reinitialization`, `timeline_demo`), in the new variable
  grammar. What still differs is content: the paper's `MOT_off` respects the shutter lags, the
  demo's does not, and the demo drives compensation coils the paper leaves out. **`docs/paper/main.tex`
  is canonical: when they disagree, the code changes** (maintainer decision, 2026-09-02).
- `drop_repeats` (on this branch, not yet on `main`) times analog transitions at the cycles where
  the DAC code actually changes, per Kowalski *et al.* Its docstring argues the filtering is
  *equivalent* to bit-flip-timed expansion on the hardware's own grid, not an approximation to it.
  Since 2026-09-23 `sec:adwin` says so, in a paragraph after the event loop. That paragraph used to
  sit commented out at the end of `sec:discussion` as future work. It has not been run on the rig.
- The other stated gap is peripherals programmed over serial rather than driven by a voltage (DDS
  being the canonical case). The paper commits to implementing this as an `expand`-shaped conversion —
  one device-layer row becoming several bit-level rows — rather than as a special case.
