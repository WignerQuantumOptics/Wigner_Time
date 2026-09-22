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

## Primary reference

`docs/paper/main.tex` is the most comprehensive description of the project: a SciPost Physics Codebases
submission (Clark, Sárközi, … Vukics) that states the design rationale, not just the API. Read it
before any non-trivial design decision. Useful section map: `sec:definitions` (the three layers),
`sec:origin` + appendix `sec:origin_full` (the complete `origin` specification and resolution order),
`sec:functions` (`create`/`update`/`ramp`/`anchor` with input-format tables), `sec:context`,
`sec:stacking` and `sec:interweaving`, `sec:adwin` (the whole real-time program, in ~15 lines),
`sec:discussion` (comparison with labscript / ARTIQ / Cicero / Entangleware, and stated future work).

The manuscript is now committed and self-contained under `docs/paper/`, imported from Overleaf:
`main.tex`, `SciPost.cls`, `SciPost_bibstyle.bst`, `WignerTime.bib`, and all five figures under
`docs/paper/graphic/`. One of those figures is **generated, not drawn**: `fig:origin` comes from
`graphic/origin_resolution_figure.py`, so a change to the origin mechanism should be carried into the
manuscript by rerunning it. It checks its own text for overflow and refuses to write a figure that
does not fit. The others are still static images. Every `\includegraphics` target and the `\bibliography{WignerTime.bib}` call
resolve. No LaTeX toolchain is installed here, so a build has not been demonstrated — and note that
`minted` requires `pygmentize` and `-shell-escape`. Build from inside `docs/paper/`; the figure paths
are relative to it.

**The committed manuscript has diverged from Overleaf, and Overleaf is the one the co-authors edit.**
The arXiv version was imported at `fdd2e0d` (2026-09-15, 1458 lines); twelve commits have changed it
since, `+117 / −45` lines plus a new generated figure, and **none of that has been carried back.**
`docs/paper/CHANGES-since-arXiv.md` is the inventory for doing so, with a `latexdiff` recipe at the
end. Until it is carried across, line numbers quoted in these notes and in `KNOWN_ISSUES.md` are
against the *committed* file and no longer match Overleaf.

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

### The dual-return idiom

`update`, `ramp`, `anchor` and `expand` return **a timeline when `timeline=` is passed, and a curried
callable when it is not**. `create` is the exception and always returns a timeline: it initialises one
from scratch, so it takes no `timeline` and no `origin` at all (2026-09-16, #45/C2 — this matches the
signature `sec:functions` has always documented). To add to an existing timeline, use `update`;
`update(..., origin=0.0)` is exactly what passing a timeline to `create` used to do. The callable branch is produced by
`internal/util.py::function__lambda`, which reads the caller's frame to capture its own arguments — so
it only works when called directly from the public function's body. `stack` and `cascade` compose
those callables (and forward their own kwargs into every one of them). Any new top-level timeline
function should follow this shape.

This is what lets a stage be written once, generically, relative only to its own beginning, and
inserted anywhere later. `create` and `update` are otherwise near-identical — they share a body,
`timeline._populate_timeline`, and differ only in what they expose of it: `create` is the entry point
of a stack and withholds `timeline`/`origin`, `update` can appear anywhere inside one and takes both.
`cascade` adds prefix-routed keyword forwarding (`MOT_duration=...` reaches `MOT`'s `duration`), so a
whole experiment has a single point of contact for its nested parameters.

**`stack` and `cascade` take their stages differently, and nothing in the syntax says so.** `stack`
takes stages *already called* — `stack(timeline, MOT(duration=15))` — where everything but the
timeline is bound (partial application, not currying: the remaining argument arrives in one call).
`cascade` takes the functions *themselves* — `cascade(MOT, molasses, MOT_duration=15)` — and calls
them with the routed keywords. So a stage reaches `cascade` bare and `stack` applied; they are not
interchangeable, and `stack(timeline, MOT)` raises (D17). `cascade` returns whatever `stack` makes of
the first stage's result — a timeline if that stage yields one (`init` ends in `create`), a deferred
function otherwise (`MOT` ends in `update`) — so a `cascade` is itself stackable.

**Deferred calls compose as siblings of a `stack`, never by nesting.** `expand(ramp(...))` looks like
composition but passes a function in as `expand`'s `timeline`; write
`stack(timeline, ramp(...), expand(...))` instead. `util.ensure_timeline` raises a `TypeError` naming
the mistake, and also rejects anything that is neither a frame nor `None` (C4, 2026-09-16) — but
`stack` and `cascade` take a leading callable *legitimately* and must stay outside that guard.
Allowing nesting to *compose* was considered and rejected; see C4 for why.

Deferred objects are tagged (`util.ATTRIBUTE__DEFERRED`, set by `function__lambda` and by `stack`),
because a deferred call, a composed `stack` and an *uncalled stage* are otherwise indistinguishable —
all plain functions with similar signatures. `stack` checks the tag on every constituent, so
`stack(timeline, MOT)` for `stack(timeline, MOT(...))` now raises instead of binding the timeline to
`MOT`'s first parameter (D17). An untagged callable taking exactly one required positional argument is
accepted too, so a hand-written `lambda tline: ...` still works; `timeline.as_deferred` marks anything
else. `noop` is consequently our own tagged function rather than `funcy.identity`.

A related trap the guard cannot catch: **`expand` acts on the whole timeline it receives**, not on the
adjacent ramp. Mid-`stack` in a late stage it expands every ramp accumulated so far, and since it then
drops the `function` column, the `expand` inside `adwin.core.convert` becomes a no-op and the
hand-passed resolution is what reaches the hardware. For per-ramp resolution, bake it into the
`function` argument as `demo.pull_coils` does.

### Origins — why chaining is causal by default

`internal/origin.py` is the heart of the package. An `origin` is a `[time, value]` pair.
`origin.update` shifts a newly built fragment's `time`/`value` per variable relative to the preceding
timeline, which is what makes `stack(timeline, update(...), ramp(...))` join end-to-end without
explicit times.

**The two slots admit different vocabularies** (2026-09-18, A7/#105):

| slot | admits |
| --- | --- |
| time | a number, `"anchor"`, `"last"`, `"variable"`, a variable name, a context name |
| value | a number, `"variable"`, a variable name |

The time slot asks *when*; the value slot asks *how much, of what*, and only a variable names a
quantity — `"anchor"`, `"last"` and a context name each resolve to whichever variable happens to hold
the row at that instant, so they answered in the wrong units. They now raise. Nothing is lost: "the
value `coil__A` held at the end of molasses" is `["molasses", "variable"]`. The `fig:origin` caption
licensed the wider reading and was amended; **the figure image still draws the old undivided tree and
needs redrawing.** `_ORIGINS` is the single list of reserved words, and a variable or context named
after one is refused where it is written.

**`None` in a slot means "defer to the default for this slot"; `0.0` means "absolute".** Do not
conflate them — that conflation was A6. `config.ORIGIN__DEFAULTS` (for `update`/`anchor`) and
`config.ORIGIN__DEFAULTS__RAMP` are **terminal chains**: each entry's time reference is tried in turn,
and if none is satisfiable the origin is `0.0` with a warning. A partially stated origin keeps the
default for the slot it omits.

**Do not propose replacing `origin` with separate `t0`/`v0` keywords.** It is a reasonable idea and
it was declined on 2026-09-19 (#74), on the merits rather than for inertia: the two slots really are
independent now, and splitting would delete the normalisation layer whose string-padding rule was A6's
mechanism. What settles it is `ramp.origin2`, which places the *end* point and does not decompose into
the same scheme — `ramp` would carry `t0`, `v0` and two more for the end, alongside the `t`, `t2` and
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
- **`ramp` is the exception that carries a value-relative default**, and it matters. It bypasses
  `config.ORIGIN__DEFAULTS` for `config.ORIGIN__DEFAULTS__RAMP`
  (`[["anchor", "variable"], ["last", "variable"]]`), because a ramp must look up where the variable
  currently sits; `update` needs no value origin since its values are absolute. Since 2026-09-18 an
  explicitly given origin *completes* rather than replaces that default, so
  `ramp(..., origin="stage1")` means what it reads as — time from `stage1`, value from the variable
  itself. (It used to start the ramp from **0.0**, silently: A6.) `sec:origin_full` has been
  corrected; it claimed no default in the package was value-relative.
- **A ramp must end after it begins**: zero and negative durations both raise. The negative case was
  the dangerous one — `expand` sorts each ramp's boundaries by time, so the endpoints were silently
  exchanged and the variable finished at its *old* value (A12). A ramp whose value does not change is
  not an error: it is a hold, and is kept.
- **A ramp of a variable with no previous value raises**, because there is nothing to start from.
  Set the variable first, or say what the start is: `origin=[None, 0.0]` (defer the time to the
  default, state the value) or the 2-D form `v=[[t1, v1], [t2, v2]]`. Note the behaviour change of
  2026-09-18: before per-slot completion, `ramp(..., origin=0.0)` on an unset variable left the value
  slot empty and started the ramp at **0.0** without comment. Zero amps on an uninitialised coil is a
  command, not a neutral default, so it now refuses and names both escapes.

*Anchors* are a non-physical variable named `⚓` (`config.LABEL__ANCHOR`), auto-numbered `⚓_001`, used
as a time reference within a `context`. They deliberately have no `connection`, so
`adwin.connection.remove_unconnected_variables` drops them at export. Their purpose is that the
instants that matter physically are often ones where nothing is commanded — a MOT collection ends
because enough time has passed, not because a device switched. **Every user-defined stage is
recommended to end with an anchor** carrying that stage's context; the anchor-then-last default is
what then turns every `t` into a Δt from the end of the preceding stage.

### Context does three jobs

`context` carries no timing information and is never sent to the hardware, but it is not decoration:
it is documentation that survives into the archived data (and drives `timeline.context_info` and the
display grouping); it is addressable as an `origin`, which makes a stage a *named region* and is the
basis of interweaving; and a backend may reserve particular names (`ADwin_LowInit`, `ADwin_Finish`).

Contexts are **inherited, not repeated** — `update`, `ramp` and `anchor` adopt the latest context of
the timeline they extend, and any `context=` given to `stack` is forwarded to all its constituents. The
corresponding trap, flagged in `timeline.update`'s docstring: rows appended after a stage in a reserved
context silently inherit that reserved context, so name the context explicitly when extending past one.

### Variable naming is load-bearing, not cosmetic

`variable.py::REGEX` — `equipment_context__unit`; **no `__unit` suffix means the line is digital**.
`connection.new` rejects names that don't match, `conversion`/`device` key off the unit, and
`adwin/display.py` groups plots by it.

### Ramps are stored as functions, then expanded

`ramp` writes two boundary rows plus a callable in a `function` column. `timeline.expand` applies it
to produce one row per point and drops the `function` column — a one-way operation, done only just
before hardware export. `expand`'s `**function_args` are filtered against each function's signature
by `util.function__filtered_kws`; that is how `time_resolution` reaches `ramp_function.tanh` from
`adwin.core.convert`.

### ADwin export pipeline

`adwin/core.py::convert` composes, in order:

1. `connection.remove_unconnected_variables` — anything without a physical port disappears (anchors).
2. `timeline.expand` — ramps become rows at the machine's cycle period.
3. `adwin/internal.py::add` — join `connections` + `devices`, `conversion.add` → `value__digits`,
   `device.check_within_range` (raises, listing every offending variable), `add_cycle`.
4. `adwin/validate.py::all` — `types` → `special_contexts` → `drop_duplicates` → `drop_repeats`.
5. `internal.to_tuples` — `[[(cycle, module, channel, digits), ...analogue], [...digital]]`.

`adwin/core.py::create` then pushes that into `Par_1..3` and `Data_10..13` / `Data_20..23` of the
machine. The consumer is `resources/ADwin/WignerTimeADwin.bas` (ADbasic, real-time side); its
`#define`s and `data_NN` array meanings must stay in sync with `core.create`.

**Keep the real-time program arithmetic-free.** Its whole job is "at this cycle, if a value differs
from the previous one, output it": one comparison per channel group, early exit, no computation. Every
instruction in the event loop must finish within one cycle, so logic there is paid for directly in
temporal resolution — the ADbasic implementation this replaced evaluated `tanh` in-loop and was
limited to a 5 µs cycle; the present system runs the same experiments at 1 µs. The design is a
deliberate trade of computation for memory, which is the entire reason `expand` exists. Proposals that
move logic back into ADbasic to save rows are going the wrong way.

Two distinct kinds of filtering, easy to confuse: `drop_duplicates` removes *temporal* collisions
(two rows for one variable rounding to the same cycle); `drop_repeats` removes *value* redundancy
(a row commanding a channel to the value it already holds), grouped by physical channel rather than
by variable, and always keeping the first and last row of each channel — `core.create` derives the
run length from the highest non-special cycle, and tanh ramp tails are flat.

`adwin/__init__.py::CONTEXTS__SPECIAL` (`ADwin_LowInit`, `ADwin_Init`, `ADwin_Finish`) map to sentinel
cycle numbers. Rows in these contexts have **no meaningful time**, so they are validated separately
(at most one row per variable) and exempted from both drop functions.

## Conventions

- **`__` separates a name from its qualifier or unit; `_` separates words inside the name.** It runs
  through everything: columns (`value__digits`), kwargs (`duration__initial`, `column__value`,
  `timeline__past`), functions (`mask__changed`, `sanitize__round_value`), and the `variable` regex.
  Trailing `__002` on filenames is `file.py`'s collision suffix. Note the scope limit from D7: this
  governs library-internal identifiers, and `docs/paper/main.tex` overrides it for anything the paper shows.
- **Route dataframe operations through `internal/dataframe.py`** (imported as `wt_frame`), not through
  pandas directly. That module exists so a polars backend can be dropped in later; `wt_frame.CLASS` is
  the dataframe type. Several older modules (`conversion.py`, `device.py`, `adwin/connection.py`,
  `internal/timeline/inherit.py`) still import pandas and carry TODOs about it — don't add more.
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
  over calls to `tl.create` and friends.

## Known rough edges

For bugs and open API decisions, **`KNOWN_ISSUES.md` is the list.** Do not duplicate it here, and do
not re-report its section F. Its items were verified against the live repo on 2026-09-01; D1 (the
`origin.py` self-import) and E (the suite aborting when an optional extra was absent) were fixed then,
and the verification results are recorded in the entries themselves.

The trap that used to lead this section, **A4**, was fixed on 2026-09-18: a `ramp` onto an
anchorless timeline no longer lands at absolute time, because `ramp`'s chain now has a `"last"` step
and a terminal `0.0`. **A8 was fixed the same day**: a start value stated in the 2-D form is now taken as
written, and the value origin is resolved only for the variables whose start had to be inferred. The
rule to keep in mind when writing a ramp is which form you are in — `ramp(v=target, t=..., duration=...)`
starts from wherever the variable currently sits, while `ramp(v=[[t1, v1], [t2, v2]])` starts from `v1`,
full stop. **B1 and A3 are both settled** (2026-09-18): the boundary frames are aligned on `variable` before
being compared, a zero-duration ramp raises, and a flat ramp is kept as the hold it is.

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
  `src/wignertime/demo/full_experiment.py`, not a copy of it**, and the two have drifted: the paper
  uses single-underscore parameter names (`duration_coil_ramp`, `lag_MOT_shutter`,
  `lower_current_initial`, `to__MHz`), the code uses the `__` convention (`duration__coil_ramp`,
  `lag__MOTshutter`, `li`/`ui`, `toMHz`); the paper has `shutter_OP1`/`shutter_OP2` and
  `MOT_detuned_growth` against the code's `shutter_OP001`/`shutter_OP002` and `MOT__detuned_growth`;
  and the paper adds a `MOT_off` stage and a `delay_shutter_reinitialization` parameter that the code
  inlines as `0.1`. (The ADbasic subroutine `processSwitches` was renamed to
  `processUpdates` in both `.bas` files on 2026-09-15, so that divergence is gone.) **`docs/paper/main.tex` is canonical: when they disagree, the code changes** (maintainer
  decision, 2026-09-02 — see `KNOWN_ISSUES.md` D7 for the inventory and the prerequisites). This
  governs only what the paper actually shows; internal identifiers it never mentions keep the `__`
  convention below.
- `drop_repeats` (on the current branch) implements what `sec:discussion` still describes as future
  work in a commented-out paragraph — timing analog transitions at the instants the DAC code actually
  changes, per Kowalski *et al.* Its docstring argues the filtering is *equivalent* to bit-flip-timed
  expansion on the hardware's own grid, not an approximation to it. That paragraph is worth reviving
  rather than leaving commented out.
- The other stated gap is peripherals programmed over serial rather than driven by a voltage (DDS
  being the canonical case). The paper commits to implementing this as an `expand`-shaped conversion —
  one device-layer row becoming several bit-level rows — rather than as a special case.
